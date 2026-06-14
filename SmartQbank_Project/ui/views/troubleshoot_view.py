import flet as ft
from core.troubleshoot_processor import scan_troubleshooting_resources, search_troubleshooting
from ui.state import StateManager
from pathlib import Path
import os

class TroubleshootView:
    def __init__(self, page: ft.Page, state: StateManager):
        self.page = page
        self.state = state
        self.results_column = ft.Column(spacing=10, scroll=ft.ScrollMode.ADAPTIVE, expand=True)
        self.search_input = ft.TextField(
            hint_text="搜索故障名称、类别或关键词...",
            prefix_icon=ft.Icons.SEARCH,
            on_submit=self.on_search_click,
            expand=True
        )

    def build(self):
        # 初始加载时扫描资源
        scan_troubleshooting_resources()
        self.load_results()

        main_content = ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("故障排查资源库", size=32, weight="bold", color=ft.Colors.BLUE_GREY_900),
                        ft.IconButton(
                            ft.Icons.REFRESH, 
                            on_click=self.on_refresh_click, 
                            tooltip="重新扫描资源",
                            icon_color=ft.Colors.BLUE_600,
                            icon_size=28
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                ),
                ft.Container(
                    content=ft.Row(
                        [
                            self.search_input,
                            ft.ElevatedButton(
                                "智能搜索", 
                                icon=ft.Icons.SEARCH, 
                                on_click=self.on_search_click,
                                style=ft.ButtonStyle(
                                    shape=ft.RoundedRectangleBorder(radius=8),
                                    padding=ft.Padding.all(16),
                                    bgcolor=ft.Colors.BLUE_600,
                                    color=ft.Colors.WHITE
                                )
                            ),
                        ],
                        spacing=12
                    ),
                    padding=ft.Padding.only(bottom=10)
                ),
                ft.Divider(height=2, color=ft.Colors.BLUE_GREY_100),
                self.results_column
            ],
            expand=True,
            spacing=20
        )

        return ft.Container(
            content=main_content,
            padding=20,
            expand=True
        )

    def on_refresh_click(self, e):
        res = scan_troubleshooting_resources()
        # 旧版 Flet 显示 SnackBar 的方式
        self.page.snack_bar = ft.SnackBar(ft.Text(f"同步完成，发现 {res.get('count', 0)} 个资源"))
        self.page.snack_bar.open = True
        self.load_results()
        self.page.update()

    def on_search_click(self, e):
        self.load_results(self.search_input.value)
        self.page.update()

    def load_results(self, keyword=""):
        items = search_troubleshooting(keyword)
        self.results_column.controls.clear()
        
        if not items:
            self.results_column.controls.append(
                ft.Container(
                    content=ft.Text("未找到相关资源", size=16, color=ft.Colors.GREY_500),
                    alignment=ft.Alignment(0, 0),
                    padding=40
                )
            )
        else:
            categories = {}
            for item in items:
                cat = item['category']
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(item)
            
            for cat, cat_items in categories.items():
                self.results_column.controls.append(
                    ft.Text(cat, size=20, weight="bold", color=ft.Colors.BLUE_700)
                )
                grid = ft.ResponsiveRow(spacing=10, run_spacing=10)
                for item in cat_items:
                    grid.controls.append(self.build_item_card(item))
                self.results_column.controls.append(grid)
                self.results_column.controls.append(ft.Container(height=10))

    def build_item_card(self, item):
        has_video = bool(item['video_path'])
        has_doc = bool(item['doc_path'])
        has_image = bool(item.get('image_path'))
        icons = []
        if has_video: icons.append(ft.Icon(ft.Icons.PLAY_CIRCLE_FILL, color=ft.Colors.RED_400, size=20, tooltip="包含视频"))
        if has_doc: icons.append(ft.Icon(ft.Icons.DESCRIPTION, color=ft.Colors.BLUE_400, size=20, tooltip="包含文档"))
        if has_image: icons.append(ft.Icon(ft.Icons.IMAGE, color=ft.Colors.GREEN_400, size=20, tooltip="包含流程图"))

        # 使用最原始的函数绑定
        def handle_click(e):
            print(f"点击了: {item['title']}")
            self.show_details(item)

        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Row([
                                ft.Icon(ft.Icons.BUILD_CIRCLE, color=ft.Colors.BLUE_GREY_400, size=24),
                                ft.Text(item['title'], weight="bold", size=16, color=ft.Colors.BLUE_GREY_900, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ], expand=True),
                            ft.Row(icons, spacing=6)
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                    ),
                    ft.Text(
                        item['description'] or "该资源暂无详细文字描述...", 
                        size=13, 
                        color=ft.Colors.GREY_600, 
                        max_lines=2,
                        overflow=ft.TextOverflow.ELLIPSIS
                    ),
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.TextButton(
                                    "快速查看", 
                                    icon=ft.Icons.ARROW_FORWARD_IOS, 
                                    icon_color=ft.Colors.BLUE_600,
                                    style=ft.ButtonStyle(color=ft.Colors.BLUE_600),
                                    on_click=handle_click
                                )
                            ],
                            alignment=ft.MainAxisAlignment.END
                        ),
                        margin=ft.Margin.only(top=8)
                    )
                ],
                spacing=10
            ),
            padding=ft.Padding.all(20), 
            bgcolor=ft.Colors.WHITE, 
            border=ft.Border.all(1, ft.Colors.BLUE_GREY_50), 
            border_radius=12, 
            col={"sm": 12, "md": 6, "lg": 4, "xl": 3},
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=10,
                color=ft.Colors.with_opacity(0.05, ft.Colors.BLUE_GREY_400),
                offset=ft.Offset(0, 4)
            ),
            on_hover=lambda e: self.on_card_hover(e)
        )

    def on_card_hover(self, e):
        e.control.shadow.color = ft.Colors.with_opacity(0.15 if e.data == "true" else 0.05, ft.Colors.BLUE_GREY_400)
        e.control.update()

    def show_details(self, item):
        content = ft.Column(spacing=20, tight=True, scroll=ft.ScrollMode.ADAPTIVE)
        # 获取项目的绝对根目录
        project_root = Path(__file__).parent.parent.parent
        
        def create_open_handler(path):
            return lambda e: self.safe_open_file(path)
        
        if item.get('video_path'):
            abs_path = (project_root / item['video_path']).resolve()
            content.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Row([ft.Icon(ft.Icons.VIDEOCAM, color=ft.Colors.RED_400), ft.Text("操作演示视频", weight="bold", size=18)]),
                        ft.ElevatedButton(
                            "打开本地视频文件",
                            icon=ft.Icons.PLAY_CIRCLE_FILL,
                            on_click=create_open_handler(abs_path),
                            style=ft.ButtonStyle(
                                shape=ft.RoundedRectangleBorder(radius=8),
                                padding=ft.Padding.all(15),
                                bgcolor=ft.Colors.RED_50,
                                color=ft.Colors.RED_700
                            )
                        )
                    ]),
                    padding=15,
                    bgcolor=ft.Colors.GREY_50,
                    border_radius=8
                )
            )
        
        if item.get('image_path'):
            abs_img_path = (project_root / item['image_path']).resolve()
            img_src = str(abs_img_path)
            content.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Row([ft.Icon(ft.Icons.IMAGE, color=ft.Colors.GREEN_400), ft.Text("故障流程图 / 参考图片", weight="bold", size=18)]),
                        ft.Container(
                            content=ft.Image(
                                src=img_src,
                                width=900,
                                fit="contain",
                                border_radius=ft.BorderRadius.all(10),
                            ),
                            border=ft.Border.all(1, ft.Colors.GREY_300),
                            border_radius=10,
                            padding=10,
                            bgcolor=ft.Colors.WHITE
                        ),
                        ft.TextButton(
                            "调用外部看图软件打开大图",
                            icon=ft.Icons.ZOOM_IN,
                            on_click=create_open_handler(abs_img_path),
                            style=ft.ButtonStyle(color=ft.Colors.GREEN_600)
                        )
                    ]),
                    padding=15,
                    bgcolor=ft.Colors.GREY_50,
                    border_radius=8
                )
            )

        if item['doc_path']:
            project_root = Path(__file__).parent.parent.parent
            abs_doc_path = (project_root / item['doc_path']).resolve()
            
            doc_container = ft.Column([
                ft.Row([ft.Icon(ft.Icons.DESCRIPTION, color=ft.Colors.BLUE_400), ft.Text("详细说明文档", weight="bold", size=18)]),
            ])
            
            try:
                try:
                    with open(abs_doc_path, 'r', encoding='utf-8') as f:
                        doc_text = f.read()
                except UnicodeDecodeError:
                    with open(abs_doc_path, 'r', encoding='gbk') as f:
                        doc_text = f.read()
                
                doc_container.controls.append(
                    ft.Container(
                        content=ft.Text(doc_text, size=14, selectable=True),
                        padding=15,
                        bgcolor=ft.Colors.WHITE,
                        border=ft.Border.all(1, ft.Colors.GREY_300),
                        border_radius=8,
                        width=900
                    )
                )
            except Exception as e:
                print(f"读取文档出错: {e}")
                doc_container.controls.append(ft.Text(f"无法在软件内预览文档内容: {e}", color=ft.Colors.RED))
                
            doc_container.controls.append(
                ft.TextButton(
                    "使用系统默认程序打开文档",
                    icon=ft.Icons.FILE_OPEN,
                    on_click=create_open_handler(abs_doc_path),
                    style=ft.ButtonStyle(color=ft.Colors.BLUE_600)
                )
            )
            
            content.controls.append(
                ft.Container(
                    content=doc_container,
                    padding=15,
                    bgcolor=ft.Colors.GREY_50,
                    border_radius=8
                )
            )

        def close_dlg(e):
            print("关闭弹窗")
            dlg.open = False
            self.page.update()

        dlg = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.Icons.INFO_OUTLINE, color=ft.Colors.BLUE_GREY_600),
                ft.Text(item['title'], size=24, weight="bold", color=ft.Colors.BLUE_GREY_800)
            ]),
            content=ft.Container(content, width=1000, height=800),
            actions=[
                ft.ElevatedButton(
                    "关闭", 
                    on_click=close_dlg,
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.BLUE_GREY_600,
                        color=ft.Colors.WHITE,
                        padding=ft.Padding.only(left=30, right=30, top=10, bottom=10)
                    )
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=16)
        )
        
        # 终极兼容方案：将弹窗加入页面的 overlay 中
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()
        print(f"弹窗已通过 overlay 发送显示指令: {item['title']}")

    def safe_open_file(self, path: Path):
        """安全地打开本地文件，并提供反馈"""
        print(f"尝试打开文件: {path}")
        if path.exists():
            try:
                os.startfile(str(path))
                print("打开成功")
            except Exception as e:
                self.page.snack_bar = ft.SnackBar(ft.Text(f"打开失败: {str(e)}"))
                self.page.snack_bar.open = True
        else:
            self.page.snack_bar = ft.SnackBar(ft.Text(f"找不到文件: {path.name}"))
            self.page.snack_bar.open = True
        self.page.update()