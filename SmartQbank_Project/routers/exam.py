from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db
from db import crud
from core.schemas import QuestionView

router = APIRouter()

class ExamGenerateRequest(BaseModel):
    limit: int = 10
    question_type: str = "all"
    categories: List[str] = []
    prefer_wrong: bool = False
    prefer_unanswered: bool = False

@router.post("/generate", response_model=List[QuestionView])
async def generate_exam(req: ExamGenerateRequest, db: Session = Depends(get_db)):
    """生成一套模拟试卷"""
    try:
        questions = crud.fetch_exam_questions(
            conn=db,
            limit=req.limit,
            question_type=req.question_type,
            categories=req.categories,
            prefer_wrong=req.prefer_wrong,
            prefer_unanswered=req.prefer_unanswered,
        )
        return questions
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
