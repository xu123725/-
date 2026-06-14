from __future__ import annotations

import json
import logging
import math
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from hashlib import md5
from typing import Any, Callable

from pydantic import BaseModel, Field, ValidationError

from config import (
    IMPORT_MAX_OUTPUT_TOKENS,
    MAX_CHUNK_TOKENS,
    MAX_CLASSIFY_RETRIES,
    MAX_CLASSIFY_WORKERS,
)
from .llm_client import LLMClient

logger = logging.getLogger(__name__)


class QuestionItem(BaseModel):
    stem: str = Field(min_length=2)
    options: list[str] = Field(default_factory=list)
    answer: str = ""
    question_type: str = "single"
    category: str = Field(min_length=1)
    difficulty: int = Field(default=3, ge=1, le=5)
    tag: str | list[str] = ""


@dataclass
class ChunkTask:
    chunk_id: int
    text: str
    est_tokens: int


@dataclass
class ChunkResult:
    chunk_id: int
    questions: list[dict[str, Any]]
    success: bool
    retries: int = 0
    error: str = ""


@dataclass(frozen=True)
class SubjectRule:
    category: str
    subcategory: str
    topic: str
    keywords_strong: tuple[str, ...]
    keywords_weak: tuple[str, ...]


MAJOR_CATEGORIES = [
    "03天气雷达",
    "05综合观测基础知识",
    "06观测自动化及技术规定",
    "07观测新平台和新装备",
    "08数据格式及质量控制",
    "09质量管理体系",
    "10探测环境保护",
    "11法律法规及规章制度",
    "自动气象站维护与维修",
]


SUBJECT_RULES: list[SubjectRule] = [
    SubjectRule("03天气雷达", "", "", ("天气雷达", "新一代天气雷达", "多普勒", "雷达回波", "x波段", "s波段", "c波段"), ("体扫", "径向速度", "反射率", "雷达标校", "雷达维护")),
    SubjectRule("05综合观测基础知识", "", "", ("综合观测", "观测基础", "观测要素", "气温", "气压", "湿度", "风向", "风速", "降水"), ("人工观测", "自动观测", "云量", "云高", "能见度")),
    SubjectRule("06观测自动化及技术规定", "", "", ("自动站", "自动观测系统", "技术规定", "业务规范", "观测规范", "台站业务"), ("采集", "传输", "数据上报", "运行维护")),
    SubjectRule("07观测新平台和新装备", "", "", ("北斗探空", "l波段探空", "风廓线雷达", "微波辐射计", "gps/met", "新装备", "新平台"), ("探空仪", "遥感", "垂直观测", "设备升级")),
    SubjectRule("08数据格式及质量控制", "", "", ("数据格式", "报文", "编码", "质量控制", "质控", "一致性", "可疑值"), ("数据处理", "数据校验", "质量评估", "元数据")),
    SubjectRule("09质量管理体系", "", "", ("质量管理体系", "质量考核", "质量评估", "业务事故", "事故调查", "事故分级"), ("考核", "整改", "闭环", "持续改进")),
    SubjectRule("10探测环境保护", "", "", ("探测环境", "环境保护", "保护范围", "防雷", "电磁干扰", "台站迁建"), ("屏蔽", "接地", "选址", "评估", "验收")),
    SubjectRule("11法律法规及规章制度", "", "", ("法律法规", "规章制度", "条例", "办法", "标准", "规范性文件", "无线电管理"), ("依法", "合规", "监管", "行政")),
    SubjectRule("自动气象站维护与维修", "", "", ("维护", "维修", "保障", "备件", "传感器更换", "采集器维修", "供电维护", "通信维修"), ("自动站维护", "设备维修", "故障排除")),
]


def estimate_tokens(text: str) -> int:
    return max(1, math.ceil(len(text) / 1.6))


def _is_question_start(line: str) -> bool:
    text = line.strip()
    if not text:
        return False
    return bool(re.match(r"^(?:\d+\s*[、\.\)）]|[A-Ha-h](?:\.|、|\)|）))", text))


def _split_question_blocks(text: str) -> list[str]:
    blocks: list[str] = []
    current: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if _is_question_start(line) and current:
            blocks.append("\n".join(current).strip())
            current = [line]
        else:
            current.append(line)
    if current:
        blocks.append("\n".join(current).strip())
    return [b for b in blocks if b]


