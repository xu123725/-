from __future__ import annotations

from typing import Any
from sqlalchemy.orm import Session
import json

from db.models import Question
from .llm_client import LLMClient


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

def get_or_generate_analysis(db: Session, client: LLMClient, question_id: int, retry: int = 3) -> str:
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        return "未找到该题目。"
    if question.analysis:
        return question.analysis
    
    try:
        options = json.loads(question.options_json) if question.options_json else []
    except Exception:
        options = []
        
    prompt = (
        f"题干：{question.stem}\n"
        f"选项：{options}\n"
        f"答案：{question.answer}\n"
        "请给出简洁解析，控制在 4 条要点内，每条不超过 35 字，最后补 1 条易错提醒。"
    )
    try:
        analysis = client.chat_completion(
            messages=[
                {"role": "system", "content": "你是严谨的题目解析助手。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1000,
        ).strip()
        question.analysis = analysis
        db.commit()
        return analysis
    except Exception as e:
        return f"解析生成失败: {e}"
