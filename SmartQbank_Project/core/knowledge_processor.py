import logging
import re
from typing import List, Dict, Any
from pathlib import Path
from typing import List, Dict, Any
from .extractor import extract_content
from db.database import get_connection

logger = logging.getLogger(__name__)

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    将长文本切分为较小的块，以便于检索和生成。
    """
    # 清理多余空行，统一换行符
    text = text.replace('\r\n', '\n').strip()
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    text_len = len(text)
    if text_len == 0:
        return []
    
    # 如果文本非常短，直接作为一个块返回
    if text_len <= chunk_size:
        return [text]
        
    chunks = []
    start = 0
    
    while start < text_len:
        end = start + chunk_size
        if end < text_len:
            # 尝试在最后的换行或句号处切分，避免断开完整句子
            # 在 50% ~ 100% 的 chunk_size 范围内寻找切分点
            search_start = start + chunk_size // 2
            best_break = -1
            for char in ['\n\n', '\n', '。', '！', '？', '!', '?', '. ']:
                pos = text.rfind(char, search_start, end)
                if pos != -1:
                    best_break = pos + len(char)
                    break
            
            if best_break != -1:
                end = best_break
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # 移动指针，考虑重叠度
        start = end - overlap
        if start < 0: start = 0
        if end >= text_len: break
        
    return chunks

def ingest_knowledge(file_path: str, category: str = "竞赛要求") -> Dict[str, Any]:
    """
    提取文件内容并存入知识库。
    """
    try:
        path_obj = Path(file_path)
        if not path_obj.exists():
            return {"success": False, "error": f"文件不存在: {file_path}"}
            
        content = extract_content(file_path)
        if not content or not content.strip():
            return {"success": False, "error": "内容提取为空，请确保文档包含可读文本。"}
            
        file_name = path_obj.name
        chunks = chunk_text(content)
        
        if not chunks:
            return {"success": False, "error": "文本切分失败，未能生成有效的知识片段。"}
            
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # 先删除该文件的旧知识，实现幂等导入 (触发器会自动清理 FTS 表)
            cursor.execute("DELETE FROM knowledge_base WHERE source = ?", (file_name,))
                
            count = 0
            for i, chunk in enumerate(chunks):
                # 插入原始表 (触发器会自动同步到 FTS 表)
                cursor.execute(
                    "INSERT INTO knowledge_base (title, content, category, source) VALUES (?, ?, ?, ?)",
                    (f"{file_name} - Part {i+1}", chunk, category, file_name)
                )
                
                count += 1
            conn.commit()
            
        return {"success": True, "count": count}
    except Exception as e:
        logger.exception(f"Ingest knowledge failed for {file_path}")
        return {"success": False, "error": f"解析失败: {str(e)}"}
