import logging
import re
from typing import Any
from sqlalchemy.orm import Session

from db.crud import fetch_categories
from .llm_client import LLMClient
from .retriever import retrieve_questions, retrieve_knowledge
from .categories import MAJOR_RULES, build_major_map
import config

logger = logging.getLogger(__name__)


def _parse_count(prompt: str) -> int:
    match = re.search(r"(\d+)\s*道", prompt)
    if match:
        return max(1, min(100, int(match.group(1))))
    return 10


def _match_categories(prompt: str, categories: list[str]) -> list[str]:
    matched = [item for item in categories if item and item in prompt]
    if matched:
        return matched
    major_map = build_major_map(categories)
    prompt_lower = prompt.lower()
    hit_major = [major for major, keys in MAJOR_RULES if any(k in prompt_lower for k in keys)]
    expanded: list[str] = []
    for major in hit_major:
        expanded.extend(major_map.get(major, []))
    if expanded:
        return list(dict.fromkeys(expanded))
    if len(categories) == 1:
        return categories
    return []


def _needs_paper(prompt: str) -> bool:
    return any(word in prompt for word in ["生成", "组", "出一套", "来一套"]) and any(
        word in prompt for word in ["卷", "试卷", "卷子", "题"]
    )


def _parse_question_type(prompt: str) -> str:
    text = (prompt or "").lower()
    if "判断" in text:
        return "true_false"
    if "填空" in text:
        return "fill_blank"
    if any(w in text for w in ["单选", "选择", "选择题"]):
        return "single"
    return "all"


def _reset_exam_state(state: Any) -> None:
    state.exam_state.is_running = False
    state.exam_state.submitted = False
    state.exam_state.mode = ""
    state.exam_state.current_index = 0
    state.exam_state.answers = {}
    state.exam_state.revealed = {}
    state.exam_state.score = 0
    state.exam_state.time_left = 0


def _clean_response_text(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def process_user_request(prompt: str, state: Any, conn: Session) -> str:
    categories = fetch_categories(conn)
    
    # 1. 尝试识别是否为组卷/生成请求
    if _needs_paper(prompt):
        selected = _match_categories(prompt, categories)
        if not selected:
            if categories:
                return "我已收到组卷请求，但没有识别到学科。当前可用学科有：" + "、".join(categories[:8])
            return "当前题库里还没有可用学科，请先在“文档入库”中导入题目。"
        question_type = _parse_question_type(prompt)
        recent_hours = max(0, int(config.DEFAULT_RECENT_HOURS))
        questions = retrieve_questions(
            conn=conn,
            total_count=_parse_count(prompt),
            categories=selected,
            recent_hours=recent_hours,
            question_type=question_type,
        )
        relaxed = False
        if not questions and recent_hours > 0:
            questions = retrieve_questions(
                conn=conn,
                total_count=_parse_count(prompt),
                categories=selected,
                recent_hours=0,
                question_type=question_type,
            )
            relaxed = bool(questions)
        
        if questions:
            state.generated_paper = questions
            _reset_exam_state(state)
            type_text = {"single": "单选题", "fill_blank": "填空题", "all": "全部题型"}.get(question_type, "全部题型")
            if relaxed:
                return f"已为您生成 {len(questions)} 道“{'、'.join(selected)}”{type_text}，并自动放宽了最近使用过滤。现在可以去“模拟考试”里选择刷题练习或模拟考试。"
            return f"已为您生成 {len(questions)} 道“{'、'.join(selected)}”{type_text}。现在可以去“模拟考试”里选择刷题练习或模拟考试。"
        return "未找到符合条件的题目，请换一个学科、调整题型，或减少最近使用过滤后重试。"
    
    # 2. 如果不是组卷请求，则进入知识库检索 (RAG)
    kb_results = retrieve_knowledge(conn, prompt, limit=3)
    knowledge_context = ""
    if kb_results:
        knowledge_context = "\n".join([f"--- 知识库片段 [{r['source']}] ---\n{r['content']}" for r in kb_results])

    # 3. 调用 LLM 生成回复 (带上检索到的知识)
    client = LLMClient(
        api_key=config.get_api_key(),
        base_url=config.get_api_base_url(),
        model=config.get_api_model(),
        timeout=config.IMPORT_LLM_TIMEOUT,
    )
    
    system_prompt = (
        "你现在是一位具有20年经验的‘高级气象装备维修工程师’。你的回答应当专业、严谨且富有实践经验。\n"
        "你的主要任务是协助用户在‘自动气象站智慧学习平台’上进行业务学习和故障排查。回答时请遵循以下原则：\n"
        "1. 专业性：使用准确的气象装备术语（如：采集器、传感器、光电隔离、信号调理等）。\n"
        "2. 实践导向：在解释知识点时，尽量结合台站实际维护场景（如：巡检注意、雷击防护、接线排查）。\n"
        "3. 引用来源：如果提供了知识库参考片段，请务必在回答中注明引用来源（例如：根据《GB/T ...》或《XX技术手册》）。\n"
        "4. 鼓励学习：对于用户的疑问，除了给出答案，可以适当地引导其关注相关的业务考点。\n"
        "\n请用中文回答。"
    )
    if knowledge_context:
        system_prompt += f"\n\n以下是相关的参考知识，请优先结合这些知识回答用户问题，并注明出处：\n{knowledge_context}"
    
    messages = [{"role": "system", "content": system_prompt}]
    if hasattr(state, "chat_history") and state.chat_history:
        for msg in state.chat_history[-10:]:
            messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
    else:
        messages.append({"role": "user", "content": prompt})
    
    try:
        return _clean_response_text(
            client.chat_completion(
                messages=messages,
                temperature=0.4,
                max_tokens=1200,
            )
        )
    except Exception as exc:
        logger.exception("assistant failed")
        return f"智能助手暂时不可用：{exc}"
