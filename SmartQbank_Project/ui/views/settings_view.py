import flet as ft
import httpx
import asyncio
import os
from db.database import backup_database
from config import (
    load_settings, 
    save_settings, 
    refresh_config, 
    DEFAULT_API_BASE_URL, 
    DEFAULT_API_MODEL,
    get_api_key,
    get_api_base_url,
    get_api_model
)

class SettingsView:
    def __init__(self, page: ft.Page, state):
        self.page = page
        self.state = state
        self.api_key_field = ft.TextField(
            label="用户 Token / API Key",
            password=True,
            can_reveal_password=True,
            value=get_api_key(),
            hint_text="请输入由管理员分发的 Token 或 OpenAI 兼容的 API Key",
            width=600,
        )
        self.base_url_field = ft.TextField(
            label="网关地址 / API Base URL",
            value=get_api_base_url(),
            hint_text=DEFAULT_API_BASE_URL,
            width=600,
        )
        self.model_field = ft.TextField(
            label="模型名称",
            value=get_api_model(),
            hint_text=DEFAULT_API_MODEL,
            width=600,
        )
        self.status_text = ft.Text("", color=ft.Colors.GREY_600)

    async def test_connection(self, e):
        self.status_text.value = "正在测试连接..."
        self.status_text.color = ft.Colors.BLUE
        self.page.update()
        
        api_key = self.api_key_field.value.strip()
        base_url = self.base_url_field.value.strip().rstrip("/")
        
        try:
            # 尝试调用网关的用量接口或简单的 chat completions
            # 这里我们尝试调用 /v1/models 或一个极简的 chat 请求来验证
            headers = {"Authorization": f"Bearer {api_key}"}
            async with httpx.AsyncClient(timeout=10.0) as client:
                # 优先尝试网关特有的用量接口，如果失败则尝试标准 models 接口
                resp = await client.get(f"{base_url}/usage/me", headers=headers)
                if resp.status_code == 404:
                    resp = await client.get(f"{base_url}/models", headers=headers)
                
                if resp.status_code < 400:
                    self.status_text.value = "✅ 连接成功！网关响应正常。"
                    self.status_text.color = ft.Colors.GREEN
                else:
                    self.status_text.value = f"❌ 连接失败: 状态码 {resp.status_code} ({resp.text[:50]}...)"
                    self.status_text.color = ft.Colors.RED
        except Exception as ex:
            self.status_text.value = f"❌ 网络错误: {str(ex)}"
            self.status_text.color = ft.Colors.RED
        
        self.page.update()

    def save_config(self, e):
        settings = load_settings()
        settings["api_key"] = self.api_key_field.value.strip()
        settings["api_base_url"] = self.base_url_field.value.strip()
        settings["api_model"] = self.model_field.value.strip()
        
        save_settings(settings)
        refresh_config() # 刷新内存中的全局变量
        
        self.page.snack_bar = ft.SnackBar(ft.Text("配置已保存，部分设置可能需要重启应用生效"))
        self.page.snack_bar.open = True
        self.page.update()

    def do_backup(self, e):
        try:
            path = backup_database()
            self.page.snack_bar = ft.SnackBar(ft.Text(f"✅ 备份成功！文件保存在: {os.path.basename(path)}"))
            self.page.snack_bar.open = True
        except Exception as ex:
            self.page.snack_bar = ft.SnackBar(ft.Text(f"❌ 备份失败: {str(ex)}"))
            self.page.snack_bar.open = True
        self.page.update()

    def build(self):
        return ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.SETTINGS, size=30, color=ft.Colors.BLUE),
                        ft.Text("系统设置", size=28, weight="bold"),
                    ],
                    alignment=ft.MainAxisAlignment.START,
                ),
                ft.Divider(height=20, thickness=1),
                
                # API 配置部分
                ft.Text("API 与网关配置", size=18, weight="bold"),
                ft.Text("配置后即可通过你的托管网关或直接调用大模型 API。"),
                ft.Container(height=10),
                self.api_key_field,
                self.base_url_field,
                self.model_field,
                ft.Row(
                    [
                        ft.ElevatedButton(
                            "测试连接", 
                            icon=ft.Icons.NETWORK_CHECK, 
                            on_click=self.test_connection,
                            style=ft.ButtonStyle(color=ft.Colors.BLUE)
                        ),
                        ft.ElevatedButton(
                            "保存配置", 
                            icon=ft.Icons.SAVE, 
                            on_click=self.save_config,
                            bgcolor=ft.Colors.BLUE,
                            color=ft.Colors.WHITE
                        ),
                    ],
                    spacing=20,
                ),
                self.status_text,
                
                ft.Divider(height=30),
                
                # 数据管理部分
                ft.Text("数据管理", size=18, weight="bold"),
                ft.Text("您可以对本地题库和知识库进行备份，以防数据丢失。"),
                ft.Row(
                    [
                        ft.ElevatedButton(
                            "备份数据库", 
                            icon=ft.Icons.BACKUP, 
                            on_click=self.do_backup,
                            bgcolor=ft.Colors.ORANGE_600,
                            color=ft.Colors.WHITE
                        ),
                        ft.OutlinedButton(
                            "打开数据目录", 
                            icon=ft.Icons.FOLDER_OPEN,
                            on_click=lambda _: os.startfile(os.path.dirname(os.path.abspath(backup_database()))) if hasattr(os, "startfile") else None
                        ),
                    ],
                    spacing=20,
                ),

                ft.Divider(height=40),
                ft.Text("关于项目", size=18, weight="bold"),
                ft.Text("自动气象站智慧学习平台 v1.1.0"),
                ft.Text("基于 Flet 与 DeepSeek 构建，集成了智能题库、智慧学习诊断与排障指南。"),
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            spacing=20,
        )
