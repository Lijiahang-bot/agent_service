# -*- coding: utf-8 -*-
"""一键启动脚本：同时启动 FastAPI 后端和 Streamlit 前端"""
import subprocess
import sys
import time
import os


def check_env():
    """检查环境变量配置"""
    if not os.getenv("DASHSCOPE_API_KEY"):
        print("⚠️  警告：未设置 DASHSCOPE_API_KEY 环境变量")
        print("请设置环境变量后重新启动：")
        print("  Windows PowerShell: $env:DASHSCOPE_API_KEY=\"your-api-key\"")
        print("  或在代码中直接配置 API Key")
        print()


def start_backend():
    """启动 FastAPI 后端服务（热重载模式）"""
    print("🚀 正在启动 FastAPI 后端服务（热重载模式）...")
    backend_process = subprocess.Popen(
        [sys.executable, "main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    time.sleep(15)  # 等待后端启动（热重载需要更多时间）
    return backend_process


def start_frontend():
    """启动 Streamlit 前端"""
    print("🎨 正在启动 Streamlit 前端界面...")
    frontend_process = subprocess.Popen(
        ["streamlit", "run", "app.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    return frontend_process


def main():
    """主函数"""
    print("=" * 60)
    print("🤖 AI 智能助手 - 多轮对话 Web 应用")
    print("=" * 60)
    print()
    
    check_env()
    
    try:
        # 启动后端
        backend_proc = start_backend()
        
        # 启动前端
        frontend_proc = start_frontend()
        
        print()
        print("✅ 服务启动成功！")
        print()
        print("🔥 热重载已启用：修改代码后会自动重启")
        print()
        print("📱 访问地址:")
        print("   前端界面：http://localhost:8501")
        print("   后端 API:  http://localhost:8000")
        print("   API 文档：http://localhost:8000/docs")
        print()
        print("按 Ctrl+C 停止所有服务")
        print("=" * 60)
        
        # 监控进程
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n🛑 正在停止服务...")
        backend_proc.terminate()
        frontend_proc.terminate()
        backend_proc.wait()
        frontend_proc.wait()
        print("✅ 所有服务已停止")


if __name__ == "__main__":
    main()
