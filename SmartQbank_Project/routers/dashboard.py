from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import traceback

from db.database import get_db
from db import crud

router = APIRouter()

@router.get("/stats")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """获取仪表盘统计数据"""
    try:
        total_questions = crud.get_total_question_count(db)
        average_accuracy = crud.get_average_accuracy(db)
        pending_wrong = crud.get_pending_wrong_question_count(db)
        
        # 计算健康快照
        health = crud.fetch_import_health_snapshot(db, lookback_hours=24)
        
        return {
            "total_questions": total_questions,
            "average_accuracy": average_accuracy,
            "pending_wrong": pending_wrong,
            "import_health": health
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
