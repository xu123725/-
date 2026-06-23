from __future__ import annotations
import os
import shutil
import time
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from config import DB_DIR, DB_PATH, UPLOAD_DIR, is_web_deploy
from .models import Base

# ==================== 1. 数据库连接串自适应改造 ====================
# 检测是否运行在 Render 类似云端环境（Render 会自带 RENDER 或 PORT 环境变量）
IS_CLOUD = "RENDER" in os.environ or "PORT" in os.environ

# 获取系统配置的数据库 URL
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # 如果配置了环境变量（如未来升级为云端 PostgreSQL），则使用配置的值
    SQLALCHEMY_DATABASE_URL = DATABASE_URL
    if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)
else:
    if IS_CLOUD:
        # 【关键改动】如果在云端且没配云数据库，自动回退到方案一：使用跟随项目的本地 SQLite
        # 建立在项目根目录下的 smart_qbank.db
        BASE_DIR = Path(__file__).resolve().parent.parent
        sqlite_path = BASE_DIR / "smart_qbank.db"
        print(f"[INFO] 云端环境未检测到远程数据库，自动启用本地 SQLite 存储: {sqlite_path}")
        SQLALCHEMY_DATABASE_URL = f"sqlite:///{sqlite_path}"
    else:
        # 本地开发（Windows）默认依然使用你原本的 SQL Server 2022
        SQLALCHEMY_DATABASE_URL = "mssql+pyodbc://xsy:xsy123@localhost/SmartQbank?driver=ODBC+Driver+17+for+SQL+Server"

# 设置 check_same_thread=False 允许 FastAPI 并发使用 SQLite
connect_args = {"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)

# 创建一个配置好的 Session 类
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        # 如果是 SQLite，开启 WAL 模式以显著提升多用户并发读写性能，防止出现 database is locked
        if "sqlite" in SQLALCHEMY_DATABASE_URL:
            db.execute("PRAGMA journal_mode=WAL")
        yield db
    finally:
        db.close()


def ensure_dirs() -> None:
    # 【改动】即使是 Web 部署，如果使用了本地 SQLite，也需要确保文件夹存在，防止写入时找不到路径
    if is_web_deploy() and not "sqlite" in SQLALCHEMY_DATABASE_URL:
        return
    from config import DB_DIR, UPLOAD_DIR, RESOURCE_DIR, DATA_DIR
    DB_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    RESOURCE_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def init_db() -> None:
    # 【改动】如果是云端使用 SQLite，必须允许在云端初始化数据库和自动创建表
    if is_web_deploy() and not "sqlite" in SQLALCHEMY_DATABASE_URL:
        return
    # 利用 SQLAlchemy 自动创建所有表（如果表不存在）
    Base.metadata.create_all(bind=engine)


def init_app_environment() -> None:
    ensure_dirs()
    init_db()