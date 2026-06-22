import logging
import os
import shutil
import threading
import time
from tkinter import filedialog
import flet as ft
from ui.state import StateManager
from config import UPLOAD_DIR
from core.classifier import classify_questions, build_chunk_tasks
from core.extractor import extract_content
from core.llm_client import LLMClient
from core.processor import upsert_questions
from core.knowledge_processor import ingest_knowledge
from db.database import get_connection
from db.crud import (
    fetch_question_count_by_source,
    get_cached_import,
    has_recent_failed_import,
    upsert_imported_file,
)
from utils.logger import create_trace_id, log_event
from ui.theme import AppColors, AppStyles
import config

logger = logging.getLogger(__name__)

def _open_file_dialog() -> list[str]:
    """使用系统原生文件对话框选择文件，返回文件路径列表"""
    paths = filedialog.askopenfilenames(
        title="选择要导入的文档",
        filetypes=[("文档文件", "*.docx *.pdf"), ("所有文件", "*.*")],
    )
    return list(paths)


class ImportView:
    def __init__(self, page: ft.Page, state: StateManager):
        self.page = page
        self.state = state

    def build(self) -> ft.Control:
        progress_ring = ft.ProgressRing(visible=False, color=AppColors.PRIMARY, width=20, height=20)
        status_text = AppStyles.desc_text("")
        
        target_dropdown = ft.Dropdown(
            label="导入目标",
            options=[
                ft.dropdown.Option("qbank", "题目入库 (用于组卷和考试)"),
                ft.dropdown.Option("aws_maintenance", "自动气象站维护与维修 (题库分类)"),
                ft.dropdown.Option("knowledge", "知识库入库 (用于智能助手 RAG)"),
            ],
            value="qbank",
            width=400,
            border_radius=12,
            bgcolor=AppColors.SURFACE,
        )
        
        def process_files(file_paths: list[str], target="qbank"):
            total_success = 0
            total_duplicate = 0
            total_cached = 0
            failed_files: list[str] = []

            if target == "knowledge":
                for src_path in file_paths:
                    fname = os.path.basename(src_path)
                    try:
                        status_text.value = f"正在将 {fname} 导入知识库..."
                        self.page.update()
                        dest_path = os.path.join(UPLOAD_DIR, fname)
                        shutil.copy2(src_path, dest_path)
                        res = ingest_knowledge(dest_path, category="竞赛要求")
                        if res.get("success"):
                            total_success += res.get("count", 0)
                        else:
                            failed_files.append(f"{fname}: {res.get('error', '未知错误')}")
                    except Exception as ex:
                        failed_files.append(f"{fname}: {str(ex)}")
                
                progress_ring.visible = False
                if failed_files:
                    status_text.value = f"⚠️ 知识库导入完成! 新增 {total_success} 条片段，失败 {len(failed_files)} 个。"
                    status_text.color = AppColors.ERROR
                else:
                    status_text.value = f"✅ 知识库导入完成! 新增 {total_success} 条知识片段。"
                    status_text.color = AppColors.SUCCESS
                self.page.update()
                return

            fixed_category = "自动气象站维护与维修" if target == "aws_maintenance" else None

            client = LLMClient(
                api_key=config.get_api_key(),
                base_url=config.get_api_base_url(),
                model=config.get_api_model(),
                timeout=config.IMPORT_LLM_TIMEOUT,
            )
            
            for src_path in file_paths:
                fname = os.path.basename(src_path)
                trace_id = create_trace_id()
                dest_path = os.path.join(UPLOAD_DIR, fname)
                shutil.copy2(src_path, dest_path)
                file_signature = "unknown"
                try:
                    client.set_trace_id(trace_id)
                    file_stat = os.stat(dest_path)
                    file_signature = f"{file_stat.st_size}:{file_stat.st_mtime_ns}"
                    
                    with get_connection() as conn:
                        cached = get_cached_import(conn, fname, file_signature)
                        failed_recently = has_recent_failed_import(conn, fname, file_signature)
                        upsert_imported_file(conn, fname, file_signature, 0, status="processing")
                        conn.commit()
                    
                    if cached:
                        total_cached += 1
                        status_text.value = f"{fname} 已入库，跳过重复解析"
                        self.page.update()
                        continue

                    status_text.value = f"正在解析 {fname} 的内容..."
                    self.page.update()
                    
                    content_text = extract_content(dest_path)
                    if not content_text:
                        failed_files.append(f"{fname}: 文档内容为空")
                        continue
                    
                    def on_progress(done: int, total: int):
                        status_text.value = f"正在处理 {fname}（{done}/{total} 块）..."
                        self.page.update()

                    questions, _ = classify_questions(
                        content_text,
                        client,
                        max_tokens=config.MAX_CHUNK_TOKENS,
                        max_workers=max(1, config.IMPORT_CLASSIFY_WORKERS),
                        progress_hook=on_progress,
                        fixed_category=fixed_category,
                    )
                    
                    if not questions:
                        failed_files.append(f"{fname}: 未识别到有效题目")
                        continue

                    with get_connection() as conn:
                        stats = upsert_questions(conn, questions, source=fname)
                        source_count = fetch_question_count_by_source(conn, fname)
                        upsert_imported_file(conn, fname, file_signature, source_count, status="done")
                        conn.commit()
                        
                    total_success += stats["success"]
                    total_duplicate += stats["duplicate"]
                    status_text.value = f"{fname} 解析完成"
                    self.page.update()
                except Exception as ex:
                    with get_connection() as conn:
                        upsert_imported_file(conn, fname, file_signature, 0, status="failed", last_error=str(ex))
                        conn.commit()
                    failed_files.append(f"{fname}: {str(ex)}")
                    status_text.value = f"{fname} 处理失败"
                    self.page.update()
                        
            progress_ring.visible = False
            status_text.value = f"✅ 完成! 新增 {total_success} 题，重复 {total_duplicate} 题。"
            status_text.color = AppColors.SUCCESS
            self.page.update()

        def pick_files(_):
            # 在后台线程中打开文件对话框，避免阻塞 Flet
            def choose_and_process():
                paths = _open_file_dialog()
                if not paths:
                    return
                progress_ring.visible = True
                status_text.value = f"正在处理 {len(paths)} 个文件..."
                status_text.color = AppColors.TEXT_SECONDARY
                self.page.update()
                process_files(paths, target_dropdown.value)
            
            threading.Thread(target=choose_and_process, daemon=True).start()

        return ft.Column([
            AppStyles.page_header("文档入库", "支持智能解析 Docx/PDF 文档，自动提取题目与知识点", ft.Icons.UPLOAD_FILE_ROUNDED),
            AppStyles.glass_container(
                content=ft.Column([
                    ft.Text("1. 选择导入目标", size=16, weight="bold", color=AppColors.TEXT_PRIMARY),
                    target_dropdown,
                    ft.Divider(height=40, color=ft.Colors.TRANSPARENT),
                    ft.Text("2. 选择要导入的文档", size=16, weight="bold", color=AppColors.TEXT_PRIMARY),
                    AppStyles.desc_text("支持批量上传，AI 将自动进行结构化处理"),
                    ft.Container(height=10),
                    AppStyles.primary_button(
                        "选取文件并开始导入", 
                        icon=ft.Icons.CLOUD_UPLOAD_ROUNDED, 
                        on_click=pick_files
                    ),
                    ft.Container(height=30),
                    ft.Row([progress_ring, status_text], spacing=12),
                ], spacing=10),
                padding=40,
            )
        ], expand=True)
