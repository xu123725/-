import random
import flet as ft
from ui.state import StateManager
from db.database import get_connection
from db import crud
from ui.theme import AppColors, AppStyles


class DashboardView:
    def __init__(self, page: ft.Page, state: StateManager):
        self.page = page
        self.state = state
        self._bar_data = {k: [random.randint(8, 36) for _ in range(16)] for k in range(10)}

    def _stat_card(self, value: str, label: str, gradient: ft.LinearGradient):
        return ft.Container(
            content=ft.Column([
                ft.Text(value, size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ft.Text(label, size=12, color=ft.Colors.with_opacity(0.85, ft.Colors.WHITE)),
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4),
            gradient=gradient,
            border_radius=20,
            padding=ft.Padding.symmetric(horizontal=24, vertical=18),
            shadow=AppStyles.CARD_SHADOW,
            expand=True,
            height=100,
        )

    def _chart_card(self, title: str, seed: int, bar_color: str):
        data = self._bar_data[seed]
        max_val = max(data, default=36)
        y_labels_count = 4
        axis_color = "#CBD5E1"

        # 柱状条
        bars = []
        for v in data:
            h = max(4, int(v / max_val * 85))
            bars.append(
                ft.Column([
                    ft.Container(width=9, height=h, bgcolor=bar_color, border_radius=3),
                ], alignment=ft.MainAxisAlignment.END, expand=True)
            )

        # Y 轴刻度标签（左侧）
        y_labels = ft.Column([
            ft.Text(str(max_val), size=10, color=axis_color),
            ft.Text(str(max_val // 2), size=10, color=axis_color),
            ft.Text("0", size=10, color=axis_color),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, expand=True)

        # 柱状图区域 + Y 轴
        chart_body = ft.Row([
            ft.Container(content=y_labels, width=24, padding=ft.Padding.only(right=4)),
            ft.Container(
                content=ft.Row(bars, spacing=4, alignment=ft.MainAxisAlignment.CENTER, expand=True),
                border=ft.Border(
                    left=ft.BorderSide(1, axis_color),
                    bottom=ft.BorderSide(1, axis_color),
                ),
                padding=ft.Padding.only(left=4, right=5, top=6, bottom=1),
                expand=True,
            ),
        ], spacing=0, expand=True)

        # X 轴刻度（底部）
        x_count = len(data)
        x_ticks = ft.Row(
            [ft.Text(f"第{i+1}次", size=9, color=axis_color) for i in range(0, x_count, 4)],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        chart = ft.Column([
            chart_body,
            ft.Row([ft.Container(width=24), x_ticks], spacing=0, expand=True),
        ], spacing=2, expand=True)

        return ft.Container(
            content=ft.Column([
                ft.Text(title, size=13, weight=ft.FontWeight.W_600, color=AppColors.TEXT_SECONDARY),
                chart,
            ], spacing=6, expand=True),
            padding=16,
            bgcolor=AppColors.SURFACE,
            border_radius=20,
            shadow=AppStyles.CARD_SHADOW,
            expand=True,
            height=220,
        )

    def build(self) -> ft.Control:
        with get_connection() as conn:
            total_q = crud.get_total_question_count(conn)
            avg_acc = crud.get_average_accuracy(conn)
            wrong_count = crud.get_pending_wrong_question_count(conn)

        stat_row = ft.ResponsiveRow([
            ft.Container(
                content=self._stat_card(
                    str(total_q), "题库总量",
                    ft.LinearGradient([AppColors.PRIMARY, "#38BDF8"]),
                ),
                col={"sm": 6, "md": 3},
            ),
            ft.Container(
                content=self._stat_card(
                    f"{avg_acc:.0f}%", "平均正确率",
                    ft.LinearGradient([AppColors.SECONDARY, "#2DD4BF"]),
                ),
                col={"sm": 6, "md": 3},
            ),
            ft.Container(
                content=self._stat_card(
                    str(wrong_count), "待攻克错题",
                    ft.LinearGradient([AppColors.ACCENT, "#FBBF24"]),
                ),
                col={"sm": 6, "md": 3},
            ),
            ft.Container(
                content=self._stat_card(
                    str(max(0, int(total_q * avg_acc / 100))), "正确答题数",
                    ft.LinearGradient([AppColors.SUCCESS, "#34D399"]),
                ),
                col={"sm": 6, "md": 3},
            ),
        ], spacing=16, run_spacing=16)

        # 词云评价 - 浅色主题
        cloud_card = ft.Container(
            content=ft.Column([
                ft.Text("学习评价词云", size=13, weight=ft.FontWeight.W_600, color=AppColors.TEXT_SECONDARY),
                ft.Row([
                    ft.Column([
                        ft.Text("积极 →", size=11, color=AppColors.SUCCESS, weight=ft.FontWeight.BOLD),
                        ft.Text("清晰 喜欢 太棒了 感谢 易懂 实用 高效 深入浅出 受益匪浅",
                                size=11, color=AppColors.TEXT_SECONDARY),
                    ], spacing=4),
                    ft.VerticalDivider(width=20, color=AppColors.BACKGROUND),
                    ft.Column([
                        ft.Text("消极 →", size=11, color=AppColors.ERROR, weight=ft.FontWeight.BOLD),
                        ft.Text("难度大 网速慢 内容少",
                                size=11, color=AppColors.TEXT_SECONDARY),
                    ], spacing=4),
                ], spacing=20),
            ], spacing=10, expand=True),
            padding=16,
            bgcolor=AppColors.SURFACE,
            border_radius=20,
            shadow=AppStyles.CARD_SHADOW,
            expand=True,
            height=140,
        )

        # 成绩趋势
        trend_card = self._chart_card("成绩走向 / 预测趋势", 0, AppColors.PRIMARY)

        # 左侧维度
        col_left = ft.Column([
            self._chart_card("信息感知维度", 1, "#6366F1"),
            self._chart_card("信息投入维度", 2, "#8B5CF6"),
            self._chart_card("信息加工维度", 3, "#EC4899"),
        ], expand=1, spacing=14)

        # 中间
        col_mid = ft.Column([cloud_card, trend_card], expand=2, spacing=14)

        # 右侧维度
        col_right = ft.Column([
            self._chart_card("学习态度维度", 4, "#F59E0B"),
            self._chart_card("信息接收维度", 5, "#10B981"),
            self._chart_card("社会化交互维度", 6, "#3B82F6"),
        ], expand=1, spacing=14)

        return ft.Container(
            content=ft.Column([
                AppStyles.page_header(
                    "学情分析", "学习行为数据智能可视化，多维度评估学习成效",
                    ft.Icons.INSIGHTS_ROUNDED,
                ),
                stat_row,
                ft.Container(height=8),
                ft.Row([col_left, col_mid, col_right], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, expand=True),
            ], spacing=8, expand=True, scroll=ft.ScrollMode.AUTO),
            expand=True,
            padding=20,
        )
