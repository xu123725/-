import threading
import flet as ft
from ui.state import StateManager
from core import agent_logic
from ui.theme import AppColors, AppStyles

class ChatView:
    def __init__(self, page: ft.Page, state: StateManager):
        self.page = page
        self.state = state

    def _build_chat_content(self, on_close=None) -> ft.Control:
        chat_history = ft.ListView(expand=True, spacing=16, auto_scroll=True, padding=ft.Padding.only(bottom=10))
        
        user_input = ft.TextField(
            hint_text="询问业务知识或下达指令...",
            hint_style=ft.TextStyle(color=AppColors.TEXT_SECONDARY, size=14),
            expand=True,
            border_radius=12,
            bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.BLACK),
            border_color=ft.Colors.TRANSPARENT,
            focused_border_color=AppColors.PRIMARY,
            content_padding=ft.Padding.symmetric(horizontal=16, vertical=12),
            text_size=14,
        )
        
        send_button = ft.IconButton(
            icon=ft.Icons.SEND_ROUNDED,
            icon_color=AppColors.PRIMARY,
            tooltip="发送消息",
        )

        def create_message_bubble(role: str, content: str):
            is_user = (role == "user")
            return ft.Column(
                [
                    ft.Row([
                        ft.Icon(ft.Icons.PERSON_ROUNDED if is_user else ft.Icons.SMART_TOY_ROUNDED, size=14, color=AppColors.TEXT_SECONDARY),
                        ft.Text("您" if is_user else "AI 助手", size=11, color=AppColors.TEXT_SECONDARY, weight="bold"),
                    ], spacing=4, alignment=ft.MainAxisAlignment.END if is_user else ft.MainAxisAlignment.START),
                    ft.Container(
                        content=ft.Markdown(
                            content,
                            selectable=True,
                            extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                            code_theme="atom-one-dark",
                            on_tap_link=lambda e: self.page.launch_url(e.data),
                            style=ft.MarkdownStyleSheet(
                                p_text_style=ft.TextStyle(color=ft.Colors.WHITE if is_user else AppColors.TEXT_PRIMARY, size=14),
                                code_block_bg=ft.Colors.BLACK,
                            )
                        ) if not is_user else ft.Text(content, selectable=True, color=ft.Colors.WHITE, size=14),
                        bgcolor=AppColors.PRIMARY if is_user else ft.Colors.WHITE,
                        padding=14,
                        border_radius=ft.BorderRadius.only(
                            top_left=16, top_right=16, 
                            bottom_left=16 if is_user else 4, 
                            bottom_right=4 if is_user else 16
                        ),
                        shadow=ft.BoxShadow(spread_radius=0, blur_radius=5, color=ft.Colors.with_opacity(0.05, ft.Colors.BLACK)),
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.END if is_user else ft.CrossAxisAlignment.START,
            )

        for msg in self.state.chat_history:
            chat_history.controls.append(create_message_bubble(msg['role'], msg['content']))

        def send_message(_):
            prompt = (user_input.value or "").strip()
            if not prompt:
                return
            self.state.add_chat_message("user", prompt)
            chat_history.controls.append(create_message_bubble("user", prompt))
            
            # 助手消息容器
            assistant_col = ft.Column(
                [
                    ft.Row([
                        ft.Icon(ft.Icons.SMART_TOY_ROUNDED, size=14, color=AppColors.TEXT_SECONDARY),
                        ft.Text("AI 助手", size=11, color=AppColors.TEXT_SECONDARY, weight="bold"),
                    ], spacing=4),
                    ft.Container(
                        content=ft.Row([
                            ft.ProgressRing(width=14, height=14, stroke_width=2, color=AppColors.PRIMARY),
                            ft.Text("正在思考...", size=14, color=AppColors.TEXT_SECONDARY),
                        ], spacing=10),
                        bgcolor=ft.Colors.WHITE,
                        padding=14,
                        border_radius=ft.BorderRadius.only(top_left=16, top_right=16, bottom_right=16),
                        shadow=ft.BoxShadow(spread_radius=0, blur_radius=5, color=ft.Colors.with_opacity(0.05, ft.Colors.BLACK)),
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.START,
            )
            chat_history.controls.append(assistant_col)
            
            user_input.value = ""
            user_input.disabled = True
            send_button.disabled = True
            self.page.update()

            def worker():
                try:
                    response_text = agent_logic.process_user_request(prompt, self.state)
                    assistant_col.controls[1].content = ft.Markdown(
                        response_text,
                        selectable=True,
                        extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                        code_theme="atom-one-dark",
                        style=ft.MarkdownStyleSheet(
                            p_text_style=ft.TextStyle(color=AppColors.TEXT_PRIMARY, size=14),
                        )
                    )
                    self.state.add_chat_message("assistant", response_text)
                except Exception as ex:
                    error_text = f"出错了: {str(ex)}"
                    assistant_col.controls[1].content = ft.Text(error_text, color=AppColors.ERROR, size=14)
                    self.state.add_chat_message("assistant", error_text)
                user_input.disabled = False
                send_button.disabled = False
                self.page.update()

            threading.Thread(target=worker, daemon=True).start()

        send_button.on_click = send_message
        user_input.on_submit = send_message
        
        header_row = ft.Row([
            ft.Icon(ft.Icons.AUTO_AWESOME_ROUNDED, color=AppColors.PRIMARY, size=24),
            ft.Text("智能助手", size=18, weight="bold", color=AppColors.TEXT_PRIMARY),
            ft.Container(expand=True),
            ft.IconButton(ft.Icons.CLOSE_ROUNDED, icon_color=AppColors.TEXT_SECONDARY, on_click=on_close) if on_close else ft.Container(),
        ], alignment=ft.MainAxisAlignment.CENTER)

        return ft.Column([
            header_row,
            ft.Divider(height=1, color=ft.Colors.with_opacity(0.05, ft.Colors.BLACK)),
            chat_history,
            ft.Container(
                content=ft.Row([user_input, send_button], spacing=4),
                padding=ft.Padding.only(top=10),
            ),
        ], expand=True)

    def build_panel(self, on_close=None) -> ft.Control:
        return ft.Container(content=self._build_chat_content(on_close=on_close), expand=True, padding=20)

    def build(self) -> ft.Control:
        return self.build_panel()
