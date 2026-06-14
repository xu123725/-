import json
import logging
import sys
import uuid
from pathlib import Path
from typing import Any


def create_trace_id() -> str:
    return uuid.uuid4().hex[:16]


def log_event(logger: logging.Logger, level: int, event: str, **fields: Any) -> None:
    payload = {"event": event, **fields}
    logger.log(level, json.dumps(payload, ensure_ascii=False, default=str))


def setup_logging(log_file_path: Path):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    if logger.hasHandlers():
        logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    if log_file_path:
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_file_path, encoding="utf-8")
        fh.setFormatter(formatter)
        logger.addHandler(fh)
