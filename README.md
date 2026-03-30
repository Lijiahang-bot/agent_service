# AI 智能助手 - 多轮对话 Web 应用

基于 FastAPI + Streamlit + LangChain 构建的多轮对话系统，支持滑动窗口上下文管理。

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

设置环境变量（推荐）：
```bash
# Windows PowerShell
$env:DASHSCOPE_API_KEY="your-api-key-here"

# 或在代码中直接配置（不推荐用于生产环境）
```

获取 API Key: https://help.aliyun.com/zh/model-studio/get-api-key

### 3. 启动后端服务

```bash
python main.py
```

后端将在 `http://localhost:8000` 启动，API 文档位于 `http://localhost:8000/docs`

### 4. 启动前端界面

打开新的终端窗口：
```bash
streamlit run app.py
```

Streamlit 将自动在浏览器中打开，默认地址为 `http://localhost:8501`

## 📋 功能特性

- ✅ **多轮对话支持**：自动维护对话历史，AI 记住上下文
- ✅ **滑动窗口机制**：保留最近 10 条消息，避免上下文过长
- ✅ **会话管理**：通过 Session ID 管理多个独立对话
- ✅ **响应式布局**：适配桌面和移动设备
- ✅ **简洁美观**：现代化 UI 设计，类似聊天软件的交互体验
- ✅ **实时健康检查**：前端实时监控后端服务状态

## 🛠️ 技术栈

- **后端**: FastAPI + Uvicorn
- **前端**: Streamlit
- **AI 框架**: LangChain + 通义千问 (Qwen3.5-flash)
- **API**: 兼容 OpenAI 接口

## 📝 使用说明

1. 在聊天输入框中输入您的问题
2. AI 会回复并记住对话内容
3. 可以继续追问相关问题（多轮对话）
4. 通过侧边栏的"会话 ID"切换不同对话
5. 点击"清空对话"可重置当前会话

## ⚙️ 配置说明

### 修改模型
编辑 `main.py` 中的 `build_llm()` 函数：
```python
return ChatOpenAI(
    model="qwen3.5-flash",  # 修改为其他模型
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)
```

### 调整滑动窗口大小
编辑 `main.py` 和 `agent_test.py` 中的 `SLIDING_WINDOW` 常量：
```python
SLIDING_WINDOW = 10  # 修改为您想要的消息数量
```

### 修改端口
- **后端**: 编辑 `main.py` 底部，修改 `uvicorn.run()` 的 port 参数
- **前端**: 启动时指定 `streamlit run app.py --server.port=8502`

## 🔌 API 接口

### POST /chat
发送聊天请求

**请求体**:
```json
{
  "message": "你好",
  "session_id": "default",
  "history": []
}
```

**响应**:
```json
{
  "reply": "你好！有什么可以帮助你的？",
  "history": [
    {"role": "user", "content": "你好"},
    {"role": "assistant", "content": "你好！有什么可以帮助你的？"}
  ]
}
```

### GET /health
健康检查接口

## 📄 文件说明

- `main.py` - FastAPI 后端服务
- `app.py` - Streamlit 前端界面
- `agent_test.py` - 原始命令行版本（保留）
- `requirements.txt` - Python 依赖包

## ⚠️ 注意事项

- 生产环境请修改 CORS 配置，限制允许的域名
- 建议使用环境变量管理 API Key，不要硬编码在代码中
- 内存存储会话数据，重启服务后数据会丢失，如需持久化可扩展 MessageStore 类

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！
