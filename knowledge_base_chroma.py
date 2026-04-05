# -*- coding: utf-8 -*-
"""知识库导入：解析多类型文件 → Ollama(bge-m3) 向量化 → Chroma 持久化落库（适用于 Windows 等无法使用 Milvus Lite 的环境）。

环境变量与默认模型见 models 模块。"""
from __future__ import annotations

import io
import threading
import uuid
from pathlib import Path
from typing import Optional

import chromadb
import pandas as pd
from ollama import Client as OllamaClient
from ollama import ResponseError as OllamaResponseError
from chromadb.api import ClientAPI
from collections import Counter

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from models import (
    ENV_KB_COLLECTION,
    ENV_KB_EMBEDDING_DIM,
    OLLAMA_CLIENT_TIMEOUT_SEC,
    get_chroma_db_path,
    get_kb_collection_default,
    get_kb_embedding_dim,
    get_ollama_base_url,
    get_ollama_embed_batch_size,
    get_ollama_embed_model,
)

router = APIRouter(prefix="/kb_chroma", tags=["knowledge-base-chroma"])

_chroma_lock = threading.Lock()
_chroma_client: Optional[ClientAPI] = None


def get_chroma_client() -> ClientAPI:
    global _chroma_client
    with _chroma_lock:
        if _chroma_client is None:
            path = get_chroma_db_path()
            parent = Path(path)
            parent.mkdir(parents=True, exist_ok=True)
            _chroma_client = chromadb.PersistentClient(path=str(parent))
        return _chroma_client


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

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ""],
        length_function=len,
    )
    chunks = splitter.split_text(text)
    print(f"分块数量：{len(chunks)}")
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
        # print(f"当前为第{i}开始的")
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


def chroma_rag_retrieve_chunks(
    collection_name: str,
    query_text: str,
    top_n: int,
    similarity_threshold: float,
) -> list[str]:
    """从指定 Chroma 集合中按查询向量做相似检索，返回文档块文本列表（已按相似度过滤、排序）。

    Chroma 使用 cosine 空间时，返回的 distance 越小越相似；近似相似度为 ``1 - distance``。
    ``similarity_threshold`` 为 0 时不过滤，仅取距离最近的 ``top_n`` 条；否则仅保留
    ``(1 - distance) >= similarity_threshold`` 的块（在 top_n 候选内）。
    """
    if top_n < 1 or top_n > 50:
        raise ValueError("top_n 须在 1～50 之间")
    if similarity_threshold < 0 or similarity_threshold > 1:
        raise ValueError("similarity_threshold 须在 0～1 之间")

    coll_name = _normalize_collection_name(collection_name)
    q = (query_text or "").strip()
    if not q:
        raise ValueError("查询文本不能为空")

    try:
        chroma = get_chroma_client()
        collection = chroma.get_collection(name=coll_name)
    except Exception as e:
        raise ValueError(f"知识库「{coll_name}」不存在或无法打开：{e}") from e

    cnt = collection.count()
    if cnt == 0:
        return []

    n_fetch = min(top_n, cnt)
    try:
        vectors = _embed_ollama([q])
    except OllamaResponseError as e:
        err_text = str(e.error) if e.error is not None else str(e)
        raise RuntimeError(f"Ollama 嵌入失败：{e.status_code} {err_text[:500]}") from e
    except Exception as e:
        raise RuntimeError(f"Ollama 嵌入失败：{e}") from e

    dim = get_kb_embedding_dim()
    if len(vectors) != 1 or len(vectors[0]) != dim:
        raise RuntimeError(
            f"查询向量维度异常，期望 {dim}，实际 {len(vectors[0]) if vectors else 0}"
        )

    try:
        res = collection.query(
            query_embeddings=vectors,
            n_results=n_fetch,
            include=["documents", "distances"],
        )
    except Exception as e:
        raise RuntimeError(f"Chroma 检索失败：{e}") from e

    docs = res.get("documents")
    dists = res.get("distances")
    if not docs or not docs[0]:
        return []
    row_docs = docs[0]
    row_dists = dists[0] if dists is not None and len(dists) > 0 and dists[0] is not None else None

    out: list[str] = []
    for i, doc in enumerate(row_docs):
        if doc is None or not str(doc).strip():
            continue
        if row_dists is not None and i < len(row_dists):
            d = float(row_dists[i])
            sim = 1.0 - d
            if similarity_threshold > 0 and sim < similarity_threshold:
                continue
        out.append(str(doc))
    return out


class KbImportResponse(BaseModel):
    ok: bool = True
    collection: str
    filename: str
    file_type: str
    chunks: int = Field(description="分块数量")
    inserted: int = Field(description="写入 Chroma 的条数")


class KbCollectionItem(BaseModel):
    name: str
    document_count: int = Field(description="该集合中文档条数（分块数）")


