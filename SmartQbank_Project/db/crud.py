from __future__ import annotations

import json
import logging
import random
import time
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, text, distinct

import config
from core.schemas import ImportStats, QuestionCreate, QuestionView, WrongQuestionView
from db.models import Question, UserLog, WrongQuestion, ImportedFile, KnowledgeBase

logger = logging.getLogger(__name__)

def _to_question_view(row: Question) -> QuestionView:
    return QuestionView(
        id=int(row.id),
        stem=row.stem,
        options=json.loads(row.options_json) if row.options_json else [],
        answer=row.answer,
        question_type=row.question_type,
        category=row.category,
        tag=row.tag or "",
        difficulty=int(row.difficulty),
        analysis=row.analysis or "",
        wrong_count=0, # 联表查询时覆盖
        last_wrong_at="", # 联表查询时覆盖
    )

def fetch_categories(db: Session) -> list[str]:
    categories = db.query(distinct(Question.category)).order_by(Question.category).all()
    return [c[0] for c in categories if c[0]]

def get_total_question_count(db: Session) -> int:
    return db.query(func.count(Question.id)).scalar() or 0

def get_average_accuracy(db: Session) -> float:
    avg_acc = db.query(func.avg(UserLog.is_correct) * 100).scalar()
    return float(avg_acc) if avg_acc is not None else 0.0

def get_pending_wrong_question_count(db: Session) -> int:
    return db.query(func.count(WrongQuestion.id)).filter(WrongQuestion.is_archived == 0).scalar() or 0

def fetch_import_health_snapshot(db: Session, lookback_hours: int = 24) -> dict[str, int]:
    # 为了兼容 SQLite 和 SQL Server 跨库的时间查询语法，暂时直接取出内存计算
    files = db.query(ImportedFile).all()
    stats = {
        "total": 0, "done": 0, "failed": 0, "processing": 0,
        "cooldown_skip": 0, "cleanup_done": 0,
    }
    for f in files:
        stats["total"] += 1
        if f.status == "done":
            stats["done"] += 1
        if f.status == "failed":
            stats["failed"] += 1
        if f.status == "processing":
            stats["processing"] += 1
        if f.stage == "cooldown":
            stats["cooldown_skip"] += 1
        if f.cleanup_done == 1:
            stats["cleanup_done"] += 1
    return stats

def insert_user_log(db: Session, question_id: int, is_correct: bool) -> None:
    new_log = UserLog(
        question_id=question_id,
        is_correct=1 if is_correct else 0,
        ts=datetime.utcnow()
    )
    db.add(new_log)

def add_wrong_question(db: Session, question_id: int) -> None:
    wq = db.query(WrongQuestion).filter(WrongQuestion.question_id == question_id).first()
    if wq:
        wq.wrong_count += 1
        wq.last_wrong_at = datetime.utcnow()
        wq.is_archived = 0
    else:
        new_wq = WrongQuestion(
            question_id=question_id,
            wrong_count=1,
            last_wrong_at=datetime.utcnow(),
            is_archived=0
        )
        db.add(new_wq)

def retrieve_knowledge(db: Session, query: str, limit: int = 3) -> list[dict]:
    # 由于全文检索 (FTS) 与特定数据库绑定较深（SQLite FTS5, SQL Server CONTAINS）
    # 为了兼容性，我们这里使用简单的 LIKE 查询
    # 在生产中建议接入 ElasticSearch 或向量数据库
    results = db.query(KnowledgeBase).filter(
        KnowledgeBase.content.like(f"%{query}%") | KnowledgeBase.title.like(f"%{query}%")
    ).limit(limit).all()
    
    return [
        {
            "id": r.id,
            "title": r.title,
            "content": r.content,
            "source": r.source or "知识库",
        }
        for r in results
    ]

def remove_wrong_question(db: Session, question_id: int) -> None:
    wq = db.query(WrongQuestion).filter(WrongQuestion.question_id == question_id).first()
    if wq:
        wq.is_archived = 1
        db.commit()

def list_wrong_questions(db: Session, limit: int = 100, order_by: str = "recent") -> list[WrongQuestionView]:
    query = db.query(WrongQuestion, Question).join(Question, Question.id == WrongQuestion.question_id).filter(WrongQuestion.is_archived == 0)
    
    if order_by == "recent":
        query = query.order_by(WrongQuestion.last_wrong_at.desc())
    else:
        query = query.order_by(WrongQuestion.wrong_count.desc(), WrongQuestion.last_wrong_at.desc())
        
    results = query.limit(limit).all()
    views = []
    for wq, q in results:
        v = _to_question_view(q)
        v.wrong_count = wq.wrong_count
        v.last_wrong_at = wq.last_wrong_at.isoformat() if wq.last_wrong_at else ""
        views.append(WrongQuestionView(**v.model_dump()))
    return views

def fetch_exam_questions(
    conn: Session,
    limit: int,
    question_type: str,
    categories: list[str],
    prefer_wrong: bool = False,
    prefer_unanswered: bool = False,
    exclude_ids: list[int] | None = None,
) -> list[QuestionView]:
    query = conn.query(Question)
    if question_type != "all":
        query = query.filter(Question.question_type == question_type)
    if categories:
        query = query.filter(Question.category.in_(categories))
    if exclude_ids:
        query = query.filter(~Question.id.in_(exclude_ids))
        
    # 为了简化跨库兼容性，先取出随机 limit 的数据
    if conn.bind.dialect.name == "mssql":
        query = query.order_by(text("NEWID()"))
    else:
        query = query.order_by(func.random())
        
    results = query.limit(limit).all()
    return [_to_question_view(row) for row in results]
