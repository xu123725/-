import asyncio
import threading
import flet as ft

import config
from core.llm_client import LLMClient
from core.processor import get_or_generate_analysis, generate_learning_report_stream
from db.crud import add_wrong_question, insert_user_log, is_in_wrong_book, remove_wrong_question
from db.database import get_connection
from ui.state import StateManager

def _normalize_answer(value: str) -> str:
    return (value or "").strip().lower()


def _is_answer_correct(user_answer: str, std_answer: str) -> bool:
    return _normalize_answer(user_answer) == _normalize_answer(std_answer)


class ExamView:
    def __init__(self, page: ft.Page, state: StateManager):
        self.page = page
        self.state = state

    def build(self) -> ft.Control:
        content = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=20)

        def reset_state():
            self.state.exam_state.is_running = False
            self.state.exam_state.submitted = False
            self.state.exam_state.mode = ""
            self.state.exam_state.current_index = 0
            self.state.exam_state.answers = {}
            self.state.exam_state.revealed = {}
            self.state.exam_state.score = 0
            self.state.exam_state.time_left = 0
            self.state.exam_state.exam_report = ""

        def render_not_started():
            paper = self.state.generated_paper
            if not paper:
                return ft.Text("当前没有已生成的试卷。请先在“组卷生成”或通过智能助手生成试卷。")

            def start_exam(_):
                reset_state()
                self.state.exam_state.mode = "exam"
                self.state.exam_state.is_running = True
                self.state.exam_state.time_left = len(paper) * 60
                self.page.run_task(timer_task)
                refresh_view()

            def start_practice(_):
                reset_state()
                self.state.exam_state.mode = "practice"
                refresh_view()

            return ft.Column([
                ft.Text(f"当前试卷包含 {len(paper)} 道题目。", size=18),
                ft.Text("可选择模拟考试或刷题练习。刷题练习支持即时查看答案与解析。"),
                ft.Row([
                    ft.ElevatedButton("模拟考试", icon=ft.Icons.PLAY_ARROW, on_click=start_exam),
                    ft.OutlinedButton("刷题练习", icon=ft.Icons.MENU_BOOK, on_click=start_practice),
                ]),
            ])

        async def timer_task():
            while self.state.exam_state.is_running and self.state.exam_state.time_left > 0:
                await asyncio.sleep(1)
                self.state.exam_state.time_left -= 1
                if hasattr(self, "timer_text"):
                    mins, secs = divmod(self.state.exam_state.time_left, 60)
                    self.timer_text.value = f"剩余时间: {mins:02d}:{secs:02d}"
                    self.page.update()
            if self.state.exam_state.is_running and self.state.exam_state.time_left <= 0:
                submit_exam(None)

        def submit_exam(_):
            self.state.exam_state.is_running = False
            self.state.exam_state.submitted = True
            paper = self.state.generated_paper or []
            self.state.exam_state.score = sum(
                1
                for idx, q in enumerate(paper)
                if _is_answer_correct(self.state.exam_state.answers.get(idx, ""), q.get("answer", ""))
            )
            refresh_view()
            
            # 异步流式生成学习报告
            def generate_report():
                client = LLMClient(
                    api_key=config.get_api_key(),
                    base_url=config.get_api_base_url(),
                    model=config.get_api_model(),
                )
                self.state.exam_state.exam_report = ""
                for chunk in generate_learning_report_stream(client, paper, self.state.exam_state.answers):
                    self.state.exam_state.exam_report += chunk
                    self.page.update()
            
            threading.Thread(target=generate_report, daemon=True).start()

        def render_exam():
            paper = self.state.generated_paper or []
            idx = self.state.exam_state.current_index
            q = paper[idx]
            self.timer_text = ft.Text("", size=20, weight="bold", color=ft.Colors.RED)

            def on_answer_change(e):
                self.state.exam_state.answers[idx] = e.control.value

            def prev_q(_):
                if idx > 0:
                    self.state.exam_state.current_index -= 1
                    refresh_view()

            def next_q(_):
                if idx < len(paper) - 1:
                    self.state.exam_state.current_index += 1
                    refresh_view()

            is_fill_blank = (q.get("question_type", "single") == "fill_blank")
            is_true_false = (q.get("question_type", "single") == "true_false")
            
            answer_control: ft.Control
            if is_fill_blank:
                answer_control = ft.TextField(
                    label="请输入答案",
                    value=self.state.exam_state.answers.get(idx, ""),
                    on_change=on_answer_change,
                )
            elif is_true_false:
                # 对于判断题，如果选项为空，则默认提供“正确”和“错误”
                opts = q.get("options", [])
                if not opts:
                    opts = ["正确", "错误"]
                answer_control = ft.RadioGroup(
                    content=ft.Row([ft.Radio(value=opt, label=opt) for opt in opts]),
                    value=self.state.exam_state.answers.get(idx),
                    on_change=on_answer_change,
                )
            else:
                answer_control = ft.RadioGroup(
                    content=ft.Column([ft.Radio(value=opt, label=opt) for opt in q.get("options", [])]),
                    value=self.state.exam_state.answers.get(idx),
                    on_change=on_answer_change,
                )

            return ft.Column([
                ft.Row([ft.Text(f"题目 {idx + 1}", size=20, weight="bold"), self.timer_text], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(),
                ft.Text(q.get("stem", ""), size=16),
                answer_control,
                ft.Divider(),
                ft.Row([
                    ft.ElevatedButton("上一题", on_click=prev_q, disabled=idx == 0),
                    ft.Text(f"{idx + 1} / {len(paper)}"),
                    ft.ElevatedButton("下一题", on_click=next_q, disabled=idx == len(paper) - 1),
                    ft.Container(expand=True),
                    ft.ElevatedButton("交卷", on_click=submit_exam, bgcolor=ft.Colors.RED, color=ft.Colors.WHITE),
                ]),
            ], expand=True)

        def render_practice():
            paper = self.state.generated_paper or []
            idx = self.state.exam_state.current_index
            q = paper[idx]
            with get_connection() as conn:
                q["in_wrong_book"] = is_in_wrong_book(conn, q["id"])
            revealed = self.state.exam_state.revealed.get(idx, False)
            answered = sum(1 for ok in self.state.exam_state.revealed.values() if ok)
            correct = sum(1 for i, ok in self.state.exam_state.revealed.items() if ok and self.state.exam_state.answers.get(i, "") == paper[i].get("answer", ""))
            wrong_book_active = bool(q.get("in_wrong_book"))

            def on_answer_change(e):
                if not revealed:
                    self.state.exam_state.answers[idx] = e.control.value

            def prev_q(_):
                if idx > 0:
                    self.state.exam_state.current_index -= 1
                    refresh_view()

            def next_q(_):
                if idx < len(paper) - 1:
                    self.state.exam_state.current_index += 1
                    refresh_view()

            def reveal_answer(_):
                answer = self.state.exam_state.answers.get(idx, "")
                if not answer:
                    return
                is_correct = _is_answer_correct(answer, q.get("answer", ""))
                with get_connection() as conn:
                    insert_user_log(conn, q["id"], is_correct)
                    client = LLMClient(
                        api_key=config.get_api_key(), 
                        base_url=config.get_api_base_url(), 
                        model=config.get_api_model(), 
                        timeout=config.IMPORT_LLM_TIMEOUT
                    )
                    q["analysis"] = get_or_generate_analysis(conn, client, q["id"])
                paper[idx] = q
                self.state.generated_paper = paper
                self.state.exam_state.revealed[idx] = True
                refresh_view()

            def toggle_wrong_book(_):
                with get_connection() as conn:
                    if is_in_wrong_book(conn, q["id"]):
                        remove_wrong_question(conn, q["id"])
                        q["in_wrong_book"] = False
                    else:
                        add_wrong_question(conn, q["id"])
                        q["in_wrong_book"] = True
                paper[idx] = q
                self.state.generated_paper = paper
                refresh_view()

            def finish_practice(_):
                reset_state()
                refresh_view()

            is_fill_blank = (q.get("question_type", "single") == "fill_blank")
            is_true_false = (q.get("question_type", "single") == "true_false")
            
            answer_control: ft.Control
            if is_fill_blank:
                answer_control = ft.TextField(
                    label="请输入答案",
                    value=self.state.exam_state.answers.get(idx, ""),
                    on_change=on_answer_change,
                    disabled=revealed,
                )
            elif is_true_false:
                opts = q.get("options", [])
                if not opts:
                    opts = ["正确", "错误"]
                answer_control = ft.RadioGroup(
                    content=ft.Row([ft.Radio(value=opt, label=opt, disabled=revealed) for opt in opts]),
                    value=self.state.exam_state.answers.get(idx),
                    on_change=on_answer_change,
                )
            else:
                answer_control = ft.RadioGroup(
                    content=ft.Column([ft.Radio(value=opt, label=opt, disabled=revealed) for opt in q.get("options", [])]),
                    value=self.state.exam_state.answers.get(idx),
                    on_change=on_answer_change,
                )

            return ft.Column([
                ft.Row([
                    ft.Text("刷题练习", size=22, weight="bold"),
                    ft.Container(expand=True),
                    ft.Text(f"已作答 {answered}/{len(paper)}  正确 {correct}"),
                ]),
                ft.Text(q.get("stem", ""), size=16),
                answer_control,
                ft.Row([
                    ft.ElevatedButton("提交并看解析", on_click=reveal_answer, disabled=revealed),
                    ft.OutlinedButton("移出错题本" if wrong_book_active else "加入错题本", on_click=toggle_wrong_book),
                    ft.OutlinedButton("结束练习", on_click=finish_practice),
                ]),
                ft.Container(
                    content=ft.Column([
                        ft.Text("已在错题本中" if wrong_book_active else "当前未加入错题本", color=ft.Colors.ORANGE if wrong_book_active else ft.Colors.BLUE_GREY),
                        ft.Text("回答正确" if _is_answer_correct(self.state.exam_state.answers.get(idx, ""), q.get("answer", "")) else "回答错误", color=ft.Colors.GREEN if _is_answer_correct(self.state.exam_state.answers.get(idx, ""), q.get("answer", "")) else ft.Colors.RED),
                        ft.Text(f"正确答案：{q.get('answer', '')}"),
                        ft.Text(q.get("analysis", "暂无解析")),
                    ]),
                    visible=revealed,
                    padding=12,
                    border=ft.Border.all(1, ft.Colors.GREY_300),
                    border_radius=8,
                ),
                ft.Row([
                    ft.ElevatedButton("上一题", on_click=prev_q, disabled=idx == 0),
                    ft.Text(f"{idx + 1} / {len(paper)}"),
                    ft.ElevatedButton("下一题", on_click=next_q, disabled=idx == len(paper) - 1),
                ]),
            ], expand=True)

        def render_result():
            paper = self.state.generated_paper or []
            def restart(_):
                reset_state()
                refresh_view()
            
            report_content = self.state.exam_state.exam_report
            
            # 使用 Markdown 显示流式文本
            report_markdown = ft.Markdown(
                report_content, 
                selectable=True,
                extension_set=ft.MarkdownExtensionSet.GITHUB_WEB_FLAVOR
            )
            
            if not report_content:
                report_display = ft.Row([
                    ft.ProgressRing(width=16, height=16, stroke_width=2),
                    ft.Text(" 高级工程师正在为您分析答题情况...", italic=True, color=ft.Colors.BLUE_GREY)
                ])
            else:
                report_display = ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.ANALYTICS, color=ft.Colors.BLUE_600),
                            ft.Text("AI 智能学习诊断报告", size=18, weight="bold", color=ft.Colors.BLUE_600),
                        ]),
                        report_markdown,
                    ], spacing=10),
                    padding=20,
                    bgcolor=ft.Colors.BLUE_50,
                    border_radius=12,
                    border=ft.Border.all(1, ft.Colors.BLUE_100),
                )

            return ft.Column([
                ft.Container(
                    content=ft.Column([
                        ft.Text("考试结束", size=28, weight="bold", color=ft.Colors.BLUE_GREY_900),
                        ft.Text(f"得分: {self.state.exam_state.score} / {len(paper)}", size=22, weight="w500", color=ft.Colors.BLUE_600),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    alignment=ft.Alignment(0, 0),
                    padding=20,
                ),
                ft.Divider(height=1, color=ft.Colors.GREY_300),
                report_display,
                ft.Container(height=20),
                ft.Row([
                    ft.ElevatedButton("返回首页", icon=ft.Icons.HOME, on_click=restart),
                    ft.OutlinedButton("查看错题 (暂不可用)", icon=ft.Icons.LIST_ALT, disabled=True),
                ], alignment=ft.MainAxisAlignment.CENTER),
            ], spacing=10, scroll=ft.ScrollMode.AUTO)

        def refresh_view():
            content.controls.clear()
            if self.state.exam_state.mode == "exam" and self.state.exam_state.is_running:
                content.controls.append(render_exam())
            elif self.state.exam_state.mode == "exam" and self.state.exam_state.submitted:
                content.controls.append(render_result())
            elif self.state.exam_state.mode == "practice":
                content.controls.append(render_practice())
            else:
                content.controls.append(render_not_started())
            self.page.update()

        refresh_view()
        return ft.Container(content, expand=True, padding=20)
