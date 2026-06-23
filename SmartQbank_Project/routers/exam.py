from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime
import json

from db.database import get_db
from db import crud
from db.models import ExamPaperRecord, Question
from core.schemas import QuestionView

router = APIRouter()

class ExamGenerateRequest(BaseModel):
    limit: int = 10
    question_type: str = "all"
    categories: List[str] = []
    prefer_wrong: bool = False
    prefer_unanswered: bool = False

class ExamPaperView(BaseModel):
    id: int
    title: str
    question_count: int
    created_at: str

@router.post("/generate")
async def generate_exam(req: ExamGenerateRequest, db: Session = Depends(get_db)):
    """生成一套模拟试卷并保存至数据库"""
    try:
        questions = crud.fetch_exam_questions(
            conn=db,
            limit=req.limit,
            question_type=req.question_type,
            categories=req.categories,
            prefer_wrong=req.prefer_wrong,
            prefer_unanswered=req.prefer_unanswered,
        )
        if not questions:
            return {"status": "failed", "message": "未能找到符合条件的题目"}
            
        # 保存试卷记录
        question_ids = [q.id for q in questions]
        title = f"模拟试卷 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        paper = ExamPaperRecord(
            title=title,
            question_ids=json.dumps(question_ids)
        )
        db.add(paper)
        db.commit()
        db.refresh(paper)
        
        return {"status": "success", "paper_id": paper.id}
    except Exception as e:
        import traceback
        traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/papers", response_model=List[ExamPaperView])
async def get_papers(db: Session = Depends(get_db)):
    """获取生成的试卷列表"""
    try:
        papers = db.query(ExamPaperRecord).order_by(ExamPaperRecord.id.desc()).all()
        return [
            ExamPaperView(
                id=p.id,
                title=p.title,
                question_count=len(json.loads(p.question_ids)),
                created_at=p.created_at.strftime('%Y-%m-%d %H:%M') if p.created_at else ""
            ) for p in papers
        ]
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/papers/{paper_id}", response_model=List[QuestionView])
async def get_paper_detail(paper_id: int, db: Session = Depends(get_db)):
    """获取某份试卷的具体题目"""
    try:
        paper = db.query(ExamPaperRecord).filter(ExamPaperRecord.id == paper_id).first()
        if not paper:
            raise HTTPException(status_code=404, detail="试卷不存在")
            
        question_ids = json.loads(paper.question_ids)
        
        # 批量获取题目，为了保持生成的顺序，我们使用代码进行排序
        questions = db.query(Question).filter(Question.id.in_(question_ids)).all()
        q_map = {q.id: crud._to_question_view(q) for q in questions}
        
        # 按照原来的 ID 顺序返回
        return [q_map[qid] for qid in question_ids if qid in q_map]
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/papers/{paper_id}")
async def delete_paper(paper_id: int, db: Session = Depends(get_db)):
    """删除某份试卷"""
    try:
        paper = db.query(ExamPaperRecord).filter(ExamPaperRecord.id == paper_id).first()
        if not paper:
            raise HTTPException(status_code=404, detail="试卷不存在")
        db.delete(paper)
        db.commit()
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
