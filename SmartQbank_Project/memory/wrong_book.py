from __future__ import annotations

import sqlite3
from typing import Any

from db.crud import (
    add_wrong_question as dal_add_wrong_question,
    count_wrong_questions as dal_count_wrong_questions,
    list_wrong_questions as dal_list_wrong_questions,
    remove_wrong_question as dal_remove_wrong_question,
)


def add_wrong_question(conn: sqlite3.Connection, question_id: int) -> None:
    dal_add_wrong_question(conn, question_id)


def remove_wrong_question(conn: sqlite3.Connection, question_id: int) -> None:
    dal_remove_wrong_question(conn, question_id)


def get_wrong_questions(
    conn: sqlite3.Connection,
    limit: int = 100,
    order_by: str = "recent",
) -> list[dict[str, Any]]:
    return [item.model_dump() for item in dal_list_wrong_questions(conn, limit=limit, order_by=order_by)]


def count_wrong_questions(conn: sqlite3.Connection) -> int:
    return dal_count_wrong_questions(conn)
