# Netlify 部署指南

本指南旨在指导如何将“自动气象站智慧学习平台”部署到 Netlify 云平台。由于 Web 环境与桌面环境的差异，需要进行一些必要的配置和代码调整。

## 1. netlify.toml 配置文件内容

在项目根目录下创建 `netlify.toml` 文件，内容如下：

```toml
[build]
  # 构建命令：安装依赖并使用 flet publish 发布
  command = "pip install -r tiku/SmartQbank_Project/requirements.txt && flet publish tiku/SmartQbank_Project/main_desktop.py --output dist"
  # 发布目录：flet publish 默认生成或指定的输出目录
  publish = "dist"

[build.environment]
  PYTHON_VERSION = "3.10"
```

---

## 2. main_desktop.py 的改动说明

为了适配 Web 环境，建议对 `tiku/SmartQbank_Project/main_desktop.py` 进行以下修改：

### 修改建议：
- **移除固定窗口尺寸**：Web 端由浏览器控制窗口大小，设置 `window_width` 等属性在 Web 端无效或可能导致异常。
- **环境检查适配**：Web 环境下可能无法执行某些本地系统检查。

### 代码片段示例：

```python
def main(page: ft.Page):
    # init_app_environment() # 需确保数据库已适配云端
    
    # 注释掉或条件化桌面端特有设置
    page.title = "自动气象站智慧学习平台"
    # page.window_width = 1280  # Web 端建议移除
    # page.window_height = 850  # Web 端建议移除
    page.theme_mode = ft.ThemeMode.LIGHT
    # ... 其余代码保持不变 ...
```

---

## 3. 数据库迁移至云端 (Supabase) 方案

Web 端无法直接读写本地 SQLite 文件，建议迁移至 **Supabase** (PostgreSQL)。

### 迁移步骤：
1. 在 [Supabase](https://supabase.com/) 创建新项目。
2. 在 SQL Editor 中运行现有的 DDL 语句（参考 `db/database.py` 中的 `CREATE TABLE` 逻辑）初始化表结构。
3. 获取 `SUPABASE_URL` 和 `SUPABASE_KEY`。

### db/database.py 修改建议：
建议引入环境变量来切换数据库连接逻辑。

```python
import os
# 如果使用 Supabase，需要安装 supabase 库
# from supabase import create_client, Client

def get_connection():
    if os.getenv("WEB_DEPLOY") == "true":
        # 此处实现连接到 Supabase 或远程 PostgreSQL 的逻辑
        # 示例：使用 psycopg2 连接 Supabase 的连接字符串
        pass
    else:
        # 保持原有的 SQLite 连接逻辑
        import sqlite3
        conn = sqlite3.connect(DB_PATH, timeout=10)
        # ...
        return conn
```

> **注意**：需要在 `requirements.txt` 中添加相应的数据库驱动库（如 `supabase` 或 `psycopg2-binary`）。

---

## 4. Netlify 后台配置步骤

1. **关联仓库**：在 Netlify 后台点击 "Add new site" -> "Import an existing project"，关联你的 GitHub/GitLab 仓库。
2. **设置构建参数**（如果 `netlify.toml` 已存在，Netlify 会自动识别）：
   - **Build command**: `pip install -r tiku/SmartQbank_Project/requirements.txt && flet publish tiku/SmartQbank_Project/main_desktop.py --output dist`
   - **Publish directory**: `dist`
3. **配置环境变量**：
   - 进入 `Site configuration` -> `Environment variables`。
   - 添加 `PYTHON_VERSION`: `3.10`
   - 添加 `WEB_DEPLOY`: `true`
   - 添加数据库相关变量（如 `SUPABASE_URL`, `SUPABASE_KEY` 等）。
4. **部署**：点击 "Deploy site" 等待构建完成。
