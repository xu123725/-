import subprocess
import webbrowser
import time
import sys
import os
import signal
from pathlib import Path

def main():
    print("="*60)
    print("\n      SmartQbank 智慧学习平台 (Vue 3 + FastAPI 版)\n")
    print("="*60)
    
    # 确定虚拟环境 Python 的路径
    venv_python = Path(".venv/Scripts/python.exe")
    if not venv_python.exists():
        print("[错误] 找不到 Python 虚拟环境 (.venv/Scripts/python.exe)")
        print("请确保已正确安装依赖。")
        input("按回车键退出...")
        return

    processes = []
    
    try:
        # 1. 启动后端 FastAPI
        print("[1/3] 正在启动后端服务 (FastAPI) ...")
        backend_cmd = [str(venv_python), "run_api.py"]
        # 使用 CREATE_NEW_CONSOLE 在新窗口打开，或者直接在当前终端流式输出
        # 这里直接作为子进程运行，并将输出混合到当前控制台
        p_backend = subprocess.Popen(backend_cmd)
        processes.append(p_backend)
        
        # 稍微等待后端初始化
        time.sleep(3)
        
        # 2. 启动前端 Vite
        print("[2/3] 正在启动前端服务 (Vite) ...")
        # 确保进入 frontend 目录执行 npm run dev
        frontend_dir = Path("frontend").resolve()
        # Windows 下 npm 是个 cmd 脚本，所以用 shell=True
        p_frontend = subprocess.Popen("npm run dev", cwd=str(frontend_dir), shell=True)
        processes.append(p_frontend)
        
        # 等待前端服务就绪
        print("[3/3] 正在等待前端服务就绪...")
        time.sleep(4)
        
        # 3. 自动打开浏览器
        print("\n=> 服务已就绪！正在打开浏览器...")
        webbrowser.open("http://localhost:5173")
        
        print("\n" + "="*60)
        print("一键启动成功！")
        print("提示: 保持此窗口开启以维持服务运行。按 Ctrl+C 可同时关闭所有服务。")
        print("="*60 + "\n")
        
        # 保持主进程不退出，监听子进程
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n[INFO] 接收到退出指令，正在关闭所有服务...")
    finally:
        for p in processes:
            try:
                # 发送终止信号
                if os.name == 'nt':
                    subprocess.call(['taskkill', '/F', '/T', '/PID', str(p.pid)])
                else:
                    p.terminate()
            except Exception:
                pass
        print("[INFO] 所有服务已关闭。")

if __name__ == "__main__":
    main()
