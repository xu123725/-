from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.database import init_db
import config

from routers import qbank, dashboard, chat, exam, wrongbook, settings, troubleshoot

app = FastAPI(
    title="SmartQbank API", 
    description="SmartQbank 后端 API 服务", 
    version="1.0.0"
)

# 配置 CORS，允许前端 Vue 项目跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发阶段允许所有，生产阶段需指定具体域名（如 http://localhost:5173）
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    # 启动时初始化数据库
    init_db()

@app.get("/")
async def root():
    return {"message": "SmartQbank API is running", "status": "ok"}

@app.get("/api/config")
async def get_config():
    """获取系统基础配置"""
    return {
        "openai_api_key_configured": config.get_api_key() is not None,
        "difficulty_ratios": config.DEFAULT_DIFFICULTY_RATIO
    }

# 注册子路由
app.include_router(qbank.router, prefix="/api/qbank", tags=["QBank"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(exam.router, prefix="/api/exam", tags=["Exam"])
app.include_router(wrongbook.router, prefix="/api/wrongbook", tags=["WrongBook"])
app.include_router(settings.router, prefix="/api/settings", tags=["Settings"])
app.include_router(troubleshoot.router, prefix="/api/troubleshoot", tags=["Troubleshoot"])
