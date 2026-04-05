# -*- coding: utf-8 -*-
"""知识库导入：解析多类型文件 → Ollama(bge-m3) 向量化 → Milvus Lite 落库。

环境变量与默认模型见 models 模块。"""
from __future__ import annotations

import io
import threading
from pathlib import Path
from typing import Optional

import pandas as pd
from ollama import Client as OllamaClient
from ollama import ResponseError as OllamaResponseError
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from pypdf import PdfReader
from pymilvus import MilvusClient
from langchain_text_splitters import RecursiveCharacterTextSplitter

from models import (
    ENV_KB_COLLECTION,
    ENV_KB_EMBEDDING_DIM,
    OLLAMA_CLIENT_TIMEOUT_SEC,
    get_kb_collection_default,
    get_kb_embedding_dim,
    get_milvus_db_path,
    get_ollama_base_url,
    get_ollama_embed_batch_size,
    get_ollama_embed_model,
)

router = APIRouter(prefix="/kb", tags=["knowledge-base"])

_milvus_lock = threading.Lock()
_milvus_client: Optional[MilvusClient] = None


def get_milvus_client() -> MilvusClient:
    global _milvus_client
    with _milvus_lock:
        if _milvus_client is None:
            path = get_milvus_db_path()
            parent = Path(path).parent
            if str(parent) not in (".", ""):
                parent.mkdir(parents=True, exist_ok=True)
            _milvus_client = MilvusClient(uri=path)
        return _milvus_client


def _file_kind(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext in (".txt", ".md", ".markdown"):
        return "text"
    if ext == ".csv":
        return "csv"
    if ext in (".xlsx", ".xls"):
        return "excel"
    if ext == ".pdf":
        return "pdf"
    raise ValueError(f"不支持的文件类型：{ext}")


def _read_csv_bytes(raw: bytes) -> pd.DataFrame:
    last_err: Optional[Exception] = None
    for enc in ("utf-8", "utf-8-sig", "gbk", "latin-1"):
        try:
            return pd.read_csv(io.BytesIO(raw), encoding=enc)
        except Exception as e:
            last_err = e
    if last_err is not None:
        raise last_err
    raise RuntimeError("CSV 解析失败")


def _dataframe_to_lines(df: pd.DataFrame) -> str:
    lines = []
    for _, row in df.iterrows():
        parts = []
        for k, v in row.items():
            if pd.notna(v):
                parts.append(f"{k}: {v}")
        if parts:
            lines.append(" | ".join(parts))
    return "\n".join(lines)


def _extract_text(filename: str, raw: bytes) -> str:
    kind = _file_kind(filename)
    if kind == "text":
        return raw.decode("utf-8", errors="replace")
    if kind == "csv":
        df = _read_csv_bytes(raw)
        return _dataframe_to_lines(df)
    if kind == "excel":
        df = pd.read_excel(io.BytesIO(raw))
        return _dataframe_to_lines(df)
    if kind == "pdf":
        reader = PdfReader(io.BytesIO(raw))
        parts = []
        for page in reader.pages:
            t = page.extract_text()
            if t is not None and t.strip():
                parts.append(t)
        return "\n".join(parts)
    return ""


def _chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """使用 LangChain RecursiveCharacterTextSplitter 进行文本分块。"""
    text = text.strip()
    if not text:
        return []
    if chunk_size <= 0:
        raise ValueError("chunk_size 必须为正整数")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap 必须小于 chunk_size")
    
    # 使用 LangChain 的递归字符分块器，支持中英混排分隔符
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ""],
        length_function=len,
    )
    chunks = splitter.split_text(text)
    print(f"分块数量：{len(chunks)}")
    # 打印分块数据
    for i, chunk in enumerate(chunks):
        print(f"分块 {i+1}/{len(chunks)}：{len(chunk)} 字")
        print(chunk)
    return chunks


