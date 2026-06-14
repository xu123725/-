import logging
import os
import sys

import flet as ft
from config import DATA_DIR, BASE_DIR, run_startup_checks
from ui.state import StateManager
from ui.theme import AppColors, AppStyles
from ui.views.import_view import ImportView
from ui.views.generate_view import GenerateView
from ui.views.exam_view import ExamView
from ui.views.wrong_book_view import WrongBookView
from ui.views.chat_view import ChatView
from ui.views.troubleshoot_view import TroubleshootView
from ui.views.settings_view import SettingsView
from ui.views.home_view import HomeView
from db.database import init_app_environment
from utils.logger import setup_logging

setup_logging(DATA_DIR / "app.log")
logger = logging.getLogger(__name__)

def main(page: ft.Page):
    init_app_environment()

    check_result = run_startup_checks()
    for msg in check_result["warnings"]:
        logger.warning(msg)
    if check_result["fatals"]:
        for msg in check_result["fatals"]:
            logger.error(msg)

    page.title = "自动气象站智慧学习平台"
    page.window_width = 1280
    page.window_height = 850
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = AppColors.BACKGROUND
    page.padding = 0
    page.spacing = 0

    if check_result["mode"] == "strict" and check_result["fatals"]:
        page.add(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text("启动自检未通过", size=24, weight="bold", color=ft.Colors.RED),
                        ft.Text("请修复以下问题后重启应用："),
                        ft.Column([ft.Text(f"- {item}") for item in check_result["fatals"]]),
                    ],
                    spacing=12,
                ),
                padding=24,
            )
        )
        return

    state = StateManager(page)

    def show_view(index: int):
        rail.selected_index = index
        content_area.content = views[index].build()
        page.update()

    chat_view = ChatView(page, state)
    views = {
        0: HomeView(page, state, lambda idx: show_view(idx)),
        1: ImportView(page, state),
        2: GenerateView(page, state),
        3: ExamView(page, state),
        4: WrongBookView(page, state, lambda index: show_view(index)),
        5: TroubleshootView(page, state),
        6: SettingsView(page, state),
    }

    content_area = ft.Container(
        content=views[0].build(),
        expand=True,
        padding=ft.Padding.all(24),
        animate=ft.Animation(300, ft.AnimationCurve.DECELERATE),
    )

    def on_nav_change(e):
        show_view(e.control.selected_index)

    # 侧边导航栏
    rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=100,
        min_extended_width=200,
        group_alignment=-0.9,
        bgcolor=AppColors.SURFACE,
        selected_label_text_style=ft.TextStyle(color=AppColors.PRIMARY, weight=ft.FontWeight.BOLD, size=13),
        unselected_label_text_style=ft.TextStyle(color=AppColors.TEXT_SECONDARY, size=13),
        indicator_color=ft.Colors.with_opacity(0.15, AppColors.PRIMARY),
        indicator_shape=ft.RoundedRectangleBorder(radius=12),
        destinations=[
            ft.NavigationRailDestination(
                icon=ft.Icons.HOME_OUTLINED, 
                selected_icon=ft.Icons.HOME, 
                label="首页",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.LIBRARY_BOOKS_OUTLINED, 
                selected_icon=ft.Icons.LIBRARY_BOOKS, 
                label="题库",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.AUTO_AWESOME_OUTLINED, 
                selected_icon=ft.Icons.AUTO_AWESOME, 
                label="组卷",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.QUIZ_OUTLINED, 
                selected_icon=ft.Icons.QUIZ, 
                label="考试",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.BOOKMARK_BORDER, 
                selected_icon=ft.Icons.BOOKMARK, 
                label="错题本",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.BUILD_CIRCLE_OUTLINED, 
                selected_icon=ft.Icons.BUILD_CIRCLE, 
                label="排障",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.SETTINGS_OUTLINED, 
                selected_icon=ft.Icons.SETTINGS, 
                label="设置",
            ),
        ],
        on_change=on_nav_change,
        leading=ft.Container(
            content=ft.Icon(ft.Icons.CLOUD_SYNC_ROUNDED, size=40, color=AppColors.PRIMARY),
            padding=ft.Padding.only(top=20, bottom=20),
        ),
    )

    def close_ai_float(e=None):
        state.ai_float_open = False
        ai_float_container.visible = False
        page.update()

    def toggle_ai_float(e=None):
        state.ai_float_open = not state.ai_float_open
        ai_float_container.visible = state.ai_float_open
        if state.ai_float_open:
            ai_float_container.content = chat_view.build_panel(on_close=close_ai_float)
        page.update()

    # 优化后的 AI 助手容器
    ai_float_container = ft.Container(
        content=chat_view.build_panel(on_close=close_ai_float),
        width=400,
        height=600,
        visible=state.ai_float_open,
        right=24,
        bottom=100,
        border_radius=24,
        bgcolor=AppColors.SURFACE,
        border=ft.Border.all(1, ft.Colors.with_opacity(0.1, AppColors.TEXT_SECONDARY)),
        shadow=AppStyles.FLOAT_SHADOW,
        animate=ft.Animation(400, ft.AnimationCurve.EASE_OUT_BACK),
    )

    float_button = ft.FloatingActionButton(
        content=ft.Icon(ft.Icons.SMART_TOY_ROUNDED, color=ft.Colors.WHITE),
        tooltip="AI 业务助手",
        bgcolor=AppColors.SECONDARY,
        right=24,
        bottom=24,
        on_click=toggle_ai_float,
        shape=ft.RoundedRectangleBorder(radius=16),
    )

    # 顶栏装饰
    app_bar = ft.Container(
        content=ft.Row([
            AppStyles.title_text("自动气象站智慧学习平台", size=20),
            ft.Row([
                ft.Container(
                    content=ft.TextField(
                        hint_text="搜索功能或知识点...",
                        hint_style=ft.TextStyle(color=AppColors.TEXT_SECONDARY),
                        border_color=ft.Colors.TRANSPARENT,
                        bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.BLACK),
                        border_radius=12,
                        content_padding=ft.Padding.symmetric(horizontal=16, vertical=0),
                        height=40,
                        width=300,
                        suffix_icon=ft.Icons.SEARCH_ROUNDED,
                    ),
                ),
                ft.IconButton(ft.Icons.NOTIFICATIONS_OUTLINED, icon_color=AppColors.TEXT_SECONDARY),
                ft.CircleAvatar(content=ft.Text("JS"), bgcolor=AppColors.PRIMARY, radius=16),
            ], spacing=10)
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        padding=ft.Padding.symmetric(horizontal=24, vertical=12),
        bgcolor=AppColors.SURFACE,
        border=ft.Border(bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.1, ft.Colors.BLACK))),
    )

    page.add(
        ft.Row(
            [
                rail,
                ft.VerticalDivider(width=1, color=ft.Colors.with_opacity(0.05, ft.Colors.BLACK)),
                ft.Column(
                    [
                        app_bar,
                        ft.Stack(
                            [
                                content_area,
                                ai_float_container,
                                float_button,
                            ],
                            expand=True,
                        ),
                    ],
                    expand=True,
                    spacing=0,
                ),
            ],
            expand=True,
            spacing=0,
        )
    )

if __name__ == "__main__":
    ft.run(main, assets_dir=str(BASE_DIR / "assets"))
