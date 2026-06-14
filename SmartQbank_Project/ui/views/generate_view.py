from datetime import datetime
import threading
from tkinter import filedialog

import flet as ft
from ui.state import StateManager
from db.database import get_connection
from db.crud import fetch_categories
from core.retriever import retrieve_questions
from core.categories import build_major_map
from utils.exporter import export_paper_to_docx, export_paper_to_pdf
import config

class GenerateView:
    def __init__(self, page: ft.Page, state: StateManager):
        self.page = page
        self.state = state

    def build(self) -> ft.Control:
        # Load categories
        with get_connection() as conn:
            categories = fetch_categories(conn)
            
        # UI Components
        major_category_map = build_major_map(categories)
        major_categories = list(major_category_map.keys()) if major_category_map else ["无学科"]
        selected_majors: set[str] = set([major_categories[0]]) if major_categories and major_categories[0] != "无学科" else set()

        selected_text = ft.Text(
            f"已选学科大类：{', '.join(selected_majors) if selected_majors else '未选择'}",
            color=ft.Colors.BLUE_GREY,
        )

        def update_selected_text() -> None:
            selected_text.value = f"已选学科大类：{', '.join(sorted(selected_majors)) if selected_majors else '未选择'}"

        def on_major_change(e):
            major = e.control.data
            if e.control.value:
                selected_majors.add(major)
            else:
                selected_majors.discard(major)
            update_selected_text()
            self.page.update()

        major_checks = [
            ft.Checkbox(label=major, value=major in selected_majors, data=major, on_change=on_major_change)
            for major in major_categories
            if major != "无学科"
        ]

        category_selector = ft.Container(
            content=ft.Column(
                [
                    ft.Text("学科大类（可多选）", weight="bold"),
                    ft.Container(
                        content=ft.ListView(controls=major_checks, spacing=4, height=220),
                        border=ft.Border.all(1, ft.Colors.GREY_300),
                        border_radius=8,
                        padding=8,
                    ),
                    selected_text,
                ],
                spacing=8,
            ),
            width=360,
        )
            
        count_slider = ft.Slider(min=1, max=100, divisions=99, value=10, label="题量: {value}")
        question_type_dropdown = ft.Dropdown(
            label="题型",
            width=180,
            value="all",
            options=[
                ft.dropdown.Option("all", "全部"),
                ft.dropdown.Option("single", "单选题"),
                ft.dropdown.Option("true_false", "判断题"),
                ft.dropdown.Option("fill_blank", "填空题"),
            ],
        )
        recent_slider = ft.Slider(
            min=0,
            max=72,
            divisions=72,
            value=float(max(0, int(config.DEFAULT_RECENT_HOURS))),
            label="排除最近使用: {value} 小时",
            width=320,
        )

        status_text = ft.Text("")
        export_actions = ft.Row([], visible=bool(self.state.generated_paper))

        if self.state.generated_paper:
            status_text.value = f"当前已有 {len(self.state.generated_paper)} 道试题，可继续导出，或前往“模拟考试”选择模拟考试/刷题练习。"
            status_text.color = ft.Colors.BLUE

        def save_paper(data: bytes, suffix: str):
            file_name = f"智能组卷试卷_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{suffix}"
            
            def ask_and_save():
                path = filedialog.asksaveasfilename(
                    title=f"导出{suffix.upper()}文件",
                    defaultextension=f".{suffix}",
                    initialfile=file_name,
                    filetypes=[(f"{suffix.upper()} 文件", f"*.{suffix}")],
                )
                if not path:
                    return
                with open(path, "wb") as f:
                    f.write(data)
                status_text.value = f"✅ 已导出到 {path}"
                status_text.color = ft.Colors.GREEN
                self.page.update()
            
            threading.Thread(target=ask_and_save, daemon=True).start()

        def export_docx(_):
            if not self.state.generated_paper:
                status_text.value = "⚠️ 当前没有可导出的试卷。"
                status_text.color = ft.Colors.RED
                self.page.update()
                return
            save_paper(export_paper_to_docx(self.state.generated_paper), "docx")

        def export_pdf(_):
            if not self.state.generated_paper:
                status_text.value = "⚠️ 当前没有可导出的试卷。"
                status_text.color = ft.Colors.RED
                self.page.update()
                return
            save_paper(export_paper_to_pdf(self.state.generated_paper), "pdf")

        export_actions.controls = [
            ft.OutlinedButton("导出 DOCX", icon=ft.Icons.DESCRIPTION, on_click=export_docx),
            ft.OutlinedButton("导出 PDF", icon=ft.Icons.PICTURE_AS_PDF, on_click=export_pdf),
        ]

        def on_generate(e):
            total_count = int(count_slider.value)
            if not selected_majors and major_categories and major_categories[0] != "无学科":
                status_text.value = "⚠️ 请至少选择一个学科大类。"
                status_text.color = ft.Colors.RED
                self.page.update()
                return

            selected_categories: list[str] = []
            for major in sorted(selected_majors):
                selected_categories.extend(major_category_map.get(major, []))
            selected_categories = list(dict.fromkeys(selected_categories))

            recent_hours = int(recent_slider.value)
            try:
                with get_connection() as conn:
                    questions = retrieve_questions(
                        conn=conn,
                        total_count=total_count,
                        categories=selected_categories,
                        recent_hours=recent_hours,
                        question_type=question_type_dropdown.value or "all",
                    )
                    relaxed = False
                    if not questions and recent_hours > 0:
                        questions = retrieve_questions(
                            conn=conn,
                            total_count=total_count,
                            categories=selected_categories,
                            recent_hours=0,
                            question_type=question_type_dropdown.value or "all",
                        )
                        relaxed = bool(questions)

                if not questions:
                    status_text.value = "⚠️ 未找到符合条件的题目。可将“排除最近使用”调小后重试。"
                    status_text.color = ft.Colors.RED
                else:
                    self.state.generated_paper = questions
                    self.state.exam_state.submitted = False
                    export_actions.visible = True
                    if relaxed:
                        status_text.value = (
                            f"✅ 成功生成 {len(questions)} 道题目！已自动放宽“排除最近使用”到0小时。"
                        )
                    else:
                        status_text.value = f"✅ 成功生成 {len(questions)} 道题目！请前往“模拟考试”选择模拟考试或刷题练习，也可直接导出。"
                    status_text.color = ft.Colors.GREEN
            except Exception as ex:
                status_text.value = f"❌ 生成失败: {str(ex)}"
                status_text.color = ft.Colors.RED
            self.page.update()

        return ft.Container(
            content=ft.Column([
                ft.Text("组卷生成", size=24, weight="bold"),
                ft.Divider(),
                ft.Row(
                    [
                        category_selector,
                        ft.Column([
                            ft.Row([ft.Text("总题量:"), count_slider, question_type_dropdown]),
                            ft.Row([ft.Text("最近使用过滤:"), recent_slider]),
                        ], spacing=12),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                ft.Divider(),
                ft.ElevatedButton("立即生成试卷", icon=ft.Icons.LIBRARY_BOOKS, on_click=on_generate),
                export_actions,
                status_text
            ], expand=True, scroll=ft.ScrollMode.AUTO),
            expand=True,
            padding=20
        )
