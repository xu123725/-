import os
import sys
from pathlib import Path
import uvicorn

# 获取当前脚本所在目录（项目根目录）
current_dir = Path(__file__).resolve().parent
# SmartQbank_Project 目录路径
project_dir = current_dir / "SmartQbank_Project"

# 配置导入环境
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))
os.chdir(project_dir)

if __name__ == "__main__":
    print("正在启动 FastAPI 后端服务...")
    # 注意这里传入的模块名是 main_api:app，因为工作目录已经切换到了 SmartQbank_Project
    uvicorn.run("main_api:app", host="0.0.0.0", port=8000, reload=True)
    