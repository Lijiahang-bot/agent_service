# -*- coding: utf-8 -*-
"""模型 ID、服务端点与环境变量集中定义。业务代码由此读取配置，避免散落硬编码。

环境变量一览：
- DASHSCOPE_API_KEY：百炼 API Key（对话）
- CHAT_LLM_BACKEND：主对话 LLM 来源，dashscope（默认）或 ollama
- CHAT_MODEL：百炼兼容接口下的模型名（默认见 CHAT_MODEL 常量）
- OLLAMA_CHAT_MODEL：CHAT_LLM_BACKEND=ollama 时使用的本地模型名
- DASHSCOPE_COMPAT_BASE_URL：百炼兼容 OpenAI 端点（可选覆盖）
- API_BASE_URL：前端/脚本请求本仓库 FastAPI 的根地址，默认 http://localhost:8000
- OLLAMA_BASE_URL：Ollama 服务地址，默认 http://127.0.0.1:11434
- OLLAMA_EMBED_MODEL：嵌入模型名，默认 bge-m3
- OLLAMA_EMBED_BATCH_SIZE：嵌入批大小，默认 10
- MILVUS_DB_PATH：Milvus Lite 本地库路径
- CHROMA_DB_PATH：Chroma 持久化目录
- KB_COLLECTION：知识库集合名，默认 kb_documents
- KB_EMBEDDING_DIM：向量维度，默认 1024（需与嵌入模型一致）
"""
from __future__ import annotations

import os
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from langchain_openai import ChatOpenAI

# ---------------------------------------------------------------------------
# 环境变量名
# ---------------------------------------------------------------------------
ENV_DASHSCOPE_API_KEY = "DASHSCOPE_API_KEY"
ENV_API_BASE_URL = "API_BASE_URL"

ENV_OLLAMA_BASE_URL = "OLLAMA_BASE_URL"
ENV_OLLAMA_EMBED_MODEL = "OLLAMA_EMBED_MODEL"
ENV_OLLAMA_EMBED_BATCH_SIZE = "OLLAMA_EMBED_BATCH_SIZE"
ENV_OLLAMA_CHAT_MODEL = "OLLAMA_CHAT_MODEL"
ENV_CHAT_LLM_BACKEND = "CHAT_LLM_BACKEND"
ENV_CHAT_MODEL = "CHAT_MODEL"
ENV_DASHSCOPE_COMPAT_BASE_URL = "DASHSCOPE_COMPAT_BASE_URL"

ENV_MILVUS_DB_PATH = "MILVUS_DB_PATH"
ENV_CHROMA_DB_PATH = "CHROMA_DB_PATH"
ENV_KB_COLLECTION = "KB_COLLECTION"
ENV_KB_EMBEDDING_DIM = "KB_EMBEDDING_DIM"

# 阿里的通义千问大模型（主要使用）
#    官网: https://bailian.console.aliyun.com/#/home
ALI_TONGYI_API_KEY_OS_VAR_NAME = "DASHSCOPE_API_KEY"
ALI_TONGYI_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
ALI_TONGYI_MAX_MODEL = "qwen3.6-plus"
ALI_TONGYI_TURBO_MODEL = "qwen3.6-plus"
ALI_TONGYI_DEEPSEEK_R1 = "deepseek-r1"
ALI_TONGYI_DEEPSEEK_R10528 = "deepseek-r1-0528"
ALI_TONGYI_DEEPSEEK_V3 = "deepseek-v3.1"
ALI_TONGYI_REASONER_MODEL = "qvq-max-latest"
ALI_TONGYI_EMBEDDING_V3 = "text-embedding-v3"
ALI_TONGYI_EMBEDDING_V4 = "text-embedding-v4"

# DeepSeek
#   官网：https://platform.deepseek.com/api_keys
DEEPSEEK_API_KEY_OS_VAR_NAME = "DEEPSEEK_API_KEY"
DEEPSEEK_URL = "https://api.deepseek.com/v1"
DEEPSEEK_CHAT_MODEL = "deepseek-chat"
DEEPSEEK_REASONER_MODEL = "deepseek-reasoner"

# ---------------------------------------------------------------------------
# 对话：阿里云百炼兼容 OpenAI（LangChain ChatOpenAI）
# ---------------------------------------------------------------------------
CHAT_MODEL = "qwen3.5-flash"
DASHSCOPE_COMPAT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
# 新加坡地域可改为：https://dashscope-intl.aliyuncs.com/compatible-mode/v1

# ---------------------------------------------------------------------------
# Ollama（嵌入等）
# ---------------------------------------------------------------------------
DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_EMBED_MODEL = "bge-m3"
DEFAULT_OLLAMA_EMBED_BATCH_SIZE = 10
DEFAULT_OLLAMA_CHAT_MODEL = "qwen3:1.7b"
OLLAMA_OPENAI_COMPAT_KEY = "ollama"
OLLAMA_CLIENT_TIMEOUT_SEC = 600.0
OLLAMA_CHAT_HTTP_TIMEOUT_SEC = 120.0