def _build_question_text(question: dict[str, Any]) -> str:
    parts: list[str] = [question.get("stem", "")]
    parts.extend(question.get("options", []) or [])
    parts.append(question.get("answer", ""))
    return " ".join([p for p in parts if p]).lower()


def _match_subject(text: str) -> tuple[str, int] | None:
    hits: list[tuple[int, int, int, SubjectRule]] = []
    for idx, rule in enumerate(SUBJECT_RULES):
        strong_count = sum(1 for kw in rule.keywords_strong if kw and kw in text)
        weak_count = sum(1 for kw in rule.keywords_weak if kw and kw in text)
        score = strong_count * 4 + weak_count
        if score <= 0:
            continue
        hits.append((score, strong_count, idx, rule))
    if not hits:
        return None
    hits.sort(key=lambda x: (-x[0], -x[1], x[2]))
    best = hits[0]
    return best[3].category, best[0]


def _fallback_category(text: str) -> str:
    matched = _match_subject(text)
    if matched:
        return matched[0]
    return "05综合观测基础知识"


def apply_subject_classification(questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for q in questions:
        text = _build_question_text(q)
        matched = _match_subject(text)
        if matched:
            q["category"] = matched[0]
        else:
            raw = f"{q.get('category', '')} {q.get('tag', '')}".lower().strip()
            q["category"] = _fallback_category(raw)
        q["tag"] = q.get("tag", "").strip()
    return questions


def _split_oversized_block(block: str, max_tokens: int) -> list[str]:
    paragraphs = [p.strip() for p in block.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [line.strip() for line in block.splitlines() if line.strip()]
    if not paragraphs:
        return []
    parts: list[str] = []
    current: list[str] = []
    current_tokens = 0
    for part in paragraphs:
        tokens = estimate_tokens(part)
        if current and current_tokens + tokens > max_tokens:
            parts.append("\n\n".join(current))
            current = [part]
            current_tokens = tokens
        else:
            current.append(part)
            current_tokens += tokens
    if current:
        parts.append("\n\n".join(current))
    return [p for p in parts if p]


def build_chunk_tasks(long_text: str, max_tokens: int = MAX_CHUNK_TOKENS) -> list[ChunkTask]:
    clean_text = long_text.strip()
    if not clean_text:
        return []
    blocks = _split_question_blocks(clean_text)
    if len(blocks) <= 1:
        blocks = _split_oversized_block(clean_text, max_tokens)
    normalized_blocks: list[str] = []
    for block in blocks:
        if estimate_tokens(block) > max_tokens:
            normalized_blocks.extend(_split_oversized_block(block, max_tokens))
        else:
            normalized_blocks.append(block)
    tasks: list[ChunkTask] = []
    buf: list[str] = []
    buf_tokens = 0
    chunk_id = 1
    for block in normalized_blocks:
        block_tokens = estimate_tokens(block)
        if buf and buf_tokens + block_tokens > max_tokens:
            text = "\n\n".join(buf).strip()
            tasks.append(ChunkTask(chunk_id=chunk_id, text=text, est_tokens=estimate_tokens(text)))
            chunk_id += 1
            buf = [block]
            buf_tokens = block_tokens
        else:
            buf.append(block)
            buf_tokens += block_tokens
    if buf:
        text = "\n\n".join(buf).strip()
        tasks.append(ChunkTask(chunk_id=chunk_id, text=text, est_tokens=estimate_tokens(text)))
    return tasks


def normalize_stem_for_hash(stem: str) -> str:
    text = stem.lower()
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"[，。、“”‘’；：！？,.\"'`~!@#$%^&*()_+\-=\[\]{}|\\/:;<>?]", "", text)
    return text


def stem_hash(stem: str) -> str:
    return md5(normalize_stem_for_hash(stem).encode("utf-8")).hexdigest()


def _parse_json_content(raw: str) -> Any:
    # Attempt to extract JSON from markdown code blocks
    match = re.search(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL)
    content = match.group(1) if match else raw
    try:
        return json.loads(content.strip())
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 解析错误: {e}") from e


def _extract_options_from_stem(stem: str) -> tuple[str, list[str]]:
    lines = [line.strip() for line in (stem or "").splitlines() if line.strip()]
    if not lines:
        return stem, []
    options: list[str] = []
    stem_lines: list[str] = []
    option_started = False
    for line in lines:
        matched = re.match(r"^[A-Ha-h][\.|、|\)|）]\s*(.+)$", line)
        if matched:
            option_started = True
            options.append(matched.group(1).strip())
            continue
        if option_started:
            if options:
                options[-1] = f"{options[-1]} {line}".strip()
        else:
            stem_lines.append(line)
    if len(options) >= 2:
        clean_stem = "\n".join(stem_lines).strip() or stem
        return clean_stem, options
    return stem, []


def _validate_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        payload = {"questions": payload}
    if not isinstance(payload, dict):
        return []
    raw_questions = payload.get("questions", [])
    if not isinstance(raw_questions, list):
        return []
    normalized: list[dict[str, Any]] = []
    for raw_item in raw_questions:
        try:
            item = QuestionItem.model_validate(raw_item)
        except ValidationError as exc:
            logger.warning(f"Validation error for question item: {exc.errors()} - Raw: {raw_item}")
            continue
        stem = item.stem.strip()
        options = [opt.strip() for opt in item.options if opt.strip()]
        if not options:
            stem, parsed_options = _extract_options_from_stem(stem)
            options = parsed_options
        answer = item.answer.strip()
        inferred_type = "fill_blank" if not options else "single"
        requested_type = (item.question_type or "").strip().lower()
        if requested_type in {"single", "fill_blank", "true_false"}:
            question_type = requested_type
        else:
            question_type = inferred_type
            
        # 进一步校验判断题逻辑：如果选项是 [正确, 错误] 或 [对, 错] 等
        if question_type == "single" and len(options) == 2:
            opt_str = "".join(options)
            if any(k in opt_str for k in ["正确", "错误", "对", "错", "是", "否"]):
                question_type = "true_false"

        if question_type == "single" and not options:
            question_type = "fill_blank"
        if question_type == "single" and len(options) < 2:
            continue
        if not answer:
            continue
        tag = item.tag if isinstance(item.tag, str) else " / ".join([str(t).strip() for t in item.tag if str(t).strip()])
        normalized.append(
            {
                "stem": stem,
                "options": options,
                "answer": answer,
                "question_type": question_type,
                "category": item.category.strip(),
                "difficulty": 3,
                "tag": tag.strip(),
            }
        )
    return normalized


def _self_correct_json(client: LLMClient, broken_content: str, error_text: str) -> str:
    prompt = (
        "你是一个JSON修复器。只输出合法 JSON，不要包含任何解释文字。"
        "目标结构为 {\"questions\":[{\"stem\":\"\",\"options\":[],\"answer\":\"\",\"question_type\":\"single\",\"category\":\"\",\"tag\":\"\"}]}"
        "。category 只能使用以下8类之一：03天气雷达、05综合观测基础知识、06观测自动化及技术规定、07观测新平台和新装备、08数据格式及质量控制、09质量管理体系、10探测环境保护、11法律法规及规章制度。"
        "若内容不完全匹配，归入你认为最相近的大类。"
        f"。\n错误信息：{error_text}\n待修复内容：\n{broken_content}"
    )
    return client.chat_completion(
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.0,
    )


def parse_questions_json(raw_content: str, client: LLMClient) -> list[dict[str, Any]]:
    raw = raw_content
    for _ in range(2):
        try:
            payload = _parse_json_content(raw)
            return _validate_payload(payload)
        except (ValueError, ValidationError) as exc:
            raw = _self_correct_json(client, raw, str(exc))
    return []


def _extract_questions_from_chunk(
    client: LLMClient,
    chunk_text: str,
    max_output_tokens: int = IMPORT_MAX_OUTPUT_TOKENS,
    fixed_category: str | None = None,
) -> list[dict[str, Any]]:
    if fixed_category:
        system_prompt = (
            "你是题库结构化助手。请从文本中识别题目并输出 JSON。"
            "必须输出合法 JSON 对象，键名仅使用 questions。"
            "questions 中每项包含 stem, options, answer, question_type, category, tag。"
            f"重要：所有题目类别均为 '{fixed_category}'，你不需要进行任何学科分类，只需专注于提取题目内容（题干、选项、答案、题型）。"
            "题型规则："
            "1. 如 options 为空，question_type 必须为 fill_blank。"
            "2. 如 options 为 [正确, 错误]、[对, 错] 等，question_type 必须为 true_false。"
            "3. 如 options 为多项选择，question_type 必须为 single。"
            "如果遇到无法直接解析的公式，请改写为标准 LaTeX，并使用 $...$ 包裹。"
            "不得输出额外说明文字。"
        )
    else:
        system_prompt = (
            "你是题库结构化助手。请从文本中识别题目并输出 JSON。"
            "必须输出合法 JSON 对象，键名仅使用 questions。"
            "questions 中每项包含 stem, options, answer, question_type, category, tag。"
            f"category 只能使用以下{len(MAJOR_CATEGORIES)}类之一：{', '.join(MAJOR_CATEGORIES)}。"
            "若无法完全判断，请归入你认为最相近的大类。"
            "题型规则："
            "1. 如 options 为空，question_type 必须为 fill_blank。"
            "2. 如 options 为 [正确, 错误]、[对, 错] 等，question_type 必须为 true_false。"
            "3. 如 options 为多项选择，question_type 必须为 single。"
            "如果遇到无法直接解析的公式，请改写为标准 LaTeX，并使用 $...$ 包裹。"
            "不得输出额外说明文字。"
        )
    user_prompt = f"请结构化以下文本：\n{chunk_text}"
    raw = client.chat_completion(
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        response_format={"type": "json_object"},
        max_tokens=max_output_tokens,
    )
    return parse_questions_json(raw, client)


def _run_chunk_with_retry(
    client: LLMClient,
    task: ChunkTask,
    retries: int,
    max_output_tokens: int = IMPORT_MAX_OUTPUT_TOKENS,
    fixed_category: str | None = None,
) -> ChunkResult:
    last_error = ""
    for attempt in range(retries + 1):
        try:
            questions = _extract_questions_from_chunk(
                client, 
                task.text, 
                max_output_tokens=max_output_tokens,
                fixed_category=fixed_category
            )
            return ChunkResult(chunk_id=task.chunk_id, questions=questions, success=True, retries=attempt)
        except Exception as exc:
            last_error = str(exc)
            logger.warning(f"Chunk extraction failed (attempt {attempt+1}/{retries+1}): {exc}")
            if attempt < retries:
                # 遇到超时增加退避等待时间
                wait_time = 2.0 * (2 ** attempt)
                time.sleep(wait_time)
    return ChunkResult(chunk_id=task.chunk_id, questions=[], success=False, retries=retries, error=last_error)


def classify_questions(
    long_text: str,
    client: LLMClient,
    max_tokens: int = MAX_CHUNK_TOKENS,
    max_workers: int = MAX_CLASSIFY_WORKERS,
    retries: int = MAX_CLASSIFY_RETRIES,
    max_output_tokens: int = IMPORT_MAX_OUTPUT_TOKENS,
    progress_hook: Callable[[int, int], None] | None = None,
    fixed_category: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    tasks = build_chunk_tasks(long_text, max_tokens=max_tokens)
    total = len(tasks)
    if total == 0:
        return [], {"total_chunks": 0, "done_chunks": 0, "success_chunks": 0, "failed_chunks": 0, "errors": []}
    all_results: list[ChunkResult] = []
    done = 0
    workers = max(1, min(max_workers, total))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_map = {
            executor.submit(_run_chunk_with_retry, client, task, retries, max_output_tokens, fixed_category): task for task in tasks
        }
        for future in as_completed(future_map):
            result = future.result()
            all_results.append(result)
            done += 1
            if progress_hook:
                progress_hook(done, total)
    all_results.sort(key=lambda x: x.chunk_id)
    merged: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for result in all_results:
        merged.extend(result.questions)
        if not result.success:
            errors.append({"chunk_id": result.chunk_id, "error": result.error})
    if merged:
        if fixed_category:
            for q in merged:
                q["category"] = fixed_category
        else:
            merged = apply_subject_classification(merged)
    stats = {
        "total_chunks": total,
        "done_chunks": done,
        "success_chunks": len([r for r in all_results if r.success]),
        "failed_chunks": len([r for r in all_results if not r.success]),
        "errors": errors,
    }
    return merged, stats
