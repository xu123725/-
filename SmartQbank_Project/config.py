import os
import sys
import json
import shutil
from pathlib import Path
from typing import Any

def get_bundle_dir() -> Path:
    """获取打包后的资源目录 (sys._MEIPASS) 或开发环境目录"""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent

def get_app_path() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent

def is_web_deploy() -> bool:
    """判断是否为 Web 部署环境 (Netlify 等)"""
    return os.environ.get("WEB_DEPLOY") == "true"

def get_data_dir() -> Path:
    app_name = "AutomaticWeatherStationAgent"  # 使用新的内部标识名，避免中文字符路径问题
    if getattr(sys, 'frozen', False):
        # 打包为 .exe 时，使用 AppData/Local/AWS_Agent 避免权限问题
        if os.name == 'nt':
            appdata = os.getenv('LOCALAPPDATA')
            if appdata:
                target_dir = Path(appdata) / app_name / "data"
                # 如果数据库文件不存在，尝试从打包资源中初始化
                db_path = target_dir / "db" / "qbank.db"
                if not db_path.exists():
                    bundle_data = get_bundle_dir() / "data"
                    if bundle_data.exists():
                        try:
                            # 如果目标目录已存在（但数据库没了），先删除以便完整拷贝
                            if target_dir.exists():
                                shutil.rmtree(target_dir, ignore_errors=True)
                            os.makedirs(target_dir.parent, exist_ok=True)
                            shutil.copytree(bundle_data, target_dir)
                            print(f"Initialized data from bundle to {target_dir}")
                        except Exception as e:
                            print(f"Failed to initialize data from bundle: {e}")
                return target_dir
        return Path.home() / f".{app_name}" / "data"
    # 开发环境下使用当前项目目录
    return Path(__file__).resolve().parent / "data"

BASE_DIR = get_app_path()
DATA_DIR = get_data_dir()
DB_DIR = DATA_DIR / "db"
UPLOAD_DIR = DATA_DIR / "uploads"
RESOURCE_DIR = DATA_DIR / "resource"
SETTINGS_PATH = DATA_DIR / "settings.json"
DB_PATH = DB_DIR / "qbank.db"

# 目录确保存在逻辑已移至 db.database.init_app_environment 中
# 以免在 Web 环境构建时因权限问题导致失败

DEFAULT_API_KEY = os.getenv("API_KEY", "sk-3fe69a05f74343378c113884838f468d")
DEFAULT_API_BASE_URL = os.getenv("API_BASE_URL", "https://api.deepseek.com")
DEFAULT_API_MODEL = os.getenv("API_MODEL", "deepseek-reasoner")

def get_api_key() -> str:
    return DEFAULT_API_KEY

def get_api_base_url() -> str:
    return DEFAULT_API_BASE_URL

def get_api_model() -> str:
    return DEFAULT_API_MODEL

# 为了兼容旧代码，保留变量引用，但建议使用 getter
API_KEY = get_api_key()
API_BASE_URL = get_api_base_url()
API_MODEL = get_api_model()

def refresh_config():
    """环境变量模式下，无需主动刷新"""
    pass

STARTUP_CHECK_MODE = os.getenv("FEATURE_STARTUP_CHECKS", "warn").strip().lower()

DEFAULT_DIFFICULTY_RATIO = {1: 0.1, 2: 0.2, 3: 0.4, 4: 0.2, 5: 0.1}
DEFAULT_PAPER_SIZE = 10
DEFAULT_RECENT_HOURS = int(os.getenv("DEFAULT_RECENT_HOURS", "0"))
MAX_CHUNK_TOKENS = int(os.getenv("MAX_CHUNK_TOKENS", "800"))
MAX_CLASSIFY_WORKERS = int(os.getenv("MAX_CLASSIFY_WORKERS", "4"))
MAX_CLASSIFY_RETRIES = int(os.getenv("MAX_CLASSIFY_RETRIES", "2"))
IMPORT_CLASSIFY_WORKERS = int(os.getenv("IMPORT_CLASSIFY_WORKERS", "1"))
IMPORT_LLM_TIMEOUT = int(os.getenv("IMPORT_LLM_TIMEOUT", "120"))
IMPORT_MAX_OUTPUT_TOKENS = int(os.getenv("IMPORT_MAX_OUTPUT_TOKENS", "4096"))
IMPORT_FAILED_RETRY_COOLDOWN_MINUTES = int(os.getenv("IMPORT_FAILED_RETRY_COOLDOWN_MINUTES", "30"))
IMPORT_CLEANUP_MODE = os.getenv("FEATURE_IMPORT_CLEANUP", "record").strip().lower()
FAST_RANDOM_QUERY_MODE = os.getenv("FEATURE_FAST_RANDOM_QUERY", "off").strip().lower()


def _path_writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        test_file = path / ".write_probe"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink(missing_ok=True)
        return True
    except Exception:
        return False


def run_startup_checks() -> dict[str, Any]:
    warnings: list[str] = []
    fatals: list[str] = []
    mode = STARTUP_CHECK_MODE if STARTUP_CHECK_MODE in {"off", "warn", "strict"} else "warn"

    if is_web_deploy():
        return {
            "mode": "normal",
            "warnings": [],
            "fatals": [],
            "ok": True,
        }

    # 动态获取当前 API 配置
    current_key = get_api_key()
    
    if not current_key or current_key == DEFAULT_API_KEY:
        warnings.append("未配置个人 API 密钥或正在使用默认密钥，建议前往“系统设置”配置网关。")

    if not _path_writable(DB_DIR):
        fatals.append(f"数据库目录不可写: {DB_DIR}")
    if not _path_writable(UPLOAD_DIR):
        fatals.append(f"上传目录不可写: {UPLOAD_DIR}")

    return {
        "mode": mode,
        "warnings": warnings,
        "fatals": fatals,
        "ok": not fatals,
    }
