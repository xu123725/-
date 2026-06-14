from __future__ import annotations
import flet as ft

from db.crud import list_wrong_questions, remove_wrong_question
from db.database import get_connection
from ui.state import StateManager


class WrongBookView:
    def __init__(self, page: ft.Page, state: StateManager, open_view):
        self.page = page
        self.state = state
        self.open_view = open_view

    def build(self) -> ft.Control:
        summary_text = ft.Text("")
        status_text = ft.Text("")
        list_column = ft.Column(spacing=12, expand=True, scroll=ft.ScrollMode.AUTO)

        def load_questions() -> list[dict]:
            with get_connection() as conn:
                return [item.model_dump() for item in list_wrong_questions(conn, limit=200, order_by="recent")]

        def load_into_practice(questions: list[dict]) -> None:
            self.state.generated_paper = questions
            self.state.exam_state.is_running = False
            self.state.exam_state.submitted = False
            self.state.exam_state.mode = "practice"
            self.state.exam_state.current_index = 0
            self.state.exam_state.answers = {}
            self.state.exam_state.revealed = {}
            self.state.exam_state.score = 0
            self.state.exam_state.time_left = 0
            self.open_view(2)

        def refresh_list() -> None:
            questions = load_questions()
            summary_text.value = f"当前错题本共 {len(questions)} 道题"
            start_all_button.disabled = not questions
            list_column.controls.clear()

            if not questions:
                list_column.controls.append(
                    ft.Container(
                        content=ft.Text("错题本还是空的。可在刷题练习中把题加入错题本。"),
                        padding=16,
                        border=ft.Border.all(1, ft.Colors.GREY_300),
                        border_radius=10,
                    )
                )
                return

            for item in questions:
                stem = item.get("stem", "")
                preview = stem if len(stem) <= 90 else stem[:90] + "..."
                meta = f"{item.get('category', '未分类')}｜难度 {item.get('difficulty', '-')}｜错题次数 {item.get('wrong_count', 0)}"

                def practice_one(_, q=item):
                    load_into_practice([q])

                def remove_one(_, qid=item["id"]):
                    with get_connection() as conn:
                        remove_wrong_question(conn, qid)
                    status_text.value = "已从错题本移除"
                    status_text.color = ft.Colors.GREEN
                    refresh_list()
                    self.page.update()

                list_column.controls.append(
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(preview, size=16, weight="bold"),
                                ft.Text(meta, color=ft.Colors.BLUE_GREY_600),
                                ft.Row(
                                    [
                                        ft.ElevatedButton("练这题", icon=ft.Icons.PLAY_ARROW, on_click=practice_one),
                                        ft.OutlinedButton("移出错题本", icon=ft.Icons.DELETE_OUTLINE, on_click=remove_one),
                                    ]
                                ),
                            ],
                            spacing=10,
                        ),
                        padding=14,
                        border=ft.Border.all(1, ft.Colors.GREY_300),
                        border_radius=10,
                    )
                )

        def start_all(_):
            questions = load_questions()
            if not questions:
                status_text.value = "当前没有可练习的错题。"
                status_text.color = ft.Colors.RED
                self.page.update()
                return
            load_into_practice(questions)

        start_all_button = ft.ElevatedButton("刷全部错题", icon=ft.Icons.MENU_BOOK, on_click=start_all)

        refresh_list()

        return ft.Container(
            content=ft.Column(
                [
                    ft.Text("错题本", size=24, weight="bold"),
                    ft.Divider(),
                    ft.Row([summary_text, ft.Container(expand=True), start_all_button]),
                    status_text,
                    list_column,
                ],
                expand=True,
                scroll=ft.ScrollMode.AUTO,
            ),
            expand=True,
            padding=20,
        )