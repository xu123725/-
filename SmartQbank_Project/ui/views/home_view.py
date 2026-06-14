import flet as ft
from ui.state import StateManager
from ui.theme import AppColors, AppStyles
from db.database import get_connection
from db import crud

class HomeView:
    def __init__(self, page: ft.Page, state: StateManager, on_nav):
        self.page = page
        self.state = state
        self.on_nav = on_nav
        
        # 加载真实统计数据
        with get_connection() as conn:
            self.total_questions = crud.get_total_question_count(conn)
            self.avg_accuracy = crud.get_average_accuracy(conn)
            self.pending_wrong = crud.get_pending_wrong_question_count(conn)

    def build(self) -> ft.Control:
        def create_bento_card(title, icon, description, index, color=AppColors.PRIMARY, col=4, height=180, bgcolor=None, gradient=None):
            return ft.Container(
                content=ft.Column([
                    ft.Icon(icon, size=32, color=ft.Colors.WHITE if (bgcolor or gradient) else color),
                    ft.Column([
                        ft.Text(title, size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE if (bgcolor or gradient) else AppColors.TEXT_PRIMARY),
                        ft.Text(description, size=13, color=ft.Colors.with_opacity(0.65, ft.Colors.WHITE) if (bgcolor or gradient) else AppColors.TEXT_SECONDARY),
                    ], spacing=4),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                padding=24,
                bgcolor=bgcolor if bgcolor else (None if gradient else AppColors.SURFACE),
                gradient=gradient,
                border_radius=24,
                on_click=lambda _: self.on_nav(index),
                shadow=AppStyles.CARD_SHADOW,
                animate=ft.Animation(300, ft.AnimationCurve.EASE_OUT),
                col=col,
                height=height,
            )

        # 欢迎卡片 (大) - 优化排版与对齐
        welcome_card = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.WB_SUNNY_ROUNDED, color=ft.Colors.WHITE, size=40),
                    ft.Column([
                        ft.Text("早安，气象业务员", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        ft.Text("今天也是精进业务的一天。", color=ft.Colors.with_opacity(0.9, ft.Colors.WHITE)),
                    ], spacing=2),
                ], alignment=ft.MainAxisAlignment.START),
                ft.Container(height=10), # 增加呼吸感
                ft.Divider(height=1, color=ft.Colors.with_opacity(0.2, ft.Colors.WHITE)),
                ft.Row([
                    ft.Column([
                        ft.Text(f"{self.total_questions}", size=28, weight="bold", color=ft.Colors.WHITE),
                        ft.Text("已入库题目", size=12, color=ft.Colors.with_opacity(0.8, ft.Colors.WHITE)),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True),
                    ft.VerticalDivider(width=1, color=ft.Colors.with_opacity(0.3, ft.Colors.WHITE)),
                    ft.Column([
                        ft.Text(f"{self.avg_accuracy:.0f}%", size=28, weight="bold", color=ft.Colors.WHITE),
                        ft.Text("平均正确率", size=12, color=ft.Colors.with_opacity(0.8, ft.Colors.WHITE)),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True),
                    ft.VerticalDivider(width=1, color=ft.Colors.with_opacity(0.3, ft.Colors.WHITE)),
                    ft.Column([
                        ft.Text(f"{self.pending_wrong}", size=28, weight="bold", color=ft.Colors.WHITE),
                        ft.Text("待攻克错题", size=12, color=ft.Colors.with_opacity(0.8, ft.Colors.WHITE)),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True),
                ], alignment=ft.MainAxisAlignment.SPACE_EVENLY, height=80),
            ], alignment=ft.MainAxisAlignment.CENTER),
            padding=ft.Padding.only(left=30, right=30, top=40, bottom=30), # 增加顶部边距
            gradient=ft.LinearGradient(
                begin=ft.Alignment.TOP_LEFT,
                end=ft.Alignment.BOTTOM_RIGHT,
                colors=[AppColors.PRIMARY, "#64B5F6"],
            ),
            border_radius=24,
            shadow=AppStyles.CARD_SHADOW,
            col={"sm": 12, "md": 8},
            height=220, # 稍微增加高度以容纳更多呼吸空间
        )

        # AI 助手快捷卡片 (小) - 增加饱满度
        ai_card = ft.Container(
            content=ft.Stack([
                # 背景装饰图标
                ft.Container(
                    content=ft.Icon(ft.Icons.AUTO_AWESOME_ROUNDED, color=ft.Colors.with_opacity(0.15, ft.Colors.WHITE), size=120),
                    right=-20,
                    bottom=-20,
                ),
                ft.Column([
                    ft.Icon(ft.Icons.AUTO_AWESOME_ROUNDED, color=ft.Colors.WHITE, size=32),
                    ft.Column([
                        ft.Text("AI 智能组卷", size=20, weight="bold", color=ft.Colors.WHITE),
                        ft.Text("基于考点热度精准生成", size=13, color=ft.Colors.with_opacity(0.9, ft.Colors.WHITE)),
                    ], spacing=8),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ]),
            padding=24,
            gradient=ft.LinearGradient(
                begin=ft.Alignment.TOP_LEFT,
                end=ft.Alignment.BOTTOM_RIGHT,
                colors=[AppColors.SECONDARY, "#4DB6AC"],
            ),
            border_radius=24,
            on_click=lambda _: self.on_nav(2),
            shadow=AppStyles.CARD_SHADOW,
            col={"sm": 6, "md": 4},
            height=220, # 与左侧对齐
        )

        features = [
            # 标题, 图标, 描述, 索引, 颜色(备用), 列宽, 高度, 背景色, 渐变
            ("题库管理", ft.Icons.ACCOUNT_TREE_ROUNDED, "智能解析 Docx/PDF 入库", 1, None, 4, 180, None, 
             ft.LinearGradient([ft.Colors.BLUE_700, ft.Colors.BLUE_500])),
            
            ("模拟考试", ft.Icons.QUIZ_ROUNDED, "全仿真环境 实时诊断", 3, None, 4, 180, None, 
             ft.LinearGradient([ft.Colors.GREEN_700, ft.Colors.GREEN_500])),
            
            ("错题强化", ft.Icons.BOOKMARK_ROUNDED, "薄弱环节 针对性巩固", 4, None, 4, 180, None, 
             ft.LinearGradient([ft.Colors.AMBER_700, ft.Colors.AMBER_500])),
            
            ("排障实操", ft.Icons.HANDYMAN_ROUNDED, "交互式故障 案例模拟", 5, None, 6, 180, None, 
             ft.LinearGradient([ft.Colors.RED_700, ft.Colors.RED_500])),
            
            ("系统设置", ft.Icons.SETTINGS_SUGGEST_ROUNDED, "个性化学习 环境配置", 6, None, 6, 180, None, 
             ft.LinearGradient([ft.Colors.BLUE_GREY_700, ft.Colors.BLUE_GREY_500])),
        ]

        bento_cards = [welcome_card, ai_card]
        for f in features:
            bento_cards.append(create_bento_card(f[0], f[1], f[2], f[3], f[4], f[5], f[6], f[7], f[8]))

        return ft.Container(
            content=ft.Column([
                ft.ResponsiveRow(
                    bento_cards,
                    spacing=20,
                    run_spacing=20,
                ),
                ft.Container(height=20),
                # 提示横幅
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.TIPS_AND_UPDATES_ROUNDED, color=ft.Colors.WHITE, size=20),
                        ft.Text("提示：最近考试中“传感器维护”类题目错误率较高，建议重点练习。", color=ft.Colors.WHITE, size=13, weight=ft.FontWeight.W_500),
                    ], spacing=10),
                    padding=ft.Padding.symmetric(horizontal=20, vertical=14),
                    bgcolor=ft.Colors.with_opacity(0.9, AppColors.ACCENT), # 提高不透明度以增强对比度
                    border_radius=12,
                )
            ], scroll=ft.ScrollMode.AUTO, expand=True),
            expand=True,
        )
