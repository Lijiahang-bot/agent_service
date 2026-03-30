# -*- coding: utf-8 -*-
"""FastAPI 后端服务：提供多轮对话 API，支持流式响应"""
import os
import json
from typing import Optional, AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI

# 依赖：pip install langchain-openai langchain-core fastapi uvicorn
SLIDING_WINDOW = 10

app = FastAPI(title="Agent Service API", description="多轮对话服务")

# 配置 CORS，允许 Streamlit 前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    history: Optional[list[dict]] = None


class ChatResponse(BaseModel):
    reply: str
    history: list[dict]


class MessageStore:
    """简单的内存消息存储，用于维护不同会话的历史"""
    def __init__(self):
        self.stores = {}
    
    def get_messages(self, session_id: str) -> list[BaseMessage]:
        if session_id not in self.stores:
            self.stores[session_id] = []
        return self.stores[session_id]
    
    def update_messages(self, session_id: str, messages: list[BaseMessage]):
        self.stores[session_id] = messages


message_store = MessageStore()
llm_instance: Optional[ChatOpenAI] = None


def build_llm() -> ChatOpenAI:
    """构建 LLM 实例"""
    return ChatOpenAI(
        model="qwen3.5-flash",
        # 若没有配置环境变量，可将下行改为 api_key="sk-xxx"
        # 获取 API Key：https://help.aliyun.com/zh/model-studio/get-api-key
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        # 北京地域；新加坡地域请改为：https://dashscope-intl.aliyuncs.com/compatible-mode/v1
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )


def apply_sliding_window(messages: list[BaseMessage], max_messages: int = SLIDING_WINDOW) -> list[BaseMessage]:
    """仅保留末尾 max_messages 条消息，用于多轮上下文截断。"""
    if len(messages) <= max_messages:
        return messages
    return messages[-max_messages:]


def messages_to_dict(messages: list[BaseMessage]) -> list[dict]:
    """将消息列表转换为字典格式"""
    result = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            result.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            result.append({"role": "assistant", "content": msg.content})
    return result


def dict_to_messages(msg_dicts: list[dict]) -> list[BaseMessage]:
    """将字典格式转换为消息对象"""
    messages = []
    for msg in msg_dicts:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))
    return messages


@app.get("/")
async def root():
    return {"message": "欢迎使用 Agent Service API", "docs": "/docs"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """处理聊天请求，支持多轮对话（非流式）"""
    global llm_instance
    
    if llm_instance is None:
        llm_instance = build_llm()
    
    try:
        # 获取或初始化历史消息
        if request.history:
            history = dict_to_messages(request.history)
        else:
            history = message_store.get_messages(request.session_id)
        
        # 追加用户消息
        history = list(history)
        history.append(HumanMessage(content=request.message))
        
        # 应用滑动窗口
        to_model = apply_sliding_window(history)
        
        # 调用模型
        response = llm_instance.invoke(to_model)
        reply = response.content if response.content is not None else ""
        
        # 追加助手回复并截断
        history.append(AIMessage(content=reply))
        history = apply_sliding_window(history)
        
        # 更新存储
        message_store.update_messages(request.session_id, history)
        
        return ChatResponse(
            reply=reply,
            history=messages_to_dict(history)
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"对话失败：{str(e)}")


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """处理聊天请求，流式响应（SSE）"""
    global llm_instance
    
    if llm_instance is None:
        llm_instance = build_llm()
    
    # 获取或初始化历史消息
    if request.history:
        history = dict_to_messages(request.history)
    else:
        history = message_store.get_messages(request.session_id)
    
    # 追加用户消息
    history = list(history)
    history.append(HumanMessage(content=request.message))
    
    # 应用滑动窗口
    to_model = apply_sliding_window(history)
    
    async def generate() -> AsyncGenerator[str, None]:
        """生成器：流式输出 AI 回复"""
        nonlocal history
        full_reply = ""
        try:
            # 使用流式调用
            for chunk in llm_instance.stream(to_model):
                if chunk.content:
                    full_reply += chunk.content
                    # SSE 格式发送数据块
                    data = json.dumps({"content": chunk.content, "done": False}, ensure_ascii=False)
                    yield f"data: {data}\n\n"
            
            # 发送完成信号
            data = json.dumps({"content": "", "done": True}, ensure_ascii=False)
            yield f"data: {data}\n\n"
            
            # 保存完整回复到历史
            history.append(AIMessage(content=full_reply))
            history = apply_sliding_window(history)
            message_store.update_messages(request.session_id, history)
            
        except Exception as e:
            error_data = json.dumps({"error": str(e), "done": True}, ensure_ascii=False)
            yield f"data: {error_data}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    # 启用热重载模式（需要以模块方式运行）
    # 开发环境建议使用：python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
    # 或者直接运行：python main.py (不使用 reload)
    uvicorn.run(
        "main:app",  # 使用字符串格式支持热重载
        host="0.0.0.0", 
        port=8000,
        reload=False,  # Windows 下热重载可能不稳定，建议设为 False
        log_level="info"
    )
