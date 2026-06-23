import subprocess
import webbrowser
import time
import sys
import os
import uvicorn
import platform
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR / "SmartQbank_Project"))
def main():
    print("="*60)
    print("\n      SmartQbank 智慧学习平台 (Vue 3 + FastAPI 版)\n")
    print("="*60)
    
    # 1. 自动识别平台，解决 Linux(Render) 找不到 .exe 的问题
    is_windows = platform.system() == "Windows"
    
    # 检测是否运行在 Render 等云端环境（Render 会自带 PORT 环境变量）
    is_cloud = "RENDER" in os.environ or "PORT" in os.environ

    if is_windows:
        venv_python = Path(".venv/Scripts/python.exe")
    else:
        # Linux / macOS 路径 (Render 云端)
        venv_python = Path(".venv/bin/python")

    # 如果在云端，Render 已经帮我们激活并处理好了环境，如果找不到本地 .venv，直接退回到系统 python
    if not venv_python.exists():
        if is_cloud:
            print("[INFO] 未检测到本地 .venv 目录，云端环境自动切换为系统 Python 运行...")
            venv_python = Path(sys.executable)
        else:
            print(f"[错误] 找不到 Python 虚拟环境 ({venv_python})")
            print("请确保已正确安装依赖。")
            # 只有在本地有控制台交互时才使用 input()，防止云端 EOFError
            if not is_cloud:
                input("按回车键退出...")
            return

    processes = []
    
    try:
        # 2. 启动后端 FastAPI (改用 run_api.py)
        print("[1/3] 正在启动后端服务 (FastAPI) ...")
        
        # 如果在云端，我们需要让 FastAPI 监听 0.0.0.0 和云端分配的端口
        if is_cloud:
            port = os.environ.get("PORT", "8000")
            print(f"[INFO] 云端环境检测成功，绑定端口: {port}")
            # 如果你的 run_api.py 内部没有读取 PORT 变量，可以直接在这里用 uvicorn 命令强行拉起
            backend_cmd = [str(venv_python), "run_api.py"] 
        else:
            backend_cmd = [str(venv_python), "run_api.py"]

        p_backend = subprocess.Popen(backend_cmd)
        processes.append(p_backend)
        
        # 如果在云端部署，我们**只需要后端运行**，前端代码通常是单独部署或者已经打包好的。
        # 为了防止 start.py 在云端强行运行前端导致端口冲突或卡死，如果是云端，到这里就可以直接维持运行了。
        if is_cloud:
            print("\n=> 后端服务已在云端就绪！维持主进程监听中...")
            while True:
                # 检查子进程是否挂掉
                if p_backend.poll() is not None:
                    print("[ERROR] 后端子进程意外终止")
                    break
                time.sleep(2)
            return

        # ================= 以下代码仅在本地电脑（Windows/Mac）执行 =================
        
        # 3. 稍微等待后端初始化
        time.sleep(3)
        
        # 4. 启动前端 Vite
        print("[2/3] 正在启动前端服务 (Vite) ...")
        frontend_dir = Path("frontend").resolve()
        
        # 根据系统决定是否开启 shell=True (Windows 下 npm 必须开启)
        p_frontend = subprocess.Popen("npm run dev", cwd=str(frontend_dir), shell=True)
        processes.append(p_frontend)
        
        # 等待前端服务就绪
        print("[3/3] 正在等待前端服务就绪...")
        time.sleep(4)
        
        # 5. 自动打开浏览器
        print("\n=> 服务已就绪！正在打开浏览器...")
        webbrowser.open("http://localhost:5173")
        
        print("\n" + "="*60)
        print("一键启动成功！")
        print("提示: 保持此窗口开启以维持服务运行。按 Ctrl+C 可同时关闭所有服务。")
        print("="*60 + "\n")
        
        # 保持主进程不退出
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n[INFO] 接收到退出指令，正在关闭所有服务...")
    finally:
        print("[INFO] 正在清理子进程...")
        for p in processes:
            try:
                if os.name == 'nt':
                    subprocess.call(['taskkill', '/F', '/T', '/PID', str(p.pid)])
                else:
                    p.terminate()
            except Exception:
                pass
        print("[INFO] 所有服务已关闭。")

if __name__ == "__main__":
    # 优先读取云端分配的端口，如果没有（比如在本地运行）则默认 8000
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main_api:app", host="0.0.0.0", port=port, reload=False) # 云端建议把 reload 改为 False