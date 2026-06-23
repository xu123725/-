from __future__ import annotations

import logging
from typing import Any
from sqlalchemy.orm import Session

from core.schemas import QuestionView
from db.crud import fetch_exam_questions, retrieve_knowledge

logger = logging.getLogger(__name__)

def retrieve_questions(
    conn: Session,
    total_count: int,
    categories: list[str],
    recent_hours: int = 24,
    question_type: str = "all",
) -> list[QuestionView]:
    return fetch_exam_questions(
        conn=conn,
        limit=total_count,
        question_type=question_type,
        categories=categories,
        prefer_wrong=False,
        prefer_unanswered=False,
    )