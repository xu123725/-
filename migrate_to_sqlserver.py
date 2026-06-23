import sqlite3
import pyodbc
from pathlib import Path
import sys

# 1. 数据库配置
SQLITE_DB_PATH = Path("SmartQbank_Project/data/db/qbank.db")

# SQL Server 配置 (如果不是本机，请修改 server 地址)
SQL_SERVER_CONFIG = {
    "server": "localhost",  # 或者 localhost\\SQLEXPRESS
    "database": "SmartQbank",
    "username": "xsy",
    "password": "xsy123",
    # 如果报错找不到驱动，可以在 SSMS 中检查驱动版本，或者改为 {SQL Server}
    "driver": "{ODBC Driver 17 for SQL Server}" 
}

def get_sql_server_conn():
    conn_str = f"DRIVER={SQL_SERVER_CONFIG['driver']};SERVER={SQL_SERVER_CONFIG['server']};DATABASE={SQL_SERVER_CONFIG['database']};UID={SQL_SERVER_CONFIG['username']};PWD={SQL_SERVER_CONFIG['password']}"
    return pyodbc.connect(conn_str)

def create_sql_server_tables(cursor):
    print("正在 SQL Server 中创建表结构...")
    tables_sql = """
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='questions' and xtype='U')
    CREATE TABLE questions (
        id INT IDENTITY(1,1) PRIMARY KEY,
        stem NVARCHAR(MAX) NOT NULL,
        options_json NVARCHAR(MAX) NOT NULL,
        answer NVARCHAR(MAX) NOT NULL,
        question_type NVARCHAR(50) NOT NULL DEFAULT 'single',
        category NVARCHAR(255) NOT NULL,
        tag NVARCHAR(255) DEFAULT '',
        difficulty INT NOT NULL CHECK (difficulty BETWEEN 1 AND 5),
        analysis NVARCHAR(MAX),
        source NVARCHAR(255) DEFAULT '',
        hash_val NVARCHAR(255) NOT NULL UNIQUE,
        last_used_at DATETIME2,
        created_at DATETIME2 NOT NULL DEFAULT SYSDATETIME()
    );

    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='user_logs' and xtype='U')
    CREATE TABLE user_logs (
        id INT IDENTITY(1,1) PRIMARY KEY,
        question_id INT NOT NULL,
        is_correct INT NOT NULL CHECK (is_correct IN (0,1)),
        ts DATETIME2 NOT NULL DEFAULT SYSDATETIME()
    );

    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='wrong_questions' and xtype='U')
    CREATE TABLE wrong_questions (
        id INT IDENTITY(1,1) PRIMARY KEY,
        question_id INT NOT NULL UNIQUE,
        wrong_count INT NOT NULL DEFAULT 1,
        last_wrong_at DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
        is_archived INT NOT NULL DEFAULT 0 CHECK (is_archived IN (0,1)),
        created_at DATETIME2 NOT NULL DEFAULT SYSDATETIME()
    );

    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='imported_files' and xtype='U')
    CREATE TABLE imported_files (
        id INT IDENTITY(1,1) PRIMARY KEY,
        file_name NVARCHAR(255) NOT NULL,
        file_signature NVARCHAR(255) NOT NULL,
        question_count INT NOT NULL DEFAULT 0,
        status NVARCHAR(50) NOT NULL DEFAULT 'done',
        stage NVARCHAR(50) NOT NULL DEFAULT 'done',
        error_code NVARCHAR(255) DEFAULT '',
        last_error NVARCHAR(MAX) DEFAULT '',
        cleanup_done INT NOT NULL DEFAULT 0,
        imported_at DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
        CONSTRAINT UQ_imported_files UNIQUE(file_name, file_signature)
    );
    
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='knowledge_base' and xtype='U')
    CREATE TABLE knowledge_base (
        id INT IDENTITY(1,1) PRIMARY KEY,
        title NVARCHAR(255),
        content NVARCHAR(MAX) NOT NULL,
        category NVARCHAR(255) DEFAULT 'general',
        source NVARCHAR(255),
        created_at DATETIME2 NOT NULL DEFAULT SYSDATETIME()
    );
    
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='troubleshooting' and xtype='U')
    CREATE TABLE troubleshooting (
        id INT IDENTITY(1,1) PRIMARY KEY,
        category NVARCHAR(255) NOT NULL,
        title NVARCHAR(255) NOT NULL,
        video_path NVARCHAR(255),
        doc_path NVARCHAR(255),
        image_path NVARCHAR(255),
        description NVARCHAR(MAX),
        tags NVARCHAR(255),
        created_at DATETIME2 NOT NULL DEFAULT SYSDATETIME()
    );
    """
    cursor.execute(tables_sql)
    cursor.commit()

