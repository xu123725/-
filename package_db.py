import sys
import os
import shutil
from pathlib import Path

# 添加 SmartQbank_Project 到路径最前面，确保导入的是本项目内的 config
BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR / "SmartQbank_Project"
sys.path.insert(0, str(PROJECT_DIR))
sys.path.insert(0, str(BASE_DIR)) # 也添加根目录

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    from db.database import SQLALCHEMY_DATABASE_URL, engine as source_engine
    from db.models import Base
except ImportError as e:
    print(f"错误: 缺少必要的依赖项 ({e})。请确保已安装 requirements.txt 中的包。")
    sys.exit(1)

# 目标 SQLite 数据库路径
TARGET_DB_PATH = BASE_DIR / "smart_qbank.db"
TARGET_DATABASE_URL = f"sqlite:///{TARGET_DB_PATH}"

def package_database():
    print("=" * 50)
    print("正在开始数据库打包流程...")
    print(f"当前主数据库 URL: {SQLALCHEMY_DATABASE_URL}")
    print(f"目标打包文件路径: {TARGET_DB_PATH}")
    print("=" * 50)

    # 如果目标文件已存在，先删除
    if TARGET_DB_PATH.exists():
        try:
            TARGET_DB_PATH.unlink()
            print(f"已清理旧的 {TARGET_DB_PATH}")
        except Exception as e:
            print(f"无法清理旧文件: {e}")
            sys.exit(1)

    # 1. 创建目标 SQLite 引擎和表结构
    target_engine = create_engine(TARGET_DATABASE_URL)
    try:
        Base.metadata.create_all(bind=target_engine)
        print("成功在 SQLite 中创建表结构。")
    except Exception as e:
        print(f"创建 SQLite 表结构失败: {e}")
        # 如果是因为连接主库失败（比如 SQL Server 没开），尝试直接从本地 qbank.db 拷贝
        print("\n检测到无法连接到配置的数据库，尝试从本地 data/db/qbank.db 备份...")
        local_db = BASE_DIR / "SmartQbank_Project" / "data" / "db" / "qbank.db"
        if local_db.exists():
            shutil.copy2(local_db, TARGET_DB_PATH)
            print(f"成功直接从本地文件打包: {TARGET_DB_PATH}")
            return
        else:
            print("未找到本地 qbank.db 文件，打包失败。")
            sys.exit(1)

    # 2. 设置会话
    SourceSession = sessionmaker(bind=source_engine)
    TargetSession = sessionmaker(bind=target_engine)
    
    source_db = SourceSession()
    target_db = TargetSession()

    try:
        # 3. 按表迁移数据
        # 使用 sorted_tables 确保处理外键顺序（虽然当前模型可能没设显式外键）
        for table in Base.metadata.sorted_tables:
            table_name = table.name
            print(f"正在处理表: {table_name}...")
            
            # 从源数据库读取
            try:
                # 使用 SQL 语句查询以避免复杂的 ORM 映射问题
                rows = source_db.execute(text(f"SELECT * FROM {table_name}")).fetchall()
            except Exception as e:
                print(f"  读取表 {table_name} 失败: {e}")
                continue

            if rows:
                # 转换为字典列表
                # SQLAlchemy 1.4/2.0+ 的 Row 对象支持 _mapping
                data = [dict(row._mapping) for row in rows]
                
                # 写入目标数据库
                try:
                    target_db.execute(table.insert(), data)
                    print(f"  成功同步 {len(data)} 条记录。")
                except Exception as e:
                    print(f"  写入表 {table_name} 失败: {e}")
            else:
                print(f"  表 {table_name} 为空，跳过。")
        
        target_db.commit()
        print("\n" + "=" * 50)
        print("数据库打包成功！")
        print(f"打包文件: {TARGET_DB_PATH}")
        print("=" * 50)

    except Exception as e:
        print(f"\n迁移过程中出现错误: {e}")
        target_db.rollback()
    finally:
        source_db.close()
        target_db.close()

if __name__ == "__main__":
    package_database()
