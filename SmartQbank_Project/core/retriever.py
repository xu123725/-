from __future__ import annotations

import random
import sqlite3
from collections import defaultdict
from typing import Any

from db.crud import fetch_candidate_questions, fetch_exam_questions, update_questions_last_used
from .schemas import QuestionView

def _stratified_sample(candidates: list[QuestionView], needed: int) -> list[QuestionView]:
    if needed <= 0 or not candidates:
        return []
    tag_map: dict[str, list[QuestionView]] = defaultdict(list)
    for row in candidates:
        tag_map[(row.tag or "未分类").strip()].append(row)
    tags = list(tag_map.keys())
    random.shuffle(tags)
    for rows in tag_map.values():
        random.shuffle(rows)
    selected: list[QuestionView] = []
    while len(selected) < needed:
        progressed = False
        for tag in tags:
            if tag_map[tag]:
                selected.append(tag_map[tag].pop())
                progressed = True
                if len(selected) >= needed:
                    break
        if not progressed:
            break
    return selected


def mark_questions_used(conn: sqlite3.Connection, question_ids: list[int]) -> None:
    update_questions_last_used(conn, question_ids)


def retrieve_questions(
    conn: sqlite3.Connection,
    total_count: int,
    categories: list[str],
    recent_hours: int = 24,
    question_type: str = "all",
) -> list[dict[str, Any]]:
    rows = fetch_candidate_questions(
        conn,
        categories=categories,
        recent_hours=recent_hours,
        question_type=question_type,
    )
    selected_rows = _stratified_sample(rows, total_count)
    if len(selected_rows) < total_count:
        used_ids = {r.id for r in selected_rows}
        remain = [r for r in rows if r.id not in used_ids]
        random.shuffle(remain)
        selected_rows.extend(remain[: total_count - len(selected_rows)])
    questions = [row.model_dump() for row in selected_rows[:total_count]]
    if questions:
        mark_questions_used(conn, [q["id"] for q in questions])
    return questions


def retrieve_exam_questions(
    conn: sqlite3.Connection,
    limit: int,
    question_type: str,
    categories: list[str],
    prefer_wrong: bool = False,
    prefer_unanswered: bool = False,
    exclude_ids: list[int] | None = None,
) -> list[dict[str, Any]]:
    rows = fetch_exam_questions(
        conn=conn,
        limit=limit,
        question_type=question_type,
        categories=categories,
        prefer_wrong=prefer_wrong,
        prefer_unanswered=prefer_unanswered,
        exclude_ids=exclude_ids,
    )
    return [row.model_dump() for row in rows]

def retrieve_knowledge(
    conn: sqlite3.Connection,
    query: str,
    limit: int = 5,
    category: str | None = None
) -> list[dict[str, Any]]:
    """
    检索知识库中的相关片段。
    """
    if not query:
        return []
        
    try:
        # 尝试使用 FTS5 检索
        sql = """
            SELECT kb.id, kb.title, kb.content, kb.category, kb.source 
            FROM knowledge_fts fts
            JOIN knowledge_base kb ON fts.rowid = kb.id
            WHERE knowledge_fts MATCH ?
        """
        # 转义 FTS5 的双引号，避免查询字符串中有破坏语法的字符
        escaped_query = '"' + query.replace('"', '""') + '"'
        params = [escaped_query]
        if category:
            sql += " AND kb.category = ?"
            params.append(category)
        sql += " LIMIT ?"
        params.append(limit)
        
        rows = conn.execute(sql, params).fetchall()
        if rows:
            return [dict(r) for r in rows]
    except:
        # 回退到普通模糊检索
        pass
        
    # 普通模糊检索
    sql = "SELECT id, title, content, category, source FROM knowledge_base WHERE content LIKE ?"
    params = [f"%{query}%"]
    if category:
        sql += " AND category = ?"
        params.append(category)
    sql += " LIMIT ?"
    params.append(limit)
    
    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]
