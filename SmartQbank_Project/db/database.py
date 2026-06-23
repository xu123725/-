from __future__ import annotations
import os
import shutil
import time
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from config import DB_DIR, DB_PATH, UPLOAD_DIR, is_web_deploy
from .models import Base

# 支持通过环境变量覆盖数据库连接串，方便 Render 等云端部署
# 本地默认使用 SQL Server 2022
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "mssql+pyodbc://xsy:xsy123@localhost/SmartQbank?driver=ODBC+Driver+17+for+SQL+Server"
)

# 如果是 Render 的 PostgreSQL，其 URL 可能是 postgres:// 需要替换为 postgresql://
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

# 设置 check_same_thread=False 允许 FastAPI 并发使用 SQLite
connect_args = {"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)

# 创建一个配置好的 Session 类
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        # 如果是 SQLite，仍然建议开启 WAL 模式以提升并发读写性能
        if "sqlite" in SQLALCHEMY_DATABASE_URL:
            db.execute("PRAGMA journal_mode=WAL")
        yield db
    finally:
        db.close()

def ensure_dirs() -> None:
    if is_web_deploy():
        return
    from config import DB_DIR, UPLOAD_DIR, RESOURCE_DIR, DATA_DIR
    DB_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    RESOURCE_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

def init_db() -> None:
    if is_web_deploy():
        return
    # 利用 SQLAlchemy 自动创建所有表（如果表不存在）
    Base.metadata.create_all(bind=engine)

def init_app_environment() -> None:
    ensure_dirs()
    init_db()
