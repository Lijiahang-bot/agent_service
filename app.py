# -*- coding: utf-8 -*-
"""Streamlit 前端界面：简洁美观的多轮对话 Web 应用，支持流式响应"""
import html
import time
from typing import Optional
from urllib.parse import quote

import requests
import streamlit as st

from models import get_api_base_url

# 页面配置
st.set_page_config(
    page_title="AI 智能助手",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API 配置（可用环境变量 API_BASE_URL 覆盖，见 models）
API_BASE_URL = get_api_base_url()

# 自定义 CSS 样式
st.markdown("""
<style>
/* 全局样式 */
.stApp {
    background: radial-gradient(circle at 10% 20%, #2a2a34 0%, #17171f 45%, #121218 100%);
    font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
    color: #e8e8ee;
}

.block-container {
    max-width: 1080px;
    padding-top: 1.2rem;
    padding-bottom: 1.4rem;
}

/* 主面板 */
.main-panel {
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 18px;
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    box-shadow: 0 16px 42px rgba(0, 0, 0, 0.28);
    padding: 1.2rem;
    margin-bottom: 1rem;
}

.panel-title {
    display: flex;
    align-items: center;
    justify-content: space-between;
    color: #f6f7fb;
    margin-bottom: 0.8rem;
}

.panel-title .left {
    font-size: 1.05rem;
    font-weight: 600;
}

.badge {
    background: rgba(255, 255, 255, 0.12);
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 999px;
    padding: 0.24rem 0.7rem;
    font-size: 0.8rem;
    color: #f5f6fa;
}

.chat-scroll {
    max-height: calc(100vh - 320px);
    min-height: 320px;
    overflow-y: auto;
    padding-right: 0.4rem;
}

/* 消息气泡 - 用户消息 */
.user-message {
    background: linear-gradient(135deg, #5a67ff 0%, #7f5af0 100%);
    color: #ffffff;
    padding: 12px 16px;
    border-radius: 20px 20px 6px 20px;
    margin: 10px 0;
    max-width: 80%;
    margin-left: auto;
    word-wrap: break-word;
    font-size: 15px;
    line-height: 1.7;
    box-shadow: 0 6px 18px rgba(70, 67, 255, 0.32);
}

/* 消息气泡 - AI 助手消息 */
.assistant-message {
    background-color: rgba(255, 255, 255, 0.92);
    color: #1d1f2e;
    padding: 12px 16px;
    border-radius: 20px 20px 20px 6px;
    margin: 10px 0;
    max-width: 80%;
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.16);
    word-wrap: break-word;
    font-size: 15px;
    line-height: 1.7;
    border-left: 4px solid #7f5af0;
}

.assistant-message p, .user-message p {
    margin: 0;
}

/* 输入框区域 */
.stChatInput {
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 14px;
    padding: 0.4rem;
}

/* 输入框样式增强 */
.stChatInput input {
    background-color: rgba(255, 255, 255, 0.95);
    color: #1d1f2e;
    border: 1px solid #ced0d8;
    border-radius: 10px;
    padding: 12px 20px;
    font-size: 15px;
    transition: all 0.3s;
}

.stChatInput input:focus {
    border-color: #6e56ff;
    box-shadow: 0 0 0 3px rgba(110, 86, 255, 0.2);
}

/* 按钮样式 */
.stButton > button {
    background: linear-gradient(135deg, #4c57f7 0%, #7f5af0 100%);
    color: white;
    border: none;
    padding: 11px 22px;
    border-radius: 10px;
    font-weight: 600;
    font-size: 14px;
    transition: all 0.3s;
    box-shadow: 0 8px 18px rgba(73, 62, 205, 0.35);
}

.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 10px 22px rgba(73, 62, 205, 0.42);
}

.stButton > button:active {
    transform: translateY(0);
}

/* 侧边栏样式 */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #ffffff 0%, #f4f5fb 100%);
    color: #1d1f2e;
}

[data-testid="stSidebar"] * {
    color: #1d1f2e !important;
}

[data-testid="stSidebar"] input {
    background-color: rgba(255, 255, 255, 0.8);
    border: 1px solid #d0d0d0;
    color: #1a1a1a;
}

/* 标题样式 */
.main-title {
    text-align: center;
    color: #ffffff;
    font-size: 2.5rem;
    font-weight: 700;
    margin-bottom: 10px;
    text-shadow: 0 3px 10px rgba(0, 0, 0, 0.3);
    letter-spacing: 1px;
}

.subtitle {
    text-align: center;
    color: rgba(246, 246, 250, 0.92);
    font-size: 1.06rem;
    margin-bottom: 22px;
    font-weight: 400;
    text-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
}

/* Markdown 内容样式 */
.stMarkdown {
    color: #f2f3f8;
    font-size: 15px;
}

.stMarkdown p {
    line-height: 1.8;
    margin-bottom: 1em;
}

/* 侧边栏内的 Markdown 使用深色 */
[data-testid="stSidebar"] .stMarkdown {
    color: #1d1f2e;
}

/* Info 提示框样式 */
.stAlert {
    background-color: rgba(255, 255, 255, 0.12);
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 10px;
    color: #f2f3f8;
}

/* 侧边栏内的警告框使用不同配色 */
[data-testid="stSidebar"] .stAlert {
    background-color: #ffffff;
    border-color: #e5e8f2;
    color: #1d1f2e;
}

/* Spinner 加载动画 */
.stSpinner > div {
    border-top-color: #6e56ff;
}

/* 响应式调整 */
@media (max-width: 768px) {
    .user-message, .assistant-message {
        max-width: 94%;
        font-size: 15px;
        padding: 12px 16px;
    }
    
    .main-title {
        font-size: 2rem;
    }
    
    .subtitle {
        font-size: 0.95rem;
    }

    .chat-scroll {
        max-height: calc(100vh - 280px);
    }
}

/* 滚动条美化 */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}

::-webkit-scrollbar-track {
    background: rgba(0, 0, 0, 0.05);
    border-radius: 4px;
}

::-webkit-scrollbar-thumb {
    background: linear-gradient(135deg, #4c57f7 0%, #7f5af0 100%);
    border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
    background: #6d4be4;
}

/* 开关控件样式 */
.stToggle > label {
    color: #1d1f2e !important;
    font-weight: 600;
}

.stToggle [data-baseweb="toggle"] {
    background-color: rgba(0, 0, 0, 0.1) !important;
}

.stToggle [data-baseweb="toggle"][aria-checked="true"] {
    background-color: #4c57f7 !important;
}
</style>
""", unsafe_allow_html=True)


def _chat_json_body(
    message: str,
    session_id: str,
    history: list,
    rag_collection: Optional[str],
    rag_top_n: int,
    rag_similarity_threshold: float,
) -> dict:
    body = {
        "message": message,
        "session_id": session_id,
        "history": history,
        "rag_top_n": int(rag_top_n),
        "rag_similarity_threshold": float(rag_similarity_threshold),
    }
    if rag_collection is not None and str(rag_collection).strip() != "":
        body["rag_collection"] = str(rag_collection).strip()
    else:
        body["rag_collection"] = None
    return body


def send_message(
    message: str,
    session_id: str,
    history: list,
    rag_collection: Optional[str] = None,
    rag_top_n: int = 5,
    rag_similarity_threshold: float = 0.0,
) -> tuple:
    """发送消息到后端 API（非流式）"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/chat",
            json=_chat_json_body(
                message,
                session_id,
                history,
                rag_collection,
                rag_top_n,
                rag_similarity_threshold,
            ),
            timeout=60
        )
        response.raise_for_status()
        data = response.json()
        return data["reply"], data["history"]
    except requests.exceptions.ConnectionError:
        return "❌ 无法连接到服务器，请确保后端服务正在运行（python main.py）", []
    except Exception as e:
        return f"❌ 发生错误：{str(e)}", []


def send_message_stream(
    message: str,
    session_id: str,
    history: list,
    placeholder,
    rag_collection: Optional[str] = None,
    rag_top_n: int = 5,
    rag_similarity_threshold: float = 0.0,
) -> tuple:
    """发送消息到后端 API（流式模式）"""
    full_reply = ""
    try:
        with requests.post(
            f"{API_BASE_URL}/chat/stream",
            json=_chat_json_body(
                message,
                session_id,
                history,
                rag_collection,
                rag_top_n,
                rag_similarity_threshold,
            ),
            stream=True,
            timeout=120
        ) as response:
            response.raise_for_status()
            
            # 解析 SSE 数据
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        import json
                        data = json.loads(line_str[6:])  # 去掉 'data: ' 前缀
                        
                        if data.get('error'):
                            return f"❌ 错误：{data['error']}", history
                        
                        if not data.get('done', False):
                            # 追加内容
                            full_reply += data.get('content', '')
                            # 实时更新显示
                            placeholder.markdown(
                                f'<div class="assistant-message">{full_reply}▌</div>',
                                unsafe_allow_html=True
                            )
                            time.sleep(0.05)  # 控制刷新频率
            
            # 完成，移除光标
            placeholder.markdown(
                f'<div class="assistant-message">{full_reply}</div>',
                unsafe_allow_html=True
            )
            
            new_history = list(history)
            new_history.append({"role": "user", "content": message})
            new_history.append({"role": "assistant", "content": full_reply})
            return full_reply, new_history
            
    except requests.exceptions.ConnectionError:
        return "❌ 无法连接到服务器，请确保后端服务正在运行", history
    except Exception as e:
        return f"❌ 发生错误：{str(e)}", history


def kb_fetch_collections() -> list:
    """GET /kb_chroma/collections"""
    r = requests.get(f"{API_BASE_URL}/kb_chroma/collections", timeout=60)
    r.raise_for_status()
    data = r.json()
    cols = data.get("collections")
    if cols is None:
        return []
    return cols


def kb_create_collection(name: str) -> tuple[bool, str]:
    """POST /kb_chroma/collections，返回 (成功, 消息或知识库名)"""
    r = requests.post(
        f"{API_BASE_URL}/kb_chroma/collections",
        json={"name": name},
        timeout=60,
    )
    if r.status_code == 409:
        detail = r.json().get("detail", "知识库已存在")
        return False, str(detail)
    if r.status_code != 200:
        try:
            detail = r.json().get("detail", r.text)
        except Exception:
            detail = r.text
        return False, str(detail)
    j = r.json()
    created = j.get("name", name)
    return True, created


def kb_fetch_sources(collection_name: str) -> tuple[bool, str, list]:
    """GET .../sources，返回 (成功, 错误信息, 文件列表)"""
    enc = quote(collection_name, safe="")
    r = requests.get(
        f"{API_BASE_URL}/kb_chroma/collections/{enc}/sources",
        timeout=120,
    )
    if r.status_code == 404:
        return False, r.json().get("detail", "知识库不存在"), []
    if r.status_code != 200:
        try:
            detail = r.json().get("detail", r.text)
        except Exception:
            detail = r.text
        return False, str(detail), []
    data = r.json()
    files = data.get("files")
    if files is None:
        files = []
    return True, "", files


def kb_import_file(
    collection_name: str,
    filename: str,
    file_bytes: bytes,
    chunk_size: int,
    chunk_overlap: int,
) -> tuple[bool, str]:
    """POST /kb_chroma/import（multipart）"""
    files = {
        "file": (
            filename,
            file_bytes,
            "application/octet-stream",
        )
    }
    data = {
        "collection_name": collection_name,
        "chunk_size": str(chunk_size),
        "chunk_overlap": str(chunk_overlap),
    }
    r = requests.post(
        f"{API_BASE_URL}/kb_chroma/import",
        files=files,
        data=data,
        timeout=600,
    )
    if r.status_code != 200:
        try:
            detail = r.json().get("detail", r.text)
        except Exception:
            detail = r.text
        return False, str(detail)
    j = r.json()
    msg = (
        f"已导入「{j.get('filename', filename)}」至知识库「{j.get('collection', collection_name)}」"
        f"，分块 {j.get('chunks', '?')}，写入 {j.get('inserted', '?')} 条。"
    )
    return True, msg


def main():
    """主函数"""
    # 标题区域
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, rgba(76, 87, 247, 0.95) 0%, rgba(127, 90, 240, 0.95) 55%, rgba(24, 24, 32, 0.95) 100%);
        padding: 30px 24px 24px;
        margin: -8px 0 16px 0;
        border-radius: 16px;
        border: 1px solid rgba(255,255,255,0.15);
        box-shadow: 0 12px 30px rgba(0, 0, 0, 0.28);
    ">
        <div style="text-align: center;">
            <div class="main-title">🤖 AI 智能助手</div>
            <div class="subtitle">更清晰的多轮对话体验 · 支持流式输出</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 侧边栏配置
    with st.sidebar:
        # 使用容器包装内容以确保样式正确
        with st.container():
            st.markdown('### <span style="color: black; font-weight: 600;">⚙️ 设置</span>', unsafe_allow_html=True)
            
            # 会话 ID 管理
            session_id = st.text_input(
                "会话 ID",
                value="default",
                help="不同会话 ID 将保持独立的对话历史"
            )
            
            # 流式响应开关
            use_streaming = st.toggle(
                "⚡ 流式响应",
                value=True,
                help="开启后 AI 回复会逐字显示，体验更流畅；关闭则为等待完整回复后一次性显示"
            )
            
            # 清空对话按钮
            if st.button("🗑️ 清空对话", use_container_width=True):
                if "messages" in st.session_state:
                    st.session_state.messages = []
                if "history" in st.session_state:
                    st.session_state.history = []
                st.rerun()
            
            # 保存流式响应设置到 session_state
            if "use_streaming" not in st.session_state:
                st.session_state.use_streaming = True
            st.session_state.use_streaming = use_streaming
            
            st.divider()
            
            # 知识库（Chroma）
            st.markdown(
                '### <span style="color: black; font-weight: 600;">📚 知识库（Chroma）</span>',
                unsafe_allow_html=True,
            )
            st.caption("创建知识库后可导入 txt / md / csv / xlsx / pdf 等文件（依赖后端 Ollama 嵌入）")

            _kb_ok_flash = st.session_state.pop("kb_flash_success", None)
            if _kb_ok_flash is not None:
                st.success(_kb_ok_flash)
            _kb_err_flash = st.session_state.pop("kb_flash_error", None)
            if _kb_err_flash is not None:
                st.error(_kb_err_flash)

            new_kb_name = st.text_input(
                "新建知识库名称",
                key="kb_new_name_input",
                placeholder="例如：产品说明",
            )
            if st.button("创建知识库", use_container_width=True, key="kb_create_btn"):
                trimmed = (new_kb_name or "").strip()
                if not trimmed:
                    st.warning("请输入知识库名称")
                else:
                    try:
                        ok, info = kb_create_collection(trimmed)
                        if ok:
                            st.session_state["kb_selected"] = info
                            st.session_state["kb_new_name_input"] = ""
                            st.session_state["kb_flash_success"] = f"已创建知识库：{info}"
                            st.rerun()
                        else:
                            st.error(f"创建失败：{info}")
                    except requests.exceptions.ConnectionError:
                        st.error("无法连接后端，请确认已启动 main.py")
                    except Exception as e:
                        st.error(f"创建失败：{e}")

            kb_collections: list = []
            try:
                kb_collections = kb_fetch_collections()
            except requests.exceptions.ConnectionError:
                st.warning("无法加载知识库列表（后端未连接）")
            except Exception as e:
                st.warning(f"加载知识库列表失败：{e}")

            if kb_collections:
                names = [c["name"] for c in kb_collections]
                pref = st.session_state.get("kb_selected")
                if pref is not None and pref in names:
                    sel_index = names.index(pref)
                else:
                    sel_index = 0
                kb_selected = st.selectbox(
                    "当前知识库",
                    options=names,
                    index=sel_index,
                )
                st.session_state["kb_selected"] = kb_selected

                doc_count = next(
                    (c["document_count"] for c in kb_collections if c["name"] == kb_selected),
                    0,
                )
                st.markdown(
                    f'<p style="color:#1a1a1a;font-size:14px;margin:6px 0;">'
                    f'已选：<strong>{html.escape(kb_selected)}</strong> · 分块总数约 <strong>{doc_count}</strong></p>',
                    unsafe_allow_html=True,
                )

                ok_src, err_src, file_rows = kb_fetch_sources(kb_selected)
                if ok_src:
                    if file_rows:
                        st.markdown('<span style="color:#1a1a1a;font-weight:600;">已导入文件</span>', unsafe_allow_html=True)
                        for row in file_rows:
                            fn = row.get("filename", "")
                            ch = row.get("chunks", 0)
                            st.caption(f"· {fn}（{ch} 块）")
                    else:
                        st.caption("该知识库下暂无已导入文件")
                else:
                    st.caption(f"无法列出文件：{err_src}")

                st.markdown('<span style="color:#1a1a1a;font-weight:600;">导入文件</span>', unsafe_allow_html=True)
                kb_chunk_size = st.number_input(
                    "chunk_size（单块最大字符数）",
                    min_value=100,
                    max_value=32000,
                    value=800,
                    key="kb_chunk_size",
                )
                kb_chunk_overlap = st.number_input(
                    "chunk_overlap（块重叠字符数，须小于 chunk_size）",
                    min_value=0,
                    value=100,
                    key="kb_chunk_overlap",
                )
                kb_upload = st.file_uploader(
                    "选择文件",
                    type=["txt", "md", "markdown", "csv", "xlsx", "xls", "pdf"],
                    key="kb_file_uploader",
                )
                if st.button("导入到当前知识库", use_container_width=True, key="kb_import_btn"):
                    if kb_upload is None:
                        st.warning("请先选择要导入的文件")
                    elif kb_chunk_overlap >= kb_chunk_size:
                        st.warning("chunk_overlap 必须小于 chunk_size")
                    else:
                        try:
                            raw = kb_upload.getvalue()
                            with st.spinner("正在解析、分块并向量化，请稍候…"):
                                imp_ok, imp_msg = kb_import_file(
                                    kb_selected,
                                    kb_upload.name,
                                    raw,
                                    int(kb_chunk_size),
                                    int(kb_chunk_overlap),
                                )
                            if imp_ok:
                                st.session_state["kb_flash_success"] = imp_msg
                                st.rerun()
                            else:
                                st.error(f"导入失败：{imp_msg}")
                        except requests.exceptions.ConnectionError:
                            st.error("无法连接后端，请确认已启动 main.py")
                        except Exception as e:
                            st.error(f"导入失败：{e}")
            else:
                st.info("暂无知识库，请先输入名称并点击「创建知识库」")

            st.divider()
            
            # 使用说明
            st.markdown('### <span style="color: black; font-weight: 600;">📖 使用说明</span>', unsafe_allow_html=True)
            st.markdown("""
            <div style="color: #1a1a1a; line-height: 2; font-size: 15px;">
            - 💬 在下方输入框输入您的问题<br>
            - 🔄 支持多轮对话，AI 会记住上下文<br>
            - 📝 滑动窗口自动保留最近 10 条消息<br>
            - ⚡ 流式响应模式：逐字显示 AI 回复，体验更流畅<br>
            - ⚙️ 可通过会话 ID 管理不同对话<br>
            - 📎 主界面可选择知识库开启 RAG，并可调 TOP N 与相似度阈值
            </div>
            """, unsafe_allow_html=True)
            
            st.divider()
            
            # API 状态
            st.markdown('#### <span style="color: black; font-weight: 600;">🔌 API 状态</span>', unsafe_allow_html=True)
            try:
                health_resp = requests.get(f"{API_BASE_URL}/health", timeout=5)
                if health_resp.status_code == 200:
                    st.success("✅ 后端服务正常")
                else:
                    st.error("❌ 后端服务异常")
            except:
                st.error("❌ 无法连接到后端服务")
            
            st.divider()
            st.caption("Powered by LangChain + FastAPI + Streamlit")
    
    # 初始化会话状态
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "history" not in st.session_state:
        st.session_state.history = []
    if "use_streaming" not in st.session_state:
        st.session_state.use_streaming = True  # 默认开启流式响应

    try:
        _rag_cols_list = kb_fetch_collections()
        _rag_names_for_chat = [c["name"] for c in _rag_cols_list]
    except Exception:
        _rag_names_for_chat = []

    _rag_select_options = ["（不使用知识库）"] + _rag_names_for_chat
    st.markdown(
        '<div style="color:#f2f3f8;font-size:1rem;font-weight:600;margin-bottom:8px;">'
        "对话与检索（RAG）</div>",
        unsafe_allow_html=True,
    )
    rag_col1, rag_col2, rag_col3 = st.columns([1.5, 0.75, 1.0])
    with rag_col1:
        _rag_pick = st.selectbox(
            "本对话使用的知识库",
            options=_rag_select_options,
            index=0,
            help="默认不选为普通对话；选定后每轮从该库检索文档块再结合历史回答",
            key="main_rag_kb_select",
        )
    chat_rag_collection: Optional[str] = None
    if _rag_pick != "（不使用知识库）":
        chat_rag_collection = _rag_pick
    with rag_col2:
        chat_rag_top_n = st.number_input(
            "TOP N",
            min_value=1,
            max_value=50,
            value=5,
            disabled=chat_rag_collection is None,
            help="最多检索的候选块数量",
            key="main_rag_top_n",
        )
    with rag_col3:
        chat_rag_sim = st.slider(
            "相似度阈值",
            min_value=0.0,
            max_value=1.0,
            value=0.0,
            step=0.05,
            disabled=chat_rag_collection is None,
            help="0：仅按相似度排序取 TOP N；大于 0：只保留相似度≥该值的块（相似度≈1−Chroma 距离）",
            key="main_rag_sim_threshold",
        )
    st.markdown("---")
    
    # 聊天消息显示区域
    message_count = len(st.session_state.messages)
    st.markdown("""
    <div class="panel-title">
        <div class="left">对话窗口</div>
        <div class="badge">最近消息会被持续记忆</div>
    </div>
    """, unsafe_allow_html=True)
    
    chat_container = st.container()
    with chat_container:
        if st.session_state.messages:
            for msg in st.session_state.messages:
                if msg["role"] == "user":
                    st.markdown(
                        f'<div class="user-message">{html.escape(msg["content"])}</div>',
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f'<div class="assistant-message">{msg["content"]}</div>',
                        unsafe_allow_html=True
                    )
        else:
            # 欢迎消息
            st.markdown("""
            <div style="
                background: rgba(255, 255, 255, 0.92);
                border: 1px solid #dce0ee;
                padding: 18px;
                border-radius: 12px;
                margin: 16px auto;
                max-width: 680px;
                color: #1d1f2e;
                line-height: 1.8;
                box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
            ">
                <div style="font-size: 18px; font-weight: 600; margin-bottom: 8px;">欢迎使用 AI 智能助手</div>
                <div style="font-size: 15px;">输入任何问题即可开始，我会记住当前会话的上下文并连续回答。</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div style="
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 0.55rem;
        margin-bottom: 0.45rem;
        color: rgba(243, 244, 252, 0.92);
        font-size: 13px;
    ">
        <span>当前消息数：{message_count}</span>
        <span>输入后按 Enter 发送</span>
    </div>
    """, unsafe_allow_html=True)
    
    # 使用列布局使输入框更美观
    input_col1, _ = st.columns([10, 1])
    
    with input_col1:
        user_input = st.chat_input("输入您的问题...", key="chat_input")
    
    # 处理用户输入
    if user_input:
        # 添加用户消息到显示列表
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # 创建占位符用于流式显示
        placeholder = st.empty()
        
        # 根据设置选择调用模式
        with st.spinner("🤔 思考中..."):
            if st.session_state.use_streaming:
                # 流式模式
                reply, new_history = send_message_stream(
                    user_input,
                    session_id,
                    st.session_state.history,
                    placeholder,
                    rag_collection=chat_rag_collection,
                    rag_top_n=int(chat_rag_top_n),
                    rag_similarity_threshold=float(chat_rag_sim),
                )
            else:
                # 普通模式
                reply, new_history = send_message(
                    user_input,
                    session_id,
                    st.session_state.history,
                    rag_collection=chat_rag_collection,
                    rag_top_n=int(chat_rag_top_n),
                    rag_similarity_threshold=float(chat_rag_sim),
                )
        
        # 更新历史和消息
        st.session_state.history = new_history
        st.session_state.messages.append({"role": "assistant", "content": reply})
        
        # 重新运行以更新界面
        st.rerun()


if __name__ == "__main__":
    main()
