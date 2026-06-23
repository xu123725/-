from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
import os
import shutil
import logging

from db.database import get_db, SessionLocal
from db import crud
from core.schemas import QuestionView

router = APIRouter()
logger = logging.getLogger(__name__)

class PaginatedQuestions(BaseModel):
    items: List[QuestionView]
    total: int
    page: int
    size: int

class QueryParams(BaseModel):
    page: int = 1
    size: int = 50
    category: Optional[str] = None
    question_type: Optional[str] = None

class ExamLogSubmit(BaseModel):
    question_id: int
    is_correct: bool

def async_log_user_answer(question_id: int, is_correct: bool):
    """
    后台任务：异步写入做题日志与错题本。
    使用独立的新 Session，缓解并发写锁。
    """
    retry = 3
    import time
    
    for attempt in range(retry):
        try:
            # 开启独立连接，避免和当前请求阻塞
            with SessionLocal() as db:
                # 记录答题日志
                crud.insert_user_log(db, question_id, is_correct)
                
                # 如果答错，加入错题本
                if not is_correct:
                    crud.add_wrong_question(db, question_id)
                db.commit()
            break
        except Exception as exc:
            if "locked" in str(exc).lower() and attempt < retry - 1:
                time.sleep(0.5 * (attempt + 1))
                continue
            logger.error(f"Unexpected error in async write user log: {exc}")
            break

@router.post("/log_answer")
async def submit_answer_log(log: ExamLogSubmit, background_tasks: BackgroundTasks):
    """
    提交做题记录（支持并发削峰）
    该接口立即返回成功，实际的 SQLite 写入操作交由 FastAPI BackgroundTasks 处理。
    """
    background_tasks.add_task(async_log_user_answer, log.question_id, log.is_correct)
    return {"status": "accepted", "message": "Log submission accepted for background processing"}

@router.get("/categories", response_model=List[str])
async def get_categories(db: Session = Depends(get_db)):
    """获取所有题目分类"""
    try:
        return crud.fetch_categories(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/list", response_model=PaginatedQuestions)
async def get_questions(params: QueryParams, db: Session = Depends(get_db)):
    """获取题库列表 (支持分页与条件过滤)"""
    import traceback
    from db.models import Question
    try:
        query = db.query(Question)
        if params.category:
            query = query.filter(Question.category == params.category)
        if params.question_type:
            query = query.filter(Question.question_type == params.question_type)
            
        total = query.count()
        offset = (params.page - 1) * params.size
        
        rows = query.order_by(Question.id.desc()).offset(offset).limit(params.size).all()
        items = [crud._to_question_view(row) for row in rows]
        
        return PaginatedQuestions(
            items=items,
            total=total,
            page=params.page,
            size=params.size
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{question_id}/analysis")
async def get_question_analysis(question_id: int, db: Session = Depends(get_db)):
    """获取题目解析（如果为空则使用大模型实时生成并回写数据库）"""
    import config
    from core.processor import get_or_generate_analysis
    from core.llm_client import LLMClient
    
    try:
        client = LLMClient(
            api_key=config.get_api_key(),
            base_url=config.get_api_base_url(),
            model=config.get_api_model(),
            timeout=config.IMPORT_LLM_TIMEOUT,
        )
        analysis = get_or_generate_analysis(db, client, question_id)
        return {"status": "success", "analysis": analysis}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{question_id}")
async def delete_question(question_id: int, db: Session = Depends(get_db)):
    """删除单道题目"""
    import traceback
    from db.models import Question
    try:
        question = db.query(Question).filter(Question.id == question_id).first()
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")
        db.delete(question)
        db.commit()
        return {"status": "success", "message": f"Deleted question {question_id}"}
    except Exception as e:
        db.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """上传题库文档 (DOCX) 到 uploads 目录"""
    from config import UPLOAD_DIR
    import traceback
    try:
        if not file.filename.endswith(".docx"):
            raise HTTPException(status_code=400, detail="Only .docx files are supported")
            
        file_path = UPLOAD_DIR / file.filename
        
        # 保存文件
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        return {
            "status": "success", 
            "message": "File uploaded successfully",
            "filename": file.filename,
            "path": str(file_path)
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