def _embed_ollama(texts: list[str]) -> list[list[float]]:
    """使用 ollama 官方客户端 embed，按配置的批大小分批请求。"""
    base = get_ollama_base_url()
    model = get_ollama_embed_model()
    batch_size = get_ollama_embed_batch_size()
    all_vectors: list[list[float]] = []
    client = OllamaClient(host=base, timeout=OLLAMA_CLIENT_TIMEOUT_SEC)
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        print(f"当前为第{i}开始的")
        resp = client.embed(model=model, input=batch)
        embs = resp.embeddings
        if embs is None:
            raise RuntimeError("Ollama 响应中缺少 embeddings 字段")
        if len(embs) != len(batch):
            raise RuntimeError(
                f"Ollama 返回嵌入条数 {len(embs)} 与当前批次 {len(batch)} 不一致"
            )
        all_vectors.extend([list(vec) for vec in embs])
    return all_vectors


def _ensure_collection(client: MilvusClient, name: str, dim: int) -> None:
    if client.has_collection(name):
        return
    client.create_collection(
        collection_name=name,
        dimension=dim,
        metric_type="COSINE",
        auto_id=True,
        enable_dynamic_field=True,
    )


class KbImportResponse(BaseModel):
    ok: bool = True
    collection: str
    filename: str
    file_type: str
    chunks: int = Field(description="分块数量")
    inserted: int = Field(description="写入 Milvus 的条数")


@router.post("/import", response_model=KbImportResponse)
async def kb_import(
    file: UploadFile = File(..., description="待导入文件：txt/md/csv/xlsx/xls/pdf"),
    collection_name: Optional[str] = Form(None, description=f"Milvus 集合名，默认取环境变量 {ENV_KB_COLLECTION}"),
    chunk_size: int = Form(800, ge=100, le=32000, description="单块最大字符数"),
    chunk_overlap: int = Form(100, ge=0, description="块之间重叠字符数，须小于 chunk_size"),
):
    """上传文件：解析 → 分块 → Ollama 向量化 → 写入 Milvus Lite。"""
    filename = file.filename or "unknown"
    try:
        kind = _file_kind(filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="空文件")

    try:
        full_text = _extract_text(filename, raw)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"文件解析失败：{e}") from e

    if not full_text.strip():
        raise HTTPException(status_code=400, detail="解析后无文本内容，无法向量化")

    if chunk_overlap >= chunk_size:
        raise HTTPException(status_code=400, detail="chunk_overlap 必须小于 chunk_size")

    chunks = _chunk_text(full_text, chunk_size, chunk_overlap)
    if not chunks:
        raise HTTPException(status_code=400, detail="分块结果为空")

    dim = get_kb_embedding_dim()
    coll = (collection_name or get_kb_collection_default()).strip() or get_kb_collection_default()

    try:
        vectors = _embed_ollama(chunks)
    except OllamaResponseError as e:
        err_text = str(e.error) if e.error is not None else str(e)
        raise HTTPException(
            status_code=502,
            detail=f"Ollama 嵌入失败：{e.status_code} {err_text[:500]}",
        ) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ollama 嵌入失败：{e}") from e

    if len(vectors) != len(chunks):
        raise HTTPException(status_code=500, detail="向量数量与分块数量不一致")

    for v in vectors:
        if len(v) != dim:
            raise HTTPException(
                status_code=500,
                detail=f"向量维度为 {len(v)}，与 {ENV_KB_EMBEDDING_DIM}={dim} 不一致，请调整环境变量",
            )

    try:
        client = get_milvus_client()
        _ensure_collection(client, coll, dim)
        rows = []
        for i, (chunk, vec) in enumerate(zip(chunks, vectors)):
            rows.append(
                {
                    "vector": vec,
                    "text": chunk[:65530],
                    "source": filename[:1024],
                    "chunk_index": i,
                    "file_type": kind,
                }
            )
        client.insert(collection_name=coll, data=rows)
        client.flush(coll)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Milvus 写入失败：{e}") from e

    inserted = len(chunks)
    return KbImportResponse(
        collection=coll,
        filename=filename,
        file_type=kind,
        chunks=len(chunks),
        inserted=inserted,
    )
