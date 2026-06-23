from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.orm import Session

from db.database import get_db
from db import crud
from core.schemas import WrongQuestionView

router = APIRouter()

@router.get("/list", response_model=List[WrongQuestionView])
async def get_wrong_book(limit: int = 100, order_by: str = "recent", db: Session = Depends(get_db)):
    """获取错题本列表"""
    try:
        return crud.list_wrong_questions(db, limit=limit, order_by=order_by)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{question_id}")
async def remove_wrong_question(question_id: int, db: Session = Depends(get_db)):
    """从错题本移除某道题 (软删除)"""
    try:
        crud.remove_wrong_question(db, question_id)
        return {"status": "success", "message": "Removed from wrong book"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
