from __future__ import annotations
import flet as ft
from core.schemas import ExamPaper, ExamState

class StateManager:
    def __init__(self, page: ft.Page):
        self.page = page

        if not self.page.session.store.get("is_init"):
            self.page.session.store.set("exam_paper", None)
            self.page.session.store.set("exam_state", ExamState())
            self.page.session.store.set("generated_paper", None)
            self.page.session.store.set("chat_history", [])
            self.page.session.store.set("ai_float_open", False)
            self.page.session.store.set("is_init", True)

    @property
    def exam_paper(self) -> ExamPaper | None:
        return self.page.session.store.get("exam_paper")
        
    @exam_paper.setter
    def exam_paper(self, value: ExamPaper | None):
        self.page.session.store.set("exam_paper", value)
        
    @property
    def exam_state(self) -> ExamState:
        return self.page.session.store.get("exam_state")
        
    @exam_state.setter
    def exam_state(self, value: ExamState):
        self.page.session.store.set("exam_state", value)
        
    @property
    def generated_paper(self) -> list[dict] | None:
        return self.page.session.store.get("generated_paper")
        
    @generated_paper.setter
    def generated_paper(self, value: list[dict] | None):
        self.page.session.store.set("generated_paper", value)
        
    @property
    def chat_history(self) -> list[dict]:
        return self.page.session.store.get("chat_history")
        
    def add_chat_message(self, role: str, content: str):
        history = self.chat_history
        history.append({"role": role, "content": content})
        self.page.session.store.set("chat_history", history)

    @property
    def ai_float_open(self) -> bool:
        return bool(self.page.session.store.get("ai_float_open"))

    @ai_float_open.setter
    def ai_float_open(self, value: bool):
        self.page.session.store.set("ai_float_open", bool(value))
