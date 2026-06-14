import flet as ft

class AppColors:
    PRIMARY = "#0284C7"       # 深空蓝
    SECONDARY = "#0EA5E9"     # 亮天蓝
    ACCENT = "#F59E0B"        # 琥珀金
    BACKGROUND = "#F8FAFC"    # 极简白蓝背景
    SURFACE = "#FFFFFF"       # 纯白表面
    TEXT_PRIMARY = "#0F172A"  # 灰黑文字
    TEXT_SECONDARY = "#64748B" # 中灰文字
    GLASS_WHITE = "#E2E8F0AA" # 磨砂蓝灰
    ERROR = "#EF4444"         # 现代红
    SUCCESS = "#10B981"       # 翡翠绿

class AppStyles:
    # 阴影定义
    CARD_SHADOW = ft.BoxShadow(
        spread_radius=1,
        blur_radius=15,
        color=ft.Colors.with_opacity(0.1, ft.Colors.BLACK),
        offset=ft.Offset(0, 5),
    )
    
    FLOAT_SHADOW = ft.BoxShadow(
        spread_radius=0,
        blur_radius=20,
        color=ft.Colors.with_opacity(0.15, ft.Colors.BLACK),
        offset=ft.Offset(0, 10),
    )

    # 玻璃拟态容器
    @staticmethod
    def glass_container(content, padding=20, border_radius=16):
        return ft.Container(
            content=content,
            padding=padding,
            border_radius=border_radius,
            bgcolor=AppColors.GLASS_WHITE,
            blur=ft.Blur(10, 10, ft.BlurStyle.OUTER),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.2, ft.Colors.WHITE)),
            shadow=AppStyles.CARD_SHADOW,
        )

    # 标题样式
    @staticmethod
    def title_text(text, size=24, color=AppColors.TEXT_PRIMARY):
        return ft.Text(
            text,
            size=size,
            weight=ft.FontWeight.BOLD,
            color=color,
        )

    # 描述文字样式
    @staticmethod
    def desc_text(text, size=14, color=AppColors.TEXT_SECONDARY):
        return ft.Text(
            text,
            size=size,
            color=color,
        )

    # 通用页面标题组件
    @staticmethod
    def page_header(title, subtitle, icon=None):
        controls = []
        if icon:
            controls.append(ft.Icon(icon, size=30, color=AppColors.PRIMARY))
        
        text_column = ft.Column([
            AppStyles.title_text(title, size=24),
            AppStyles.desc_text(subtitle, size=14),
        ], spacing=2)
        
        controls.append(text_column)
        
        return ft.Container(
            content=ft.Row(controls, spacing=15, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.Padding.only(bottom=24),
        )

    # 现代按钮组件
    @staticmethod
    def primary_button(text, icon=None, on_click=None):
        return ft.ElevatedButton(
            content=ft.Row([
                ft.Icon(icon, size=18) if icon else ft.Container(),
                ft.Text(text, weight="bold"),
            ], alignment=ft.MainAxisAlignment.CENTER, tight=True),
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=AppColors.PRIMARY,
                padding=ft.Padding.symmetric(horizontal=24, vertical=16),
                shape=ft.RoundedRectangleBorder(radius=12),
            ),
            on_click=on_click,
        )
