from __future__ import annotations

from pydantic import BaseModel, Field


class QuestionBase(BaseModel):
    stem: str = Field(min_length=1)
    options: list[str] = Field(default_factory=list)
    answer: str = Field(min_length=1)
    question_type: str = "single"
    category: str = Field(min_length=1)
    tag: str = ""
    difficulty: int = Field(ge=1, le=5)
    analysis: str = ""


class QuestionCreate(QuestionBase):
    source: str = ""
    hash_val: str


class QuestionView(QuestionBase):
    id: int
    wrong_count: int = 0
    last_wrong_at: str = ""


class ExamPaperConfig(BaseModel):
    total_count: int = Field(ge=1)
    categories: list[str] = Field(default_factory=list)
    difficulty_ratio: dict[int, float] = Field(default_factory=dict)
    recent_hours: int = 24


class ParsedResult(BaseModel):
    questions: list[QuestionCreate] = Field(default_factory=list)
    total_chunks: int = 0
    success_chunks: int = 0
    failed_chunks: int = 0


class ImportStats(BaseModel):
    success: int = 0
    duplicate: int = 0
    failed: int = 0


class GenerateStats(ImportStats):
    rounds: int = 0

class WrongQuestionView(QuestionView):
    pass

class ExamPaper(BaseModel):
    questions: list[QuestionView] = Field(default_factory=list)
    config: ExamPaperConfig | None = None
    created_at: str = ""

class ExamState(BaseModel):
    is_running: bool = False
    submitted: bool = False
    mode: str = ""
    current_index: int = 0
    answers: dict[int, str] = Field(default_factory=dict)
    revealed: dict[int, bool] = Field(default_factory=dict)
    score: int = 0
    time_left: int = 0
    exam_report: str = ""
