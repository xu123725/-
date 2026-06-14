import os
import logging
from pathlib import Path
from typing import List, Dict, Any
from db.database import get_connection
from config import RESOURCE_DIR

logger = logging.getLogger(__name__)

def scan_troubleshooting_resources() -> Dict[str, Any]:
    """
    扫描 resource 目录，同步故障排查资源到数据库。
    资源结构: resource/大类文件夹/具体操作.mp4 或 具体操作.txt 或 具体操作.jpg
    """
    if not RESOURCE_DIR.exists():
        return {"success": False, "error": f"资源目录不存在: {RESOURCE_DIR}"}

    try:
        new_items = []
        # 1. 扫描子文件夹（大类故障）
        for category_dir in RESOURCE_DIR.iterdir():
            if category_dir.is_dir():
                category_name = category_dir.name
                cases: Dict[str, Dict[str, str]] = {}
                
                for file in category_dir.iterdir():
                    if file.is_file():
                        case_name = file.stem
                        if case_name not in cases:
                            cases[case_name] = {"video": "", "doc": "", "image": "", "description": ""}
                        
                        suffix = file.suffix.lower()
                        rel_path = str(file.relative_to(RESOURCE_DIR.parent.parent))
                        
                        if suffix in ['.mp4', '.mkv', '.avi']:
                            cases[case_name]["video"] = rel_path
                        elif suffix in ['.jpg', '.jpeg', '.png', '.bmp']:
                            cases[case_name]["image"] = rel_path
                        elif suffix in ['.txt', '.md']:
                            cases[case_name]["doc"] = rel_path
                            try:
                                with open(file, 'r', encoding='utf-8') as f:
                                    cases[case_name]["description"] = f.read(200).strip()
                            except:
                                pass

                
                for title, paths in cases.items():
                    new_items.append({
                        "category": category_name,
                        "title": title,
                        "video_path": paths["video"],
                        "doc_path": paths["doc"],
                        "image_path": paths["image"],
                        "description": paths["description"],
                        "tags": f"{category_name}, {title}"
                    })
            
            # 2. 扫描根目录下的独立文件（直接作为核心流程案例）
            elif category_dir.is_file():
                suffix = category_dir.suffix.lower()
                if suffix in ['.mp4', '.mkv', '.avi', '.jpg', '.jpeg', '.png', '.bmp', '.txt', '.md']:
                    rel_path = str(category_dir.relative_to(RESOURCE_DIR.parent.parent))
                    case_name = category_dir.stem
                    new_items.append({
                        "category": "核心流程/软件故障",
                        "title": case_name,
                        "video_path": rel_path if suffix in ['.mp4', '.mkv', '.avi'] else "",
                        "doc_path": rel_path if suffix in ['.txt', '.md'] else "",
                        "image_path": rel_path if suffix in ['.jpg', '.jpeg', '.png', '.bmp'] else "",
                        "description": f"流程图资源: {case_name}",
                        "tags": f"核心, 流程图, {case_name}"
                    })

        # 写入数据库
        with get_connection() as conn:
            cursor = conn.cursor()
            # 简单起见，先清空再重新同步
            cursor.execute("DELETE FROM troubleshooting")
            for item in new_items:
                cursor.execute(
                    """
                    INSERT INTO troubleshooting (category, title, video_path, doc_path, image_path, description, tags)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (item["category"], item["title"], item["video_path"], item["doc_path"], item["image_path"], item["description"], item["tags"])
                )
            conn.commit()
            
        return {"success": True, "count": len(new_items)}
    except Exception as e:
        logger.exception("Scan troubleshooting resources failed")
        return {"success": False, "error": str(e)}

def search_troubleshooting(keyword: str = "") -> List[Dict[str, Any]]:
    """
    搜索故障排查资源
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        if not keyword:
            cursor.execute("SELECT * FROM troubleshooting ORDER BY category, title")
        else:
            query = f"%{keyword}%"
            cursor.execute(
                """
                SELECT * FROM troubleshooting 
                WHERE title LIKE ? OR category LIKE ? OR tags LIKE ? 
                ORDER BY category, title
                """,
                (query, query, query)
            )
        return [dict(row) for row in cursor.fetchall()]