class KbCollectionsListResponse(BaseModel):
    collections: list[KbCollectionItem]


class KbCollectionCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=256, description="新知识库（集合）名称")


class KbCollectionCreateResponse(BaseModel):
    ok: bool = True
    name: str


class KbSourceFileItem(BaseModel):
    filename: str
    chunks: int = Field(description="该文件对应的分块数量")


class KbSourcesListResponse(BaseModel):
    collection: str
    files: list[KbSourceFileItem]


def _normalize_collection_name(name: str) -> str:
    n = name.strip()
    if not n:
        raise ValueError("知识库名称不能为空")
    if len(n) > 256:
        raise ValueError("知识库名称过长（最多 256 字符）")
    for bad in ("/", "\\", "\x00"):
        if bad in n:
            raise ValueError("知识库名称不能包含路径分隔符或空字符")
    return n


@router.get("/collections", response_model=KbCollectionsListResponse)
async def kb_list_collections():
    """列出当前 Chroma 中全部知识库（集合）及文档条数。"""
    try:
        chroma = get_chroma_client()
        cols = chroma.list_collections()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"列出知识库失败：{e}") from e

    items: list[KbCollectionItem] = []
    for c in cols:
        try:
            coll = chroma.get_collection(name=c.name)
            cnt = coll.count()
        except Exception:
            cnt = 0
        items.append(KbCollectionItem(name=c.name, document_count=cnt))
    items.sort(key=lambda x: x.name)
    return KbCollectionsListResponse(collections=items)


@router.post("/collections", response_model=KbCollectionCreateResponse)
async def kb_create_collection(body: KbCollectionCreateRequest):
    """新建空知识库（集合）；若名称已存在则返回 409。"""
    try:
        coll_name = _normalize_collection_name(body.name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    try:
        chroma = get_chroma_client()
        existing = {x.name for x in chroma.list_collections()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"访问向量库失败：{e}") from e

    if coll_name in existing:
        raise HTTPException(status_code=409, detail=f"知识库「{coll_name}」已存在")

    try:
        chroma.create_collection(name=coll_name, metadata={"hnsw:space": "cosine"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建知识库失败：{e}") from e

    return KbCollectionCreateResponse(ok=True, name=coll_name)


@router.get(
    "/collections/{collection_name}/sources",
    response_model=KbSourcesListResponse,
)
async def kb_list_sources(collection_name: str):
    """列出某知识库下已导入的文件（按 metadata.source 聚合分块数）。"""
    try:
        coll_name = _normalize_collection_name(collection_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    try:
        chroma = get_chroma_client()
        collection = chroma.get_collection(name=coll_name)
    except Exception:
        raise HTTPException(status_code=404, detail=f"知识库「{coll_name}」不存在") from None

    try:
        data = collection.get(include=["metadatas"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取文件列表失败：{e}") from e

    metadatas = data.get("metadatas")
    if metadatas is None:
        metadatas = []

    counts: Counter[str] = Counter()
    for m in metadatas:
        if m is None:
            continue
        src = m.get("source")
        if src is not None and str(src).strip():
            counts[str(src)] += 1

    files = [
        KbSourceFileItem(filename=k, chunks=v)
        for k, v in sorted(counts.items(), key=lambda kv: kv[0].lower())
    ]
    return KbSourcesListResponse(collection=coll_name, files=files)


@router.post("/import", response_model=KbImportResponse)
async def kb_import(
    file: UploadFile = File(..., description="待导入文件：txt/md/csv/xlsx/xls/pdf"),
    collection_name: Optional[str] = Form(None, description=f"Chroma 集合名，默认取环境变量 {ENV_KB_COLLECTION}"),
    chunk_size: int = Form(800, ge=100, le=32000, description="单块最大字符数"),
    chunk_overlap: int = Form(100, ge=0, description="块之间重叠字符数，须小于 chunk_size"),
):
    """上传文件：解析 → 分块 → Ollama 向量化 → 写入 Chroma。"""
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
        chroma = get_chroma_client()
        collection = chroma.get_or_create_collection(
            name=coll,
            metadata={"hnsw:space": "cosine"},
        )
        doc_cap = 65530
        ids = [str(uuid.uuid4()) for _ in chunks]
        metadatas = [
            {
                "source": filename[:1024],
                "chunk_index": i,
                "file_type": kind,
            }
            for i in range(len(chunks))
        ]
        documents = [c[:doc_cap] for c in chunks]
        collection.add(
            ids=ids,
            embeddings=vectors,
            documents=documents,
            metadatas=metadatas,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chroma 写入失败：{e}") from e

    inserted = len(chunks)
    return KbImportResponse(
        collection=coll,
        filename=filename,
        file_type=kind,
        chunks=len(chunks),
        inserted=inserted,
    )
