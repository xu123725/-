from __future__ import annotations

import logging
from pathlib import Path

import pypdfium2 as pdfium
from docx import Document
from docx.document import Document as DocxDocument
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph
from pypdf import PdfReader

logger = logging.getLogger(__name__)


def _iter_blocks(doc: DocxDocument):
    for child in doc.element.body.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, doc)
        elif isinstance(child, CT_Tbl):
            yield Table(child, doc)


def _table_to_lines(table: Table) -> list[str]:
    lines: list[str] = []
    try:
        for row in table.rows:
            # 针对合并单元格的鲁棒性处理：直接遍历单元格可能在复杂合并时报错
            cells = []
            for cell in row.cells:
                try:
                    text = cell.text.strip()
                    if text:
                        cells.append(text)
                except Exception:
                    # 遇到损坏或极其复杂的合并单元格跳过
                    continue
            if cells:
                lines.append(" | ".join(cells))
    except Exception as e:
        # 如果整表解析失败，回退到极简模式
        try:
            for row in table.rows:
                row_text = []
                for cell in row.cells:
                    try:
                        row_text.append(cell.text.strip())
                    except: pass
                if any(row_text):
                    lines.append(" | ".join([t for t in row_text if t]))
        except:
            pass
    return lines


def extract_docx_content(file_path: str | Path) -> str:
    doc = Document(str(file_path))
    blocks: list[str] = []
    for block in _iter_blocks(doc):
        if isinstance(block, Paragraph):
            text = block.text.strip()
            if text:
                blocks.append(text)
        elif isinstance(block, Table):
            table_lines = _table_to_lines(block)
            if table_lines:
                blocks.append("\n".join(table_lines))
    return "\n\n".join(blocks).strip()


def extract_pdf_content(file_path: str | Path) -> str:
    """
    提取 PDF 内容，支持 pypdf 和 pypdfium2 双引擎。
    """
    path_str = str(file_path)
    texts: list[str] = []

    # 引擎 1: pypdf (常规提取)
    try:
        reader = PdfReader(path_str)
        for page in reader.pages:
            t = (page.extract_text() or "").strip()
            if t:
                texts.append(t)
    except Exception as e:
        logger.warning(f"pypdf extraction failed for {path_str}: {e}")

    # 如果 pypdf 提取结果为空，或者提取出的字数明显过少，尝试引擎 2: pypdfium2 (基于 Chrome 引擎，更强力)
    if len("".join(texts)) < 50:
        try:
            pdf = pdfium.PdfDocument(path_str)
            texts = [] # 重置，避免重复
            for i in range(len(pdf)):
                page = pdf[i]
                textpage = page.get_textpage()
                t = textpage.get_text_range().strip()
                if t:
                    texts.append(t)
        except Exception as e:
            logger.error(f"pypdfium2 extraction also failed for {path_str}: {e}")

    return "\n\n".join(texts).strip()


def extract_txt_content(file_path: str | Path) -> str:
    """提取纯文本文件内容"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except UnicodeDecodeError:
        # 如果 UTF-8 失败，尝试 GBK
        with open(file_path, "r", encoding="gbk") as f:
            return f.read().strip()

def extract_content(file_path: str | Path) -> str:
    suffix = Path(file_path).suffix.lower()
    if suffix == ".docx":
        return extract_docx_content(file_path)
    if suffix == ".pdf":
        return extract_pdf_content(file_path)
    if suffix in [".txt", ".md"]:
        return extract_txt_content(file_path)
    raise ValueError(f"不支持的文件格式: {suffix}")
