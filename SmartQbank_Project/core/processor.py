from __future__ import annotations

import sqlite3
from typing import Any

from db.crud import fetch_question_for_analysis, insert_questions_batch, update_question_analysis
from .classifier import parse_questions_json, stem_hash
from .llm_client import LLMClient
from .schemas import QuestionCreate


def generate_learning_report(client: LLMClient, paper: list[dict], answers: dict[int, str]) -> str:
    """根据考试结果生成学习报告"""
    if not paper:
        return "没有考试数据，无法生成报告。"
    
    # 统计信息
    total = len(paper)
    correct_count = 0
    wrong_details = []
    
    for idx, q in enumerate(paper):
        user_ans = (answers.get(idx) or "").strip().lower()
        std_ans = (q.get("answer") or "").strip().lower()
        if user_ans == std_ans:
            correct_count += 1
        else:
            wrong_details.append({
                "stem": q.get("stem", ""),
                "category": q.get("category", "通用"),
                "user_ans": user_ans,
                "std_ans": std_ans
            })
    
    score_rate = (correct_count / total) * 100
    
    # 构建 Prompt
    prompt = (
        f"本次考试共 {total} 题，正确率 {score_rate:.1f}%。\n"
        "以下是错题分布情况：\n"
    )
    for w in wrong_details[:10]: # 最多传10个错题细节防止 token 过多
        prompt += f"- [学科:{w['category']}] 题干:{w['stem'][:50]}... (用户填:{w['user_ans']}, 标准:{w['std_ans']})\n"
    
    prompt += (
        "\n请作为‘高级气象装备维修工程师’，为用户写一份简短的学习诊断报告（约250字）。内容包括：\n"
        "1. 总体评价：评价用户的知识掌握情况。\n"
        "2. 弱项分析：根据错题分布，指出用户需要加强的知识领域。\n"
        "3. 学习建议：给出具体的复习建议，如查阅哪些规范或加强哪类题目的练习。\n"
        "4. 励志寄语：简短鼓励。\n"
        "要求：语气专业且亲切，多使用行业术语。"
    )
    
    try:
        report = client.chat_completion(
            messages=[
                {"role": "system", "content": "你是一位资深气象机务员，擅长进行业务指导和学习诊断。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
            max_tokens=1000,
        )
        return report.strip()
    except Exception as e:
        return f"生成报告时遇到点小问题：{str(e)}"

def generate_learning_report_stream(client: LLMClient, paper: list[dict], answers: dict[int, str]):
    """流式生成学习报告"""
    if not paper:
        yield "没有考试数据，无法生成报告。"
        return
    
    total = len(paper)
    correct_count = 0
    wrong_details = []
    for idx, q in enumerate(paper):
        user_ans = (answers.get(idx) or "").strip().lower()
        std_ans = (q.get("answer") or "").strip().lower()
        if user_ans == std_ans:
            correct_count += 1
        else:
            wrong_details.append({
                "stem": q.get("stem", ""),
                "category": q.get("category", "通用"),
                "user_ans": user_ans,
                "std_ans": std_ans
            })
    
    score_rate = (correct_count / total) * 100
    prompt = (
        f"本次考试共 {total} 题，正确率 {score_rate:.1f}%。\n"
        "以下是错题分布情况：\n"
    )
    for w in wrong_details[:10]:
        prompt += f"- [学科:{w['category']}] 题干:{w['stem'][:50]}... (用户填:{w['user_ans']}, 标准:{w['std_ans']})\n"
    
    prompt += (
        "\n请作为‘高级气象装备维修工程师’，为用户写一份简短的学习诊断报告（约250字）。内容包括：\n"
        "1. 总体评价：评价用户的知识掌握情况。\n"
        "2. 弱项分析：根据错题分布，指出用户需要加强的知识领域。\n"
        "3. 学习建议：给出具体的复习建议，如查阅哪些规范或加强哪类题目的练习。\n"
        "4. 励志寄语：简短鼓励。\n"
        "要求：语气专业且亲切，多使用行业术语。"
    )
    
    yield from client.chat_stream(
        messages=[
            {"role": "system", "content": "你是一位资深气象机务员，擅长进行业务指导和学习诊断。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.5,
        max_tokens=1000,
    )

def upsert_questions(conn: sqlite3.Connection, questions: list[dict[str, Any]], source: str = "") -> dict[str, int]:
    payload: list[QuestionCreate] = []
    for q in questions:
        payload.append(
            QuestionCreate(
                stem=q["stem"],
                options=q.get("options", []),
                answer=q["answer"],
                question_type=q.get("question_type", "single"),
                category=q["category"],
                tag=q.get("tag", ""),
                difficulty=int(q["difficulty"]),
                source=source,
                hash_val=stem_hash(q["stem"]),
            )
        )
    stats = insert_questions_batch(conn, payload, chunk_size=50)
    return stats.model_dump()


def get_or_generate_analysis(conn: sqlite3.Connection, client: LLMClient, question_id: int, retry: int = 3) -> str:
    question = fetch_question_for_analysis(conn, question_id)
    if not question:
        return "未找到该题目。"
    if question.analysis:
        return question.analysis
    prompt = (
        f"题干：{question.stem}\n"
        f"选项：{question.options}\n"
        f"答案：{question.answer}\n"
        "请给出简洁解析，控制在 4 条要点内，每条不超过 35 字，最后补 1 条易错提醒。"
    )
    analysis = client.chat_completion(
        messages=[
            {"role": "system", "content": "你是严谨的题目解析助手。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=1000,
    ).strip()
    update_question_analysis(conn, question_id, analysis, retry=retry)
    return analysis


def generate_questions_for_gap(
    conn: sqlite3.Connection,
    client: LLMClient,
    category: list[str],
    gap_count: int,
) -> dict[str, int]:
    if gap_count <= 0:
        return {"success": 0, "duplicate": 0, "failed": 0}
    category_text = "、".join(category) if category else "通用学科"
    stats = {"success": 0, "duplicate": 0, "failed": 0}
    remaining = gap_count
    batch_size = 8
    max_rounds = max(2, (gap_count + batch_size - 1) // batch_size + 2)
    empty_round = 0
    for _ in range(max_rounds):
        if remaining <= 0:
            break
        ask_count = min(batch_size, remaining)
        prompt = (
            f"请生成 {ask_count} 道客观题，学科范围：{category_text}。"
            "输出 JSON 对象，结构为 {\"questions\":[{\"stem\":\"\",\"options\":[],\"answer\":\"\",\"question_type\":\"single\",\"category\":\"\",\"tag\":\"\"}]}。"
            "每题必须有4个选项和标准答案（A/B/C/D之一）。"
            "question_type 固定为 single。"
            "如出现复杂公式，请使用 LaTeX 并包裹在 $...$ 中。"
            "不要输出任何额外说明。"
        )
        generated_text = client.chat_completion(
            messages=[{"role": "system", "content": "你是题库出题助手。"}, {"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.6,
            max_tokens=2800,
        )
        generated_questions = parse_questions_json(generated_text, client)
        if category:
            main_category = category[0]
            for q in generated_questions:
                if q.get("category") not in category:
                    q["category"] = main_category
        one_stat = upsert_questions(conn, generated_questions, source="llm_gap_fill")
        stats["success"] += one_stat["success"]
        stats["duplicate"] += one_stat["duplicate"]
        stats["failed"] += one_stat["failed"]
        remaining -= one_stat["success"]
        if one_stat["success"] == 0:
            empty_round += 1
        else:
            empty_round = 0
        if empty_round >= 2:
            break
    return stats