def migrate_data():
    if not SQLITE_DB_PATH.exists():
        print(f"找不到 SQLite 数据库: {SQLITE_DB_PATH}")
        print("如果你的数据库在其他位置（例如 C盘 AppData 下），请修改 SQLITE_DB_PATH 的路径。")
        sys.exit(1)

    sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cursor = sqlite_conn.cursor()

    try:
        sql_conn = get_sql_server_conn()
        sql_cursor = sql_conn.cursor()
    except Exception as e:
        print(f"连接 SQL Server 失败，请检查账号密码、服务是否开启以及驱动是否正确。\n错误信息: {e}")
        sys.exit(1)

    create_sql_server_tables(sql_cursor)

    # 1. 迁移 questions 表
    print("开始迁移 questions 表...")
    questions = sqlite_cursor.execute("SELECT * FROM questions").fetchall()
    if questions:
        sql_cursor.execute("SET IDENTITY_INSERT questions ON")
        for q in questions:
            try:
                sql_cursor.execute("""
                    INSERT INTO questions (id, stem, options_json, answer, question_type, category, tag, difficulty, analysis, source, hash_val, last_used_at, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (q['id'], q['stem'], q['options_json'], q['answer'], q['question_type'], q['category'], q['tag'], q['difficulty'], q['analysis'], q['source'], q['hash_val'], q['last_used_at'], q['created_at']))
            except pyodbc.IntegrityError:
                pass # 忽略重复
        sql_cursor.execute("SET IDENTITY_INSERT questions OFF")
        sql_cursor.commit()
        print(f"成功迁移 {len(questions)} 道题目！")

    # 2. 迁移 user_logs 表
    print("开始迁移 user_logs 表...")
    user_logs = sqlite_cursor.execute("SELECT * FROM user_logs").fetchall()
    if user_logs:
        sql_cursor.execute("SET IDENTITY_INSERT user_logs ON")
        for q in user_logs:
            try:
                sql_cursor.execute("""
                    INSERT INTO user_logs (id, question_id, is_correct, ts)
                    VALUES (?, ?, ?, ?)
                """, (q['id'], q['question_id'], q['is_correct'], q['ts']))
            except pyodbc.IntegrityError:
                pass
        sql_cursor.execute("SET IDENTITY_INSERT user_logs OFF")
        sql_cursor.commit()
        print(f"成功迁移 {len(user_logs)} 条答题记录！")

    # 3. 迁移 wrong_questions 表
    print("开始迁移 wrong_questions 表...")
    wrong_questions = sqlite_cursor.execute("SELECT * FROM wrong_questions").fetchall()
    if wrong_questions:
        sql_cursor.execute("SET IDENTITY_INSERT wrong_questions ON")
        for q in wrong_questions:
            try:
                sql_cursor.execute("""
                    INSERT INTO wrong_questions (id, question_id, wrong_count, last_wrong_at, is_archived, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (q['id'], q['question_id'], q['wrong_count'], q['last_wrong_at'], q['is_archived'], q['created_at']))
            except pyodbc.IntegrityError:
                pass
        sql_cursor.execute("SET IDENTITY_INSERT wrong_questions OFF")
        sql_cursor.commit()
        print(f"成功迁移 {len(wrong_questions)} 条错题记录！")
        
    # 4. 迁移 imported_files 表
    print("开始迁移 imported_files 表...")
    imported_files = sqlite_cursor.execute("SELECT * FROM imported_files").fetchall()
    if imported_files:
        sql_cursor.execute("SET IDENTITY_INSERT imported_files ON")
        for q in imported_files:
            try:
                sql_cursor.execute("""
                    INSERT INTO imported_files (id, file_name, file_signature, question_count, status, stage, error_code, last_error, cleanup_done, imported_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (q['id'], q['file_name'], q['file_signature'], q['question_count'], q['status'], q['stage'], q['error_code'], q['last_error'], q['cleanup_done'], q['imported_at']))
            except pyodbc.IntegrityError:
                pass
        sql_cursor.execute("SET IDENTITY_INSERT imported_files OFF")
        sql_cursor.commit()
        print(f"成功迁移 {len(imported_files)} 条导入记录！")

    print("数据迁移全部完成！你现在可以在 SSMS 中查看到所有数据了。")
    sqlite_conn.close()
    sql_conn.close()

if __name__ == "__main__":
    migrate_data()