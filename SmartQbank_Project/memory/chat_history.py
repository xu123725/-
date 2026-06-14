from __future__ import annotations

import sqlite3

from db.crud import insert_user_log


def log_answer_result(conn: sqlite3.Connection, question_id: int, is_correct: bool) -> None:
    insert_user_log(conn, question_id, is_correct)
