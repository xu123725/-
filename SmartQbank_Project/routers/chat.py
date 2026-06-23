from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session

from db.database import get_db
from core.agent_logic import process_user_request
from core.llm_client import LLMClient
from core.retriever import retrieve_questions, retrieve_knowledge
from core.categories import build_major_map, MAJOR_RULES
import config

router = APIRouter()

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]

def _parse_count(prompt: str) -> int:
    import re
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

@router.post("/stream")
async def chat_stream(request: ChatRequest, db: Session = Depends(get_db)):
    """流式对话接口 (Server-Sent Events)"""
    if not request.messages:
        raise HTTPException(status_code=400, detail="Empty messages")
        
    last_message = request.messages[-1].content
    
    # 我们把核心逻辑中的判断抽出来，如果匹配到“组卷”意图，则不走大模型，直接返回静态结果
    from db.crud import fetch_categories
    categories = fetch_categories(db)
    
    if _needs_paper(last_message):
        selected = _match_categories(last_message, categories)
        if not selected:
            if categories:
                msg = "我已收到组卷请求，但没有识别到学科。当前可用学科有：" + "、".join(categories[:8])
            else:
                msg = "当前题库里还没有可用学科，请先在“文档入库”中导入题目。"
            async def fast_reply():
                yield f"data: {msg}\n\n"
            return StreamingResponse(fast_reply(), media_type="text/event-stream")
            
        question_type = _parse_question_type(last_message)
        recent_hours = max(0, int(config.DEFAULT_RECENT_HOURS))
        questions = retrieve_questions(
            conn=db,
            total_count=_parse_count(last_message),
            categories=selected,
            recent_hours=recent_hours,
            question_type=question_type,
        )
        relaxed = False
        if not questions and recent_hours > 0:
            questions = retrieve_questions(
                conn=db,
                total_count=_parse_count(last_message),
                categories=selected,
                recent_hours=0,
                question_type=question_type,
            )
            relaxed = bool(questions)
            
        if questions:
            type_text = {"single": "单选题", "fill_blank": "填空题", "all": "全部题型"}.get(question_type, "全部题型")
            if relaxed:
                msg = f"已为您生成 {len(questions)} 道“{'、'.join(selected)}”{type_text}，并自动放宽了最近使用过滤。"
            else:
                msg = f"已为您生成 {len(questions)} 道“{'、'.join(selected)}”{type_text}。"
        else:
            msg = "未找到符合条件的题目，请换一个学科、调整题型，或减少最近使用过滤后重试。"
            
        async def fast_reply():
            yield f"data: {msg}\n\n"
        return StreamingResponse(fast_reply(), media_type="text/event-stream")

    # 否则，走 RAG 和大模型流式输出
    kb_results = retrieve_knowledge(db, last_message, limit=3)
    knowledge_context = ""
    if kb_results:
        knowledge_context = "\n".join([f"--- 知识库片段 [{r['source']}] ---\n{r['content']}" for r in kb_results])

    system_prompt = (
        "你现在是一位具有20年经验的‘高级气象装备维修工程师’。你的回答应当专业、严谨且富有实践经验。\n"
        "你的主要任务是协助用户在‘自动气象站智慧学习平台’上进行业务学习和故障排查。回答时请遵循以下原则：\n"
        "1. 专业性：使用准确的气象装备术语。\n"
        "2. 实践导向：在解释知识点时，尽量结合台站实际维护场景。\n"
        "3. 引用来源：如果提供了知识库参考片段，请务必在回答中注明引用来源。\n"
        "4. 鼓励学习：适当引导其关注相关的业务考点。\n"
        "\n请用中文回答。"
    )
    if knowledge_context:
        system_prompt += f"\n\n以下是相关的参考知识，请优先结合这些知识回答用户问题，并注明出处：\n{knowledge_context}"

    llm_messages = [{"role": "system", "content": system_prompt}]
    for m in request.messages[-10:]:
        llm_messages.append({"role": m.role, "content": m.content})

    client = LLMClient(
        api_key=config.get_api_key(),
        base_url=config.get_api_base_url(),
        model=config.get_api_model(),
        timeout=config.IMPORT_LLM_TIMEOUT,
    )

    async def event_stream():
        import json
        try:
            for chunk in client.chat_stream(llm_messages):
                # 转义换行符避免破坏 SSE 格式
                escaped_chunk = json.dumps({"content": chunk})
                yield f"data: {escaped_chunk}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'content': f'\\n\\n[连接异常: {str(e)}]' })}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")