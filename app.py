# -*- coding: utf-8 -*-
"""Streamlit 前端界面：简洁美观的多轮对话 Web 应用，支持流式响应"""
import streamlit as st
import requests
import time

# 页面配置
st.set_page_config(
    page_title="AI 智能助手",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API 配置
API_BASE_URL = "http://localhost:8000"

# 自定义 CSS 样式
st.markdown("""
<style>
/* 全局样式 - 使用更柔和的背景和清晰的字体 */
.stApp {
    background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
    font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
}

/* 主容器背景 - 使用浅灰色而不是白色 */
[data-testid="stVerticalBlock"] > div:first-child {
    background-color: rgba(245, 246, 250, 0.95);
    border-radius: 20px;
    margin: 20px auto;
    max-width: 1200px;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
}

/* 聊天容器 */
.chat-container {
    max-width: 900px;
    margin: 0 auto;
    padding: 20px;
}

/* 消息气泡 - 用户消息 */
.user-message {
    background: linear-gradient(135deg, #1a1a1a 0%, #3d3d3d 100%);
    color: #ffffff;
    padding: 14px 20px;
    border-radius: 20px 20px 6px 20px;
    margin: 12px 0;
    max-width: 80%;
    margin-left: auto;
    word-wrap: break-word;
    font-size: 16px;
    line-height: 1.6;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
    text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

/* 消息气泡 - AI 助手消息 */
.assistant-message {
    background-color: #f0f2f5;
    color: #1a1a1a;
    padding: 14px 20px;
    border-radius: 20px 20px 20px 6px;
    margin: 12px 0;
    max-width: 80%;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    word-wrap: break-word;
    font-size: 16px;
    line-height: 1.6;
    border-left: 4px solid #1a1a1a;
}

/* 输入框区域 */
.stChatInput {
    position: sticky;
    bottom: 0;
    background-color: rgba(255, 255, 255, 0.95);
    padding: 20px 0;
    border-top: 1px solid #e0e0e0;
}

/* 输入框样式增强 */
.stChatInput input {
    background-color: #ffffff;
    color: #1a1a1a;
    border: 2px solid #d0d0d0;
    border-radius: 25px;
    padding: 12px 20px;
    font-size: 16px;
    transition: all 0.3s;
}

.stChatInput input:focus {
    border-color: #1a1a1a;
    box-shadow: 0 0 0 3px rgba(26, 26, 26, 0.15);
}

/* 按钮样式 */
.stButton > button {
    background: linear-gradient(135deg, #1a1a1a 0%, #3d3d3d 100%);
    color: white;
    border: none;
    padding: 12px 28px;
    border-radius: 10px;
    font-weight: 600;
    font-size: 15px;
    transition: all 0.3s;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
}

.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.5);
}

.stButton > button:active {
    transform: translateY(0);
}

/* 侧边栏样式 */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #f5f6fa 0%, #e8e9ed 100%);
    color: #1a1a1a;
}

[data-testid="stSidebar"] * {
    color: #1a1a1a !important;
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
    font-size: 2.8rem;
    font-weight: 700;
    margin-bottom: 10px;
    text-shadow: 0 3px 10px rgba(0, 0, 0, 0.3);
    letter-spacing: 1px;
}

.subtitle {
    text-align: center;
    color: rgba(255, 255, 255, 0.9);
    font-size: 1.2rem;
    margin-bottom: 30px;
    font-weight: 300;
    text-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
}

/* Markdown 内容样式 */
.stMarkdown {
    color: #1a1a1a;
    font-size: 16px;
}

.stMarkdown p {
    line-height: 1.8;
    margin-bottom: 1em;
}

/* 侧边栏内的 Markdown 使用深色 */
[data-testid="stSidebar"] .stMarkdown {
    color: #1a1a1a;
}

/* Info 提示框样式 */
.stAlert {
    background-color: rgba(26, 26, 26, 0.1);
    border: 2px solid #1a1a1a;
    border-radius: 10px;
    color: #1a1a1a;
}

/* 侧边栏内的警告框使用不同配色 */
[data-testid="stSidebar"] .stAlert {
    background-color: rgba(255, 255, 255, 0.1);
    border-color: rgba(255, 255, 255, 0.3);
    color: #ffffff;
}

/* Spinner 加载动画 */
.stSpinner > div {
    border-top-color: #1a1a1a;
}

/* 响应式调整 */
@media (max-width: 768px) {
    .user-message, .assistant-message {
        max-width: 90%;
        font-size: 15px;
        padding: 12px 16px;
    }
    
    .main-title {
        font-size: 2.2rem;
    }
    
    .subtitle {
        font-size: 1rem;
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
    background: linear-gradient(135deg, #1a1a1a 0%, #3d3d3d 100%);
    border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
    background: #764ba2;
}

/* 开关控件样式 */
.stToggle > label {
    color: #1a1a1a !important;
    font-weight: 600;
}

.stToggle [data-baseweb="toggle"] {
    background-color: rgba(0, 0, 0, 0.1) !important;
}

.stToggle [data-baseweb="toggle"][aria-checked="true"] {
    background-color: #1a1a1a !important;
}
</style>
""", unsafe_allow_html=True)


def send_message(message: str, session_id: str, history: list) -> tuple:
    """发送消息到后端 API（非流式）"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/chat",
            json={
                "message": message,
                "session_id": session_id,
                "history": history
            },
            timeout=60
        )
        response.raise_for_status()
        data = response.json()
        return data["reply"], data["history"]
    except requests.exceptions.ConnectionError:
        return "❌ 无法连接到服务器，请确保后端服务正在运行（python main.py）", []
    except Exception as e:
        return f"❌ 发生错误：{str(e)}", []


def send_message_stream(message: str, session_id: str, history: list, placeholder) -> tuple:
    """发送消息到后端 API（流式模式）"""
    full_reply = ""
    try:
        with requests.post(
            f"{API_BASE_URL}/chat/stream",
            json={
                "message": message,
                "session_id": session_id,
                "history": history
            },
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
            
            # 更新历史（从后端获取完整历史）
            new_history = list(history)
            new_history.append({"role": "assistant", "content": full_reply})
            return full_reply, new_history
            
    except requests.exceptions.ConnectionError:
        return "❌ 无法连接到服务器，请确保后端服务正在运行", history
    except Exception as e:
        return f"❌ 发生错误：{str(e)}", history


def main():
    """主函数"""
    # 标题区域 - 使用渐变背景
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #1a1a1a 0%, #3d3d3d 100%);
        padding: 40px 20px 30px;
        margin: -20px -20px 30px -20px;
        border-radius: 0 0 30px 30px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    ">
        <div style="text-align: center;">
            <div class="main-title">🤖 AI 智能助手</div>
            <div class="subtitle">基于通义千问的多轮对话系统</div>
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
            
            # 使用说明
            st.markdown('### <span style="color: black; font-weight: 600;">📖 使用说明</span>', unsafe_allow_html=True)
            st.markdown("""
            <div style="color: #1a1a1a; line-height: 2; font-size: 15px;">
            - 💬 在下方输入框输入您的问题<br>
            - 🔄 支持多轮对话，AI 会记住上下文<br>
            - 📝 滑动窗口自动保留最近 10 条消息<br>
            - ⚡ 流式响应模式：逐字显示 AI 回复，体验更流畅<br>
            - ⚙️ 可通过会话 ID 管理不同对话
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
    
    # 聊天消息显示区域 - 使用浅灰色背景容器
    st.markdown("""
    <div style="
        background-color: #f5f6fa;
        border-radius: 20px;
        padding: 30px;
        margin: 20px auto;
        max-width: 1000px;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
        min-height: 400px;
    ">
    </div>
    """, unsafe_allow_html=True)
    
    chat_container = st.container()
    with chat_container:
        if st.session_state.messages:
            for msg in st.session_state.messages:
                if msg["role"] == "user":
                    st.markdown(
                        f'<div class="user-message">{msg["content"]}</div>',
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f'<div class="assistant-message">{msg["content"]}</div>',
                        unsafe_allow_html=True
                    )
        else:
            # 欢迎消息 - 使用更清晰的样式
            st.markdown("""
            <div style="
                background: linear-gradient(135deg, rgba(26, 26, 26, 0.15) 0%, rgba(61, 61, 61, 0.15) 100%);
                border-left: 5px solid #1a1a1a;
                padding: 20px;
                border-radius: 10px;
                margin: 20px auto;
                max-width: 600px;
                text-align: center;
                color: #1a1a1a;
                font-size: 18px;
                line-height: 1.8;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.08);
            ">
            💡 开始提问吧！我会记住我们的对话内容。
            </div>
            """, unsafe_allow_html=True)
    
    # 聊天输入区域 - 使用浅灰色背景容器
    st.markdown("""
    <div style="
        background-color: #f5f6fa;
        border-radius: 20px;
        padding: 20px 30px;
        margin: 20px auto;
        max-width: 1000px;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
    ">
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    # 使用列布局使输入框更美观
    input_col1, input_col2 = st.columns([5, 1])
    
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
                    placeholder
                )
            else:
                # 普通模式
                reply, new_history = send_message(
                    user_input,
                    session_id,
                    st.session_state.history
                )
        
        # 更新历史和消息
        st.session_state.history = new_history
        st.session_state.messages.append({"role": "assistant", "content": reply})
        
        # 重新运行以更新界面
        st.rerun()


if __name__ == "__main__":
    main()