DEFAULT_CHAT_LLM_BACKEND = OLLAMA_OPENAI_COMPAT_KEY# "dashscope"

# ---------------------------------------------------------------------------
# 知识库向量存储
# ---------------------------------------------------------------------------
DEFAULT_MILVUS_DB_PATH = "./data/milvus_kb.db"
DEFAULT_CHROMA_DB_PATH = "./data/chroma_kb"
DEFAULT_KB_COLLECTION = "kb_documents"
DEFAULT_KB_EMBEDDING_DIM = 1024

# ---------------------------------------------------------------------------
# 前端 / 脚本访问后端
# ---------------------------------------------------------------------------
DEFAULT_API_BASE_URL = "http://localhost:8000"


def get_dashscope_api_key() -> Optional[str]:
    raw = os.getenv(ENV_DASHSCOPE_API_KEY)
    if raw is None:
        return None
    if raw == "":
        return None
    return raw


def get_api_base_url() -> str:
    return os.getenv(ENV_API_BASE_URL, DEFAULT_API_BASE_URL).rstrip("/")


def get_ollama_base_url() -> str:
    return os.getenv(ENV_OLLAMA_BASE_URL, DEFAULT_OLLAMA_BASE_URL).rstrip("/")


def get_ollama_embed_model() -> str:
    return os.getenv(ENV_OLLAMA_EMBED_MODEL, DEFAULT_OLLAMA_EMBED_MODEL)


def get_ollama_embed_batch_size() -> int:
    return max(1, int(os.getenv(ENV_OLLAMA_EMBED_BATCH_SIZE, str(DEFAULT_OLLAMA_EMBED_BATCH_SIZE))))


def get_milvus_db_path() -> str:
    return os.getenv(ENV_MILVUS_DB_PATH, DEFAULT_MILVUS_DB_PATH)


def get_chroma_db_path() -> str:
    return os.getenv(ENV_CHROMA_DB_PATH, DEFAULT_CHROMA_DB_PATH)


def get_kb_collection_default() -> str:
    return os.getenv(ENV_KB_COLLECTION, DEFAULT_KB_COLLECTION)


def get_kb_embedding_dim() -> int:
    return int(os.getenv(ENV_KB_EMBEDDING_DIM, str(DEFAULT_KB_EMBEDDING_DIM)))


def get_dashscope_compat_base_url() -> str:
    return os.getenv(ENV_DASHSCOPE_COMPAT_BASE_URL, DASHSCOPE_COMPAT_BASE_URL).rstrip("/")


def get_chat_model_id() -> str:
    """百炼兼容模式下的对话模型名（可通过环境变量 CHAT_MODEL 覆盖）。"""
    raw = os.getenv(ENV_CHAT_MODEL, CHAT_MODEL)
    if raw is None or str(raw).strip() == "":
        return CHAT_MODEL
    return str(raw).strip()


def get_ollama_chat_model() -> str:
    raw = os.getenv(ENV_OLLAMA_CHAT_MODEL, DEFAULT_OLLAMA_CHAT_MODEL)
    if raw is None or str(raw).strip() == "":
        return DEFAULT_OLLAMA_CHAT_MODEL
    return str(raw).strip()


def get_chat_llm_backend() -> str:
    """返回 dashscope 或 ollama（小写）。"""
    raw = os.getenv(ENV_CHAT_LLM_BACKEND, DEFAULT_CHAT_LLM_BACKEND)
    if raw is None or str(raw).strip() == "":
        return DEFAULT_CHAT_LLM_BACKEND
    return str(raw).strip().lower()


def build_chat_llm() -> ChatOpenAI:
    """构建主对话用 LangChain ChatOpenAI 实例。

    - ``CHAT_LLM_BACKEND=dashscope``（默认）：百炼兼容 OpenAI 接口。
    - ``CHAT_LLM_BACKEND=ollama``：本机 Ollama 的 ``/v1`` OpenAI 兼容端点。
    """
    from langchain_openai import ChatOpenAI

    backend = get_chat_llm_backend()
    if backend == "ollama":
        print("当前使用的模型为ollama本地部署模型")
        base = get_ollama_base_url().rstrip("/")
        return ChatOpenAI(
            model=get_ollama_chat_model(),
            api_key=OLLAMA_OPENAI_COMPAT_KEY,
            base_url=f"{base}/v1",
        )
    return ChatOpenAI(
        model=get_chat_model_id(),
        api_key=get_dashscope_api_key(),
        base_url=get_dashscope_compat_base_url(),
    )
