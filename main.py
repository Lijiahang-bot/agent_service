# -*- coding: utf-8 -*-
"""FastAPI 后端服务：提供多轮对话 API，支持流式响应"""
import json
from typing import Optional, AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from ollama import Client as OllamaClient

from knowledge_base import router as kb_router
from knowledge_base_chroma import chroma_rag_retrieve_chunks, router as kb_chroma_router
from models import (
    OLLAMA_CHAT_HTTP_TIMEOUT_SEC,
    build_chat_llm,
    get_ollama_base_url,
    get_ollama_chat_model,
)

# 依赖：pip install langchain-openai langchain-core fastapi uvicorn
SLIDING_WINDOW = 10

RAG_SYSTEM_INSTRUCTION = """你是一个问答机器人。
你的任务是根据下述给定的已知信息回答用户问题。
确保你的回复完全依据下述已知信息。不要编造答案。
如果下述已知信息不足以回答用户的问题，请直接回复"我无法回答您的问题"。"""

app = FastAPI(title="Agent Service API", description="多轮对话服务")
app.include_router(kb_router)
app.include_router(kb_chroma_router)

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
    rag_collection: Optional[str] = None
    rag_top_n: int = Field(5, ge=1, le=50, description="检索返回的候选块数量上限")
    rag_similarity_threshold: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="最小余弦相似度（1 - Chroma cosine distance）；0 表示仅按 TOP N 取块，不做阈值过滤",
    )


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


class OllamaNativeChatRequest(BaseModel):
    """直接调用 Ollama Chat API（非 LangChain），与 /chat 独立。"""

    model: Optional[str] = None
    messages: list[dict]


class OllamaNativeChatResponse(BaseModel):
    model: str
    role: str
    content: str


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


def format_rag_user_content(contents: str, user_query: str) -> str:
    return (
        f"已知信息:\n{contents}\n\n----\n用户问：\n{user_query}\n\n请用中文回答用户问题。"
    )


def build_llm_messages_for_turn(
    prior_history: list[BaseMessage],
    current_user_text: str,
    rag_collection: Optional[str],
    rag_top_n: int,
    rag_similarity_threshold: float,
) -> list[BaseMessage]:
    """构造本轮发往模型的消息列表；历史仅为用户原话与助手回复，不含 RAG 拼装文本。"""
    prior_sw = apply_sliding_window(list(prior_history))
    use_rag = rag_collection is not None and rag_collection.strip() != ""
    if use_rag:
        try:
            chunks = chroma_rag_retrieve_chunks(
                rag_collection.strip(),
                current_user_text,
                rag_top_n,
                rag_similarity_threshold,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except RuntimeError as e:
            raise HTTPException(status_code=502, detail=str(e)) from e
        contents = (
            "\n\n---\n\n".join(chunks)
            if chunks
            else "（检索无符合阈值的文档片段。）"
        )
        return [
            SystemMessage(content=RAG_SYSTEM_INSTRUCTION),
            *prior_sw,
            HumanMessage(content=format_rag_user_content(contents, current_user_text)),
        ]
    return [*prior_sw, HumanMessage(content=current_user_text)]


@app.get("/")
async def root():
    return {"message": "欢迎使用 Agent Service API", "docs": "/docs"}


@app.get("/ollama/models")
async def ollama_list_models():
    """列出本机 Ollama 已安装的模型（直连 Ollama HTTP API）。"""
    try:
        client = OllamaClient(host=get_ollama_base_url(), timeout=OLLAMA_CHAT_HTTP_TIMEOUT_SEC)
        lst = client.list()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"连接 Ollama 失败：{e}") from e

    items: list[dict] = []
    if lst.models is not None:
        for m in lst.models:
            entry: dict = {"name": m.model}
            if getattr(m, "size", None) is not None:
                entry["size"] = m.size
            if getattr(m, "digest", None) is not None:
                entry["digest"] = m.digest
            if getattr(m, "modified_at", None) is not None:
                entry["modified_at"] = str(m.modified_at)
            items.append(entry)
    return {"models": items, "base_url": get_ollama_base_url()}


@app.post("/ollama/chat", response_model=OllamaNativeChatResponse)
async def ollama_native_chat(body: OllamaNativeChatRequest):
    """使用 Ollama 原生 ``chat`` 接口完成一轮/多轮消息（由调用方传入 messages）。"""
    if not body.messages:
        raise HTTPException(status_code=400, detail="messages 不能为空")

    model = (body.model or "").strip() or get_ollama_chat_model()
    try:
        client = OllamaClient(host=get_ollama_base_url(), timeout=OLLAMA_CHAT_HTTP_TIMEOUT_SEC)
        resp = client.chat(model=model, messages=body.messages, stream=False)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ollama 对话失败：{e}") from e

    msg = resp.message
    if msg is None:
        raise HTTPException(status_code=502, detail="Ollama 返回无 message 字段")
    role = msg.role if msg.role is not None else "assistant"
    content = msg.content if msg.content is not None else ""
    return OllamaNativeChatResponse(model=model, role=role, content=content)


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """处理聊天请求，支持多轮对话（非流式）"""
    global llm_instance
    
    if llm_instance is None:
        llm_instance = build_chat_llm()

    try:
        if request.history:
            prior = dict_to_messages(request.history)
        else:
            prior = message_store.get_messages(request.session_id)
        prior = list(prior)

        to_model = build_llm_messages_for_turn(
            prior,
            request.message,
            request.rag_collection,
            request.rag_top_n,
            request.rag_similarity_threshold,
        )

        response = llm_instance.invoke(to_model)
        reply = response.content if response.content is not None else ""

        history = prior + [
            HumanMessage(content=request.message),
            AIMessage(content=reply),
        ]
        history = apply_sliding_window(history)
        message_store.update_messages(request.session_id, history)

        return ChatResponse(reply=reply, history=messages_to_dict(history))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"对话失败：{str(e)}")


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """处理聊天请求，流式响应（SSE）"""
    global llm_instance
    
    if llm_instance is None:
        llm_instance = build_chat_llm()

    if request.history:
        prior = dict_to_messages(request.history)
    else:
        prior = message_store.get_messages(request.session_id)
    prior = list(prior)

    try:
        to_model = build_llm_messages_for_turn(
            prior,
            request.message,
            request.rag_collection,
            request.rag_top_n,
            request.rag_similarity_threshold,
        )
    except HTTPException:
        raise

    async def generate() -> AsyncGenerator[str, None]:
        """生成器：流式输出 AI 回复"""
        full_reply = ""
        try:
            for chunk in llm_instance.stream(to_model):
                if chunk.content:
                    full_reply += chunk.content
                    # SSE 格式发送数据块
                    data = json.dumps({"content": chunk.content, "done": False}, ensure_ascii=False)
                    yield f"data: {data}\n\n"
            
            # 发送完成信号
            data = json.dumps({"content": "", "done": True}, ensure_ascii=False)
            yield f"data: {data}\n\n"
            
            done_history = prior + [
                HumanMessage(content=request.message),
                AIMessage(content=full_reply),
            ]
            done_history = apply_sliding_window(done_history)
            message_store.update_messages(request.session_id, done_history)

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
