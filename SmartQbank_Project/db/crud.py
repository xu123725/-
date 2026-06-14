from __future__ import annotations

import json
import logging
import random
import sqlite3
import time
from datetime import datetime

import config
from core.schemas import ImportStats, QuestionCreate, QuestionView, WrongQuestionView

logger = logging.getLogger(__name__)


def _to_question_view(row: sqlite3.Row) -> QuestionView:
    return QuestionView(
        id=int(row["id"]),
        stem=row["stem"],
        options=json.loads(row["options_json"]) if row["options_json"] else [],
        answer=row["answer"],
        question_type=row["question_type"],
        category=row["category"],
        tag=row["tag"] or "",
        difficulty=int(row["difficulty"]),
        analysis=row["analysis"] or "",
        wrong_count=int(row["wrong_count"]) if "wrong_count" in row.keys() and row["wrong_count"] is not None else 0,
        last_wrong_at=row["last_wrong_at"] if "last_wrong_at" in row.keys() and row["last_wrong_at"] else "",
    )


def insert_questions_batch(
    conn: sqlite3.Connection,
    questions: list[QuestionCreate],
    chunk_size: int = 50,
    retry: int = 3,
) -> ImportStats:
    stats = ImportStats()
    if not questions:
        return stats
    for i in range(0, len(questions), max(1, chunk_size)):
        chunk = questions[i : i + max(1, chunk_size)]
        rows = [
            (
                q.stem,
                json.dumps(q.options, ensure_ascii=False),
                q.answer,
                q.question_type,
                q.category,
                q.tag,
                int(q.difficulty),
                q.source,
                q.hash_val,
            )
            for q in chunk
        ]
        for attempt in range(retry):
            try:
                conn.execute("BEGIN IMMEDIATE")
                cursor = conn.cursor()
                cursor.executemany(
                    """
                    INSERT OR IGNORE INTO questions(stem, options_json, answer, question_type, category, tag, difficulty, source, hash_val)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    rows,
                )
                inserted = cursor.rowcount
                stats.success += inserted
                stats.duplicate += (len(rows) - inserted)
                conn.commit()
                break
            except sqlite3.OperationalError as exc:
                conn.rollback()
                if "locked" in str(exc).lower() and attempt < retry - 1:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                logger.error(f"Database operational error during batch insert: {exc}")
                stats.failed += len(rows)
                break
            except Exception as exc:
                conn.rollback()
                logger.error(f"Unexpected error during batch insert: {exc}", exc_info=True)
                stats.failed += len(rows)
                break
    return stats


def fetch_question_for_analysis(conn: sqlite3.Connection, question_id: int) -> QuestionView | None:
    row = conn.execute(
        """
        SELECT id, stem, options_json, answer, question_type, category, tag, difficulty, analysis
        FROM questions
        WHERE id = ?
        """,
        (question_id,),
    ).fetchone()
    return _to_question_view(row) if row else None


def update_question_analysis(conn: sqlite3.Connection, question_id: int, analysis: str, retry: int = 3) -> None:
    for attempt in range(retry):
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("UPDATE questions SET analysis = ? WHERE id = ?", (analysis, question_id))
            conn.commit()
            return
        except sqlite3.OperationalError as exc:
            conn.rollback()
            if "locked" in str(exc).lower() and attempt < retry - 1:
                time.sleep(0.6 * (attempt + 1))
                continue
            raise


def fetch_categories(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("SELECT DISTINCT category FROM questions ORDER BY category").fetchall()
    return [row["category"] for row in rows if row["category"]]


def fetch_question_count_by_source(conn: sqlite3.Connection, source: str) -> int:
    row = conn.execute("SELECT COUNT(*) AS cnt FROM questions WHERE source = ?", (source,)).fetchone()
    return int(row["cnt"]) if row else 0


def sync_imported_files_from_questions(conn: sqlite3.Connection, upload_dir) -> None:
    rows = conn.execute(
        """
        SELECT source, COUNT(*) AS cnt
        FROM questions
        WHERE source IS NOT NULL AND source <> ''
        GROUP BY source
        """
    ).fetchall()
    for row in rows:
        source = row["source"]
        count = int(row["cnt"])
        path = upload_dir / source
        signature = f"{path.stat().st_size}:{path.stat().st_mtime_ns}" if path.exists() else "legacy"
        upsert_imported_file(conn, source, signature, count)
    conn.commit()


def upsert_imported_file(
    conn: sqlite3.Connection,
    file_name: str,
    file_signature: str,
    question_count: int,
    status: str = "done",
    stage: str = "done",
    error_code: str = "",
    last_error: str = "",
    cleanup_done: int = 0,
) -> None:
    conn.execute(
        """
        INSERT INTO imported_files(
            file_name, file_signature, question_count, status, stage, error_code, last_error, cleanup_done
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(file_name, file_signature)
        DO UPDATE SET
            question_count = excluded.question_count,
            status = excluded.status,
            stage = excluded.stage,
            error_code = excluded.error_code,
            last_error = excluded.last_error,
            cleanup_done = excluded.cleanup_done,
            imported_at = CURRENT_TIMESTAMP
        """,
        (file_name, file_signature, question_count, status, stage, error_code, last_error, int(cleanup_done)),
    )


def get_cached_import(conn: sqlite3.Connection, file_name: str, file_signature: str) -> tuple[str, int] | None:
    row = conn.execute(
        """
        SELECT file_name, question_count
        FROM imported_files
        WHERE file_name = ? AND file_signature = ? AND status = 'done'
        ORDER BY id DESC
        LIMIT 1
        """,
        (file_name, file_signature),
    ).fetchone()
    if not row:
        return None
    return row["file_name"], int(row["question_count"])


def has_recent_failed_import(
    conn: sqlite3.Connection,
    file_name: str,
    file_signature: str,
    cooldown_minutes: int = 30,
) -> bool:
    row = conn.execute(
        """
        SELECT 1
        FROM imported_files
        WHERE file_name = ?
          AND file_signature = ?
          AND status = 'failed'
          AND imported_at >= datetime('now', ?)
        LIMIT 1
        """,
        (file_name, file_signature, f"-{max(1, cooldown_minutes)} minutes"),
    ).fetchone()
    return row is not None


def fetch_import_health_snapshot(conn: sqlite3.Connection, lookback_hours: int = 24) -> dict[str, int]:
    window = f"-{max(1, lookback_hours)} hours"
    rows = conn.execute(
        """
        SELECT status, stage, cleanup_done, COUNT(*) AS cnt
        FROM imported_files
        WHERE imported_at >= datetime('now', ?)
        GROUP BY status, stage, cleanup_done
        """,
        (window,),
    ).fetchall()
    stats = {
        "total": 0,
        "done": 0,
        "failed": 0,
        "processing": 0,
        "cooldown_skip": 0,
        "cleanup_done": 0,
    }
    for row in rows:
        cnt = int(row["cnt"])
        status = (row["status"] or "").strip()
        stage = (row["stage"] or "").strip()
        stats["total"] += cnt
        if status == "done":
            stats["done"] += cnt
        if status == "failed":
            stats["failed"] += cnt
        if status == "processing":
            stats["processing"] += cnt
        if stage == "cooldown":
            stats["cooldown_skip"] += cnt
        if int(row["cleanup_done"] or 0) == 1:
            stats["cleanup_done"] += cnt
    return stats


def add_wrong_question(conn: sqlite3.Connection, question_id: int) -> None:
    conn.execute(
        """
        INSERT INTO wrong_questions(question_id, wrong_count, last_wrong_at, is_archived)
        VALUES (?, 1, CURRENT_TIMESTAMP, 0)
        ON CONFLICT(question_id) DO UPDATE SET
            wrong_count = wrong_count + 1,
            last_wrong_at = CURRENT_TIMESTAMP,
            is_archived = 0
        """,
        (question_id,),
    )
    conn.commit()


def remove_wrong_question(conn: sqlite3.Connection, question_id: int) -> None:
    conn.execute("UPDATE wrong_questions SET is_archived = 1 WHERE question_id = ?", (question_id,))
    conn.commit()


def count_wrong_questions(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) AS cnt FROM wrong_questions WHERE is_archived = 0").fetchone()
    return int(row["cnt"]) if row else 0


def is_in_wrong_book(conn: sqlite3.Connection, question_id: int) -> bool:
    row = conn.execute(
        "SELECT 1 FROM wrong_questions WHERE question_id = ? AND is_archived = 0 LIMIT 1",
        (question_id,),
    ).fetchone()
    return row is not None


def list_wrong_questions(conn: sqlite3.Connection, limit: int = 100, order_by: str = "recent") -> list[WrongQuestionView]:
    order_clause = "w.last_wrong_at DESC" if order_by == "recent" else "w.wrong_count DESC, w.last_wrong_at DESC"
    rows = conn.execute(
        f"""
        SELECT
            q.id,
            q.stem,
            q.options_json,
            q.answer,
            q.question_type,
            q.category,
            q.tag,
            q.difficulty,
            q.analysis,
            w.wrong_count,
            w.last_wrong_at
        FROM wrong_questions w
        JOIN questions q ON q.id = w.question_id
        WHERE w.is_archived = 0
        ORDER BY {order_clause}
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [WrongQuestionView(**_to_question_view(row).model_dump()) for row in rows]


def insert_user_log(conn: sqlite3.Connection, question_id: int, is_correct: bool) -> None:
    conn.execute(
        "INSERT INTO user_logs(question_id, is_correct, ts) VALUES (?, ?, ?)",
        (question_id, 1 if is_correct else 0, datetime.utcnow().isoformat(timespec="seconds")),
    )
    conn.commit()


def update_questions_last_used(conn: sqlite3.Connection, question_ids: list[int]) -> None:
    now = datetime.utcnow().isoformat(timespec="seconds")
    conn.executemany("UPDATE questions SET last_used_at = ? WHERE id = ?", [(now, qid) for qid in question_ids])
    conn.commit()


def fetch_candidate_questions(
    conn: sqlite3.Connection,
    categories: list[str],
    recent_hours: int,
    question_type: str = "all",
) -> list[QuestionView]:
    params: list = []
    where_clauses = [
        "id NOT IN (SELECT question_id FROM user_logs WHERE is_correct = 1)",
    ]
    if question_type in {"single", "fill_blank"}:
        where_clauses.insert(0, "question_type = ?")
        params.append(question_type)
    if categories:
        placeholders = ",".join(["?"] * len(categories))
        where_clauses.append(f"category IN ({placeholders})")
        params.extend(categories)
    if recent_hours > 0:
        threshold = datetime.utcnow().timestamp() - recent_hours * 3600
        threshold_text = datetime.utcfromtimestamp(threshold).isoformat(timespec="seconds")
        where_clauses.append("(last_used_at IS NULL OR last_used_at < ?)")
        params.append(threshold_text)
    rows = conn.execute(
        f"""
        SELECT id, stem, options_json, answer, question_type, category, tag, difficulty, analysis
        FROM questions
        WHERE {' AND '.join(where_clauses)}
        LIMIT 5000
        """,
        tuple(params),
    ).fetchall()
    return [_to_question_view(row) for row in rows]


def fetch_exam_questions(
    conn: sqlite3.Connection,
    limit: int,
    question_type: str,
    categories: list[str],
    prefer_wrong: bool = False,
    prefer_unanswered: bool = False,
    exclude_ids: list[int] | None = None,
) -> list[QuestionView]:
    if limit <= 0:
        return []
    params: list = [question_type]
    where_clauses = ["q.question_type = ?"]
    if categories:
        placeholders = ",".join(["?"] * len(categories))
        where_clauses.append(f"q.category IN ({placeholders})")
        params.extend(categories)
    if exclude_ids:
        placeholders = ",".join(["?"] * len(exclude_ids))
        where_clauses.append(f"q.id NOT IN ({placeholders})")
        params.extend(exclude_ids)
    if prefer_wrong and prefer_unanswered:
        priority_sql = (
            "CASE "
            "WHEN EXISTS(SELECT 1 FROM wrong_questions w WHERE w.question_id = q.id AND w.is_archived = 0) THEN 1 "
            "WHEN NOT EXISTS(SELECT 1 FROM user_logs ul WHERE ul.question_id = q.id) THEN 2 "
            "ELSE 3 END"
        )
    elif prefer_wrong:
        priority_sql = (
            "CASE "
            "WHEN EXISTS(SELECT 1 FROM wrong_questions w WHERE w.question_id = q.id AND w.is_archived = 0) THEN 1 "
            "ELSE 2 END"
        )
    elif prefer_unanswered:
        priority_sql = (
            "CASE "
            "WHEN NOT EXISTS(SELECT 1 FROM user_logs ul WHERE ul.question_id = q.id) THEN 1 "
            "ELSE 2 END"
        )
    else:
        priority_sql = "1"
    fast_mode = config.FAST_RANDOM_QUERY_MODE in {"on", "true", "1"}
    if not fast_mode:
        sql = f"""
            SELECT
                q.id, q.stem, q.options_json, q.answer, q.question_type, q.category, q.tag, q.difficulty, q.analysis,
                {priority_sql} AS priority_level
            FROM questions q
            WHERE {' AND '.join(where_clauses)}
            ORDER BY priority_level ASC, RANDOM()
            LIMIT ?
        """
        params_with_limit = [*params, limit]
        rows = conn.execute(sql, tuple(params_with_limit)).fetchall()
        return [_to_question_view(row) for row in rows]

    id_pool_limit = min(5000, max(limit * 20, 500))
    id_sql = f"""
        SELECT q.id, {priority_sql} AS priority_level
        FROM questions q
        WHERE {' AND '.join(where_clauses)}
        ORDER BY priority_level ASC, q.id DESC
        LIMIT ?
    """
    id_rows = conn.execute(id_sql, tuple([*params, id_pool_limit])).fetchall()
    if not id_rows:
        return []
    candidates = [(int(r["id"]), int(r["priority_level"])) for r in id_rows]
    random.shuffle(candidates)
    candidates.sort(key=lambda x: x[1])
    selected_ids = [qid for qid, _ in candidates[:limit]]
    if not selected_ids:
        return []
    placeholders = ",".join(["?"] * len(selected_ids))
    detail_rows = conn.execute(
        f"""
        SELECT id, stem, options_json, answer, question_type, category, tag, difficulty, analysis
        FROM questions
        WHERE id IN ({placeholders})
        """,
        tuple(selected_ids),
    ).fetchall()
    row_map = {int(r["id"]): r for r in detail_rows}
    ordered_rows = [row_map[qid] for qid in selected_ids if qid in row_map]
    return [_to_question_view(row) for row in ordered_rows]


def get_total_question_count(conn: sqlite3.Connection) -> int:
    """获取总题目数"""
    row = conn.execute("SELECT COUNT(*) AS cnt FROM questions").fetchone()
    return int(row["cnt"]) if row else 0


def get_average_accuracy(conn: sqlite3.Connection) -> float:
    """获取平均正确率 (百分比)"""
    row = conn.execute("SELECT AVG(is_correct) * 100 AS avg_acc FROM user_logs").fetchone()
    return float(row["avg_acc"]) if row and row["avg_acc"] is not None else 0.0


def get_pending_wrong_question_count(conn: sqlite3.Connection) -> int:
    """获取待处理错题数"""
    row = conn.execute("SELECT COUNT(*) AS cnt FROM wrong_questions WHERE is_archived = 0").fetchone()
    return int(row["cnt"]) if row else 0
