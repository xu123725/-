import asyncio
import threading
import flet as ft

import config
from core.llm_client import LLMClient
from core.processor import get_or_generate_analysis, generate_learning_report_stream
from db.crud import add_wrong_question, insert_user_log, is_in_wrong_book, remove_wrong_question
from db.database import get_connection
from ui.state import StateManager
from ui.theme import AppColors

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
            # 计算成绩并记录错题
            self.state.exam_state.score = 0
            with get_connection() as conn:
                for idx, q in enumerate(paper):
                    is_correct = _is_answer_correct(self.state.exam_state.answers.get(idx, ""), q.get("answer", ""))
                    insert_user_log(conn, q["id"], is_correct)
                    if is_correct:
                        self.state.exam_state.score += 1
                    else:
                        add_wrong_question(conn, q["id"])
                conn.commit()
            refresh_view()
            
            # 异步生成 AI 学习报告（不阻塞界面）
            def generate_report():
                try:
                    client = LLMClient(
                        api_key=config.get_api_key(),
                        base_url=config.get_api_base_url(),
                        model=config.get_api_model(),
                        timeout=30,
                    )
                    self.state.exam_state.exam_report = ""
                    for chunk in generate_learning_report_stream(client, paper, self.state.exam_state.answers):
                        self.state.exam_state.exam_report += chunk
                        self.page.update()
                except Exception:
                    self.state.exam_state.exam_report = "（AI 报告生成超时，请查看下方的本地统计结果）"
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
            score = self.state.exam_state.score
            total = len(paper)

            def restart(_):
                reset_state()
                refresh_view()

            # 错题列表
            wrong_list = ft.Column(spacing=8)
            for idx, q in enumerate(paper):
                user_ans = self.state.exam_state.answers.get(idx, "")
                correct_ans = q.get("answer", "")
                is_correct = _is_answer_correct(user_ans, correct_ans)
                if not is_correct and user_ans:  # 只展示做错且作答了的
                    wrong_list.controls.append(
                        ft.Container(
                            content=ft.Column([
                                ft.Text(f"第{idx+1}题: {q.get('stem', '')[:50]}...", weight=ft.FontWeight.W_500, size=13),
                                ft.Row([
                                    ft.Text(f"你的答案: {user_ans}", color=ft.Colors.RED, size=12),
                                    ft.Text("  →  ", color=ft.Colors.GREY, size=12),
                                    ft.Text(f"正确答案: {correct_ans}", color=ft.Colors.GREEN, size=12),
                                ]),
                            ], spacing=4),
                            padding=10,
                            bgcolor=ft.Colors.RED_50,
                            border_radius=8,
                            border=ft.Border.all(1, ft.Colors.RED_100),
                        )
                    )
            wrong_count = len(wrong_list.controls)

            # 正确率环形文字
            accuracy = score / total * 100 if total > 0 else 0
            accuracy_color = ft.Colors.GREEN if accuracy >= 80 else (ft.Colors.AMBER if accuracy >= 60 else ft.Colors.RED)

            # ===== 本地统计报告（即时显示，不依赖 AI）=====
            local_report = ft.Column(spacing=10)

            # 评语
            if accuracy >= 90:
                comment = "优秀！知识掌握非常扎实，继续保持！"
                comment_color = ft.Colors.GREEN
            elif accuracy >= 80:
                comment = "良好！大部分知识点已掌握，注意薄弱环节。"
                comment_color = ft.Colors.BLUE
            elif accuracy >= 60:
                comment = "一般。建议重点复习错题涉及的知识点。"
                comment_color = ft.Colors.AMBER
            else:
                comment = "需要加强。建议系统性地回顾相关课程内容。"
                comment_color = ft.Colors.RED

            local_report.controls.extend([
                ft.Row([
                    ft.Icon(ft.Icons.ANALYTICS, color=ft.Colors.BLUE_600),
                    ft.Text("考试成绩统计", size=16, weight="bold"),
                ]),
                ft.Row([
                    ft.Text(f"正确率 {accuracy:.0f}%", size=14, color=accuracy_color, weight=ft.FontWeight.BOLD),
                    ft.Text(f"  ·  答对 {score} 题  ·  答错 {wrong_count} 题", size=14, color=AppColors.TEXT_SECONDARY),
                ]),
                ft.Text(comment, size=14, color=comment_color),
            ])

            if wrong_count > 0:
                local_report.controls.append(
                    ft.Container(
                        content=ft.Text(f"{wrong_count} 道错题已自动加入错题本，可前往「错题本」针对性练习", size=13, color=ft.Colors.BLUE_600),
                        padding=ft.Padding.only(top=4),
                    )
                )

            # ===== AI 报告区域 =====
            report_content = self.state.exam_state.exam_report
            if report_content and report_content.startswith("（AI 报告生成超时"):
                ai_section = ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.INFO_OUTLINE, color=ft.Colors.AMBER, size=18),
                            ft.Text("AI 详细报告生成超时", size=14, color=ft.Colors.AMBER),
                        ]),
                        ft.Text("已为你生成本地统计分析（上方），可据此制定复习计划。", size=13, color=AppColors.TEXT_SECONDARY),
                    ], spacing=6),
                    padding=14,
                    bgcolor=ft.Colors.AMBER_50,
                    border_radius=10,
                )
            elif report_content:
                ai_section = ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.AUTO_AWESOME, color=ft.Colors.PURPLE, size=18),
                            ft.Text("AI 智能学习诊断报告", size=16, weight="bold"),
                        ]),
                        ft.Text(report_content, size=13, selectable=True),
                    ], spacing=10),
                    padding=16,
                    bgcolor=ft.Colors.PURPLE_50,
                    border_radius=12,
                    border=ft.Border.all(1, ft.Colors.PURPLE_100),
                )
            else:
                ai_section = ft.Row([
                    ft.ProgressRing(width=16, height=16, stroke_width=2),
                    ft.Text(" AI 正在生成详细分析报告...", italic=True, color=AppColors.TEXT_SECONDARY, size=13),
                ], spacing=10)

            # ===== 错题展开列表 =====
            wrong_section = ft.Container() if wrong_count == 0 else ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.ERROR_OUTLINE, color=ft.Colors.RED, size=18),
                        ft.Text(f"错题回顾（{wrong_count} 题）", size=16, weight="bold"),
                    ]),
                    wrong_list,
                ], spacing=10, scroll=ft.ScrollMode.AUTO),
                padding=ft.Padding.only(top=12),
            )

            return ft.Column([
                ft.Container(
                    content=ft.Column([
                        ft.Text("考试结束", size=28, weight="bold", color=ft.Colors.BLUE_GREY_900),
                        ft.Text(f"得分: {score} / {total}", size=22, weight="w500", color=ft.Colors.BLUE_600),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    alignment=ft.Alignment(0, 0),
                    padding=20,
                ),
                ft.Container(
                    content=local_report,
                    padding=16,
                    bgcolor=ft.Colors.BLUE_50,
                    border_radius=12,
                ),
                ai_section,
                wrong_section,
                ft.Container(height=20),
                ft.Row([
                    ft.ElevatedButton("返回首页", icon=ft.Icons.HOME, on_click=restart),
                    ft.OutlinedButton("去错题本练习", icon=ft.Icons.BOOKMARK, on_click=lambda _: (reset_state(), self.page.update()) or None),
                ], alignment=ft.MainAxisAlignment.CENTER),
            ], spacing=12, scroll=ft.ScrollMode.AUTO)

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
