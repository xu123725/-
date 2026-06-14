from __future__ import annotations
import sqlite3
import shutil
import time
from pathlib import Path

from config import DB_DIR, DB_PATH, UPLOAD_DIR


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def backup_database() -> str:
    """备份数据库到当前目录下的 backups 文件夹"""
    try:
        backup_dir = DB_DIR / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"qbank_backup_{timestamp}.db"
        
        # 使用 sqlite3 的 backup API 进行安全备份
        with get_connection() as src:
            dest = sqlite3.connect(backup_path)
            src.backup(dest)
            dest.close()
            
        return str(backup_path)
    except Exception as e:
        raise Exception(f"数据库备份失败: {str(e)}")


def ensure_dirs() -> None:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _ensure_question_type_column(conn: sqlite3.Connection) -> None:
    cols = [row["name"] for row in conn.execute("PRAGMA table_info(questions)").fetchall()]
    if "question_type" not in cols:
        conn.execute("ALTER TABLE questions ADD COLUMN question_type TEXT NOT NULL DEFAULT 'single'")


def _ensure_imported_files_columns(conn: sqlite3.Connection) -> None:
    cols = [row["name"] for row in conn.execute("PRAGMA table_info(imported_files)").fetchall()]
    if "stage" not in cols:
        conn.execute("ALTER TABLE imported_files ADD COLUMN stage TEXT NOT NULL DEFAULT 'done'")
    if "error_code" not in cols:
        conn.execute("ALTER TABLE imported_files ADD COLUMN error_code TEXT DEFAULT ''")
    if "last_error" not in cols:
        conn.execute("ALTER TABLE imported_files ADD COLUMN last_error TEXT DEFAULT ''")
    if "cleanup_done" not in cols:
        conn.execute("ALTER TABLE imported_files ADD COLUMN cleanup_done INTEGER NOT NULL DEFAULT 0")


def init_db() -> None:
    with get_connection() as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stem TEXT NOT NULL,
                options_json TEXT NOT NULL,
                answer TEXT NOT NULL,
                question_type TEXT NOT NULL DEFAULT 'single',
                category TEXT NOT NULL,
                tag TEXT DEFAULT '',
                difficulty INTEGER NOT NULL CHECK (difficulty BETWEEN 1 AND 5),
                analysis TEXT,
                source TEXT DEFAULT '',
                hash_val TEXT NOT NULL UNIQUE,
                last_used_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id INTEGER NOT NULL,
                is_correct INTEGER NOT NULL CHECK (is_correct IN (0,1)),
                ts TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS imported_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT NOT NULL,
                file_signature TEXT NOT NULL,
                question_count INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'done',
                stage TEXT NOT NULL DEFAULT 'done',
                error_code TEXT DEFAULT '',
                last_error TEXT DEFAULT '',
                cleanup_done INTEGER NOT NULL DEFAULT 0,
                imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(file_name, file_signature)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS wrong_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id INTEGER NOT NULL UNIQUE,
                wrong_count INTEGER NOT NULL DEFAULT 1,
                last_wrong_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                is_archived INTEGER NOT NULL DEFAULT 0 CHECK (is_archived IN (0,1)),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS knowledge_base (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                content TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                source TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # 强制删除旧的 troubleshooting 表，以便重新创建带 image_path 字段的新表
        conn.execute("DROP TABLE IF EXISTS troubleshooting")
        conn.execute(
            """
            CREATE TABLE troubleshooting (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                video_path TEXT,
                doc_path TEXT,
                image_path TEXT,
                description TEXT,
                tags TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # 尝试创建 FTS5 虚拟表用于全文检索
        try:
            conn.execute("DROP TABLE IF EXISTS knowledge_fts")
            conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(content, title, content='knowledge_base', content_rowid='id')")
            # 重新填充现有的知识库数据到 FTS5 虚拟表
            conn.execute("INSERT INTO knowledge_fts(knowledge_fts) VALUES('rebuild')")
            # 创建触发器以保持 FTS 同步
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS knowledge_base_ai AFTER INSERT ON knowledge_base BEGIN
                  INSERT INTO knowledge_fts(rowid, content, title) VALUES (new.id, new.content, new.title);
                END;
            """)
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS knowledge_base_ad AFTER DELETE ON knowledge_base BEGIN
                  INSERT INTO knowledge_fts(knowledge_fts, rowid, content, title) VALUES('delete', old.id, old.content, old.title);
                END;
            """)
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS knowledge_base_au AFTER UPDATE ON knowledge_base BEGIN
                  INSERT INTO knowledge_fts(knowledge_fts, rowid, content, title) VALUES('delete', old.id, old.content, old.title);
                  INSERT INTO knowledge_fts(rowid, content, title) VALUES (new.id, new.content, new.title);
                END;
            """)
        except sqlite3.OperationalError:
            # 如果不支持 FTS5，则忽略
            pass
        
        _ensure_question_type_column(conn)
        _ensure_imported_files_columns(conn)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_questions_category ON questions(category)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_questions_difficulty ON questions(difficulty)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_questions_tag ON questions(tag)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_questions_source ON questions(source)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_questions_type ON questions(question_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_user_logs_qid ON user_logs(question_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_user_logs_correct ON user_logs(is_correct)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_imported_files_name ON imported_files(file_name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_wrong_questions_last_wrong ON wrong_questions(last_wrong_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_wrong_questions_count ON wrong_questions(wrong_count)")
        conn.commit()


def init_app_environment() -> None:
    ensure_dirs()
    init_db()
