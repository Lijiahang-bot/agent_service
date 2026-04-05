# AI 智能助手（Agent Service）

基于 **FastAPI + Streamlit + LangChain** 的多轮对话 Web 应用，可选 **Chroma** 知识库（多集合、文件导入、分块参数可配）。配置集中在 `models.py`，便于切换模型与存储路径。

---

## 代码结构

| 路径 | 说明 |
|------|------|
| `main.py` | FastAPI 入口：聊天 `/chat`、`/chat/stream`，健康检查 `/health`；挂载知识库路由 |
| `app.py` | Streamlit 前端：对话界面、侧边栏设置、**知识库（Chroma）** 创建/导入/文件列表 |
| `models.py` | 环境变量名、默认模型与端点、路径与维度的读取函数（对话用百炼兼容接口，知识库用 Ollama 嵌入） |
| `knowledge_base_chroma.py` | Chroma 知识库 API（前缀 `/kb_chroma`）：集合 CRUD 列表、导入文件、按 `source` 聚合文件视图 |
| `knowledge_base.py` | Milvus Lite 知识库 API（前缀 `/kb`）：单一路径导入，适合非 Windows 或选用 Milvus 的场景 |
| `start.py` | 一键同时拉起后端与前端子进程（可选） |
| `agent_test.py` | 命令行对话测试（保留） |
| `ollama_test.py` | Ollama 连通性等小测试（保留） |
| `requirements.txt` | Python 依赖 |
| `data/` | 本地数据目录（如 Chroma / Milvus 持久化，按配置生成，勿提交敏感内容） |

**请求链路简述**：浏览器访问 Streamlit → `app.py` 通过 `API_BASE_URL` 调用 FastAPI → 对话走百炼兼容 OpenAI 接口；知识库导入走 Ollama 嵌入并写入 Chroma。

---

## 功能概览

### 对话

- 多轮对话与历史回传；服务端滑动窗口保留最近 **10** 条消息（`main.py` 中 `SLIDING_WINDOW`）
- 支持 **非流式** `/chat` 与 **SSE 流式** `/chat/stream`
- 按 **会话 ID** 隔离不同对话；前端可清空当前会话展示与历史

### 知识库（Chroma，与 Streamlit 侧边栏联动）

- **新建知识库**：创建独立 Chroma 集合（名称不可与已有重复）
- **列表**：展示所有集合名称及分块总数
- **导入文件**：支持 txt、md、csv、xlsx、xls、pdf；可设置 **chunk_size**、**chunk_overlap**
- **已导入文件列表**：按文件（`metadata.source`）聚合显示块数
- 依赖本机 **Ollama** 与嵌入模型（默认 `bge-m3`，维度需与 `KB_EMBEDDING_DIM` 一致，默认 1024）

### 知识库（Milvus Lite，`/kb`）

- 提供 `POST /kb/import`，将文件导入 Milvus；**无** Streamlit 内置管理界面，需自行调用 API 或扩展前端

---

## 环境要求

- Python 3.10+（推荐，需支持类型标注写法）
- **对话**：阿里云百炼 API Key（`DASHSCOPE_API_KEY`）
- **知识库导入**：Ollama 已安装并拉取嵌入模型（如 `bge-m3`）

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```powershell
# Windows PowerShell（分号分隔多条）
$env:DASHSCOPE_API_KEY="your-api-key"; $env:API_BASE_URL="http://localhost:8000"
```

获取百炼 API Key：<https://help.aliyun.com/zh/model-studio/get-api-key>

**常用可选变量**（详见 `models.py` 顶部注释）：

| 变量 | 含义 | 默认 |
|------|------|------|
| `API_BASE_URL` | 前端请求后端的根地址 | `http://localhost:8000` |
| `CHROMA_DB_PATH` | Chroma 持久化目录 | `./data/chroma_kb` |
| `OLLAMA_BASE_URL` | Ollama 服务地址 | `http://127.0.0.1:11434` |
| `OLLAMA_EMBED_MODEL` | 嵌入模型名 | `bge-m3` |
| `KB_EMBEDDING_DIM` | 向量维度（须与模型一致） | `1024` |
| `KB_COLLECTION` | 仅影响 **未指定集合名** 时的默认集合（如直接调 `/kb_chroma/import`） | `kb_documents` |

### 3. 启动后端

```bash
python main.py
```

服务默认：<http://localhost:8000>，交互文档：<http://localhost:8000/docs>

### 4. 启动前端

新终端：

```bash
streamlit run app.py
```

浏览器默认：<http://localhost:8501>

### 5. 一键启动（可选）

```bash
python start.py
```

会尝试同时启动 `main.py` 与 `streamlit run app.py`；若前端与后端需分开调试，建议仍分终端启动。

---

## 使用说明（Streamlit）

1. **对话**：在主界面输入框发送消息；侧边栏可开关 **流式响应**、修改 **会话 ID**、**清空对话**。
2. **知识库（Chroma）**（侧边栏「知识库（Chroma）」）  
   - 输入名称后点击 **创建知识库**；成功后名称会出现在 **当前知识库** 下拉框中。  
   - 选择知识库后，可查看 **已导入文件** 列表。  
   - 设置 **chunk_size** / **chunk_overlap**，上传文件后点击 **导入到当前知识库**；成功或失败均有页面提示，成功后列表会更新。  
3. **API 状态**：侧边栏展示对 `/health` 的检查结果，便于确认后端是否可达。

---

## API 摘要

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/chat` | 非流式聊天 |
| POST | `/chat/stream` | SSE 流式聊天 |
| GET | `/health` | 健康检查 |
| GET | `/kb_chroma/collections` | 列出 Chroma 集合及文档条数 |
| POST | `/kb_chroma/collections` | 新建集合（JSON：`{"name":"..."}`，重复名 409） |
| GET | `/kb_chroma/collections/{name}/sources` | 某集合下按文件名聚合的分块数 |
| POST | `/kb_chroma/import` | multipart：文件 + `collection_name`、`chunk_size`、`chunk_overlap` |
| POST | `/kb/import` | Milvus 导入（表单字段见 Swagger） |

完整请求/响应模型见 <http://localhost:8000/docs>。

---

## 配置修改提示

- **对话模型**：`models.py` 中 `CHAT_MODEL`；API Key 与 `base_url` 在 `main.py` 的 `build_llm()` 中引用 `models`。
- **滑动窗口长度**：`main.py` 中 `SLIDING_WINDOW`。
- **监听端口**：`main.py` 末尾 `uvicorn.run`；Streamlit 可用 `streamlit run app.py --server.port=8502`。

---

## 注意事项

- 生产环境请收紧 **CORS**（当前 `main.py` 为开发向的宽松配置）。
- **会话历史** 默认在内存中，**重启后端会丢失**；需要持久化可扩展 `MessageStore`。
- 知识库导入耗时与文件大小、Ollama 性能有关；前端对导入请求使用了较长超时。
- Windows 下若 Milvus Lite 不可用，可优先使用 **Chroma** 路径（`knowledge_base_chroma` + 侧边栏）。

---

## 贡献

欢迎提交 Issue 与 Pull Request。
