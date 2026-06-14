from __future__ import annotations

from typing import Final

DEFAULT_MAJOR_CATEGORY: Final[str] = "05综合观测基础知识"

MAJOR_RULES: Final[list[tuple[str, tuple[str, ...]]]] = [
    ("03天气雷达", ("03天气雷达", "天气雷达", "雷达", "回波", "多普勒", "x波段", "s波段", "c波段")),
    ("05综合观测基础知识", ("05综合观测基础知识", "综合观测", "观测基础", "观测要素", "气温", "气压", "湿度", "降水", "风向", "风速")),
    ("06观测自动化及技术规定", ("06观测自动化及技术规定", "自动观测", "自动站", "技术规定", "业务规范", "观测规范")),
    ("07观测新平台和新装备", ("07观测新平台和新装备", "新平台", "新装备", "探空", "北斗", "gps/met", "风廓线雷达", "微波辐射计")),
    ("08数据格式及质量控制", ("08数据格式及质量控制", "数据格式", "报文", "编码", "质量控制", "质控", "数据校验")),
    ("09质量管理体系", ("09质量管理体系", "质量管理体系", "质量评估", "质量考核", "业务事故", "事故调查")),
    ("10探测环境保护", ("10探测环境保护", "探测环境", "环境保护", "防雷", "电磁", "迁建", "台站")),
    ("11法律法规及规章制度", ("11法律法规及规章制度", "法律法规", "规章制度", "条例", "办法", "合规", "无线电管理")),
    ("自动气象站维护与维修", ("自动气象站维护与维修", "维护", "维修", "保障", "备件", "更换", "故障", "排除")),
]


def to_major_category(name: str) -> str:
    lowered = (name or "").strip().lower()
    for major, keys in MAJOR_RULES:
        if any(k in lowered for k in keys):
            return major
    return DEFAULT_MAJOR_CATEGORY


def build_major_map(categories: list[str]) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for item in categories:
        major = to_major_category(item)
        mapping.setdefault(major, []).append(item)
    return dict(sorted(mapping.items(), key=lambda x: x[0]))
