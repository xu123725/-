from __future__ import annotations

import re


def _restore_latex_controls(text: str) -> str:
    control_map = {
        "\x08": r"\b",
        "\x0c": r"\f",
        "\x0b": r"\v",
        "\x07": r"\a",
    }
    for bad, fixed in control_map.items():
        text = text.replace(bad, fixed)
    return text


def normalize_markdown(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _restore_latex_controls(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def format_for_streamlit(text: str) -> str:
    return normalize_markdown(text)
