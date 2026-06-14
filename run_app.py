import os
import sys
from pathlib import Path

# 获取当前脚本所在目录（项目根目录）
current_dir = Path(__file__).resolve().parent
# SmartQbank_Project 目录路径
project_dir = current_dir / "SmartQbank_Project"

# 1. 强力锁定 Flet 本地运行时
flet_exe = current_dir / "flet-windows" / "flet.exe"
if flet_exe.exists():
    abs_path = str(flet_exe.absolute())
    # 某些 Flet 版本要求 FLET_VIEW_PATH 指向包含 flet.exe 的目录
    os.environ["FLET_VIEW_PATH"] = str(flet_exe.parent.absolute())
    os.environ["FLET_VIEW_DIR"] = str(flet_exe.parent.absolute())
    print(f"--- Flet 离线模式已就绪 ---")
    print(f"检测到运行时: {abs_path}")
    print(f"--------------------------")
else:
    print(f"错误: 在 {flet_exe} 找不到 flet.exe")
    sys.exit(1)

# 2. 配置导入环境
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))
os.chdir(project_dir)

# 3. 启动应用
import flet as ft
# 重新导入以确保 main 看到的是最新的环境变量
from main_desktop import main
from config import BASE_DIR

if __name__ == "__main__":
    print("正在启动应用，请稍候...")
    try:
        # 使用 ft.run 启动（第一个参数必须是 main）
        ft.run(main, assets_dir="assets")
    except Exception as e:
        print(f"\n启动异常: {e}")
        if "10060" in str(e):
            print("\n[诊断] Flet 仍然尝试联网下载。请尝试手动运行:")
            print(f"& \"{abs_path}\" (程序生成的 URL)")
