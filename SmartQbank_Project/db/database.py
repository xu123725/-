from __future__ import annotations
import os
import shutil
import time
from pathlib import Path
from sqlalchemy import create_engine, text  # 【修复】在这里引入了 text
from sqlalchemy.orm import sessionmaker, Session

from config import DB_DIR, DB_PATH, UPLOAD_DIR, is_web_deploy
from .models import Base

# ==================== 1. 数据库连接串自适应改造 ====================
# 检测是否运行在 Render 类似云端环境（Render 会自带 RENDER 或 PORT 环境变量）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 2. 拼接出根目录下 smart_qbank.db 的绝对物理路径
DB_PATH = os.path.join(BASE_DIR, "smart_qbank.db")

# 3. 优先读取环境变量，如果没有，就强制锁定刚刚定位的绝对路径 SQLite
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    SQLALCHEMY_DATABASE_URL = DATABASE_URL
else:
    # 💥 核心：确保不管是本地 Windows 还是线上 Linux，都以绝对路径加载根目录下的数据库
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"


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
            # 【修复】使用 text() 包裹纯文本 SQL 语句，解决 SQLAlchemy 新版严格限制导致的 500 报错
            db.execute(text("PRAGMA journal_mode=WAL"))
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