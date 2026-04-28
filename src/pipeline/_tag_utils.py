"""标签匹配工具 —— 从 Agent 便签中提取标签名和状态 tier。

本模块提供纯 Python 工具函数，从 TagMatcherAgent 的结构化输出中
提取标签名称列表和最佳/最差状态 tier。这些是力量值计算的输入参数，
必须在确定性代码中完成（遵循"可判定逻辑用代码"原则）。
"""

from __future__ import annotations

from src.models import AgentNote


def _extract_names_from_tags(items: list, key: str = "name") -> list[str]:
    """从标签条目列表中提取名称。

    标签条目可能是 dict（含 name 字段）或纯 str 两种格式。
    此函数统一处理两种格式，并过滤掉空值。

    Args:
        items: 标签条目列表
        key: 从 dict 格式中提取名称的键名，默认 "name"

    Returns:
        标签名称字符串列表
    """
    result = []
    for item in items:
        if isinstance(item, dict):
            val = item.get(key)
            if val:
                result.append(val)
        elif isinstance(item, str):
            result.append(item)
    return result


# 公开别名，保持调用处语义清晰
extract_tag_names = _extract_names_from_tags
extract_status_names = _extract_names_from_tags


def extract_status_tiers(tag_note: AgentNote):
    """从 Tag 匹配 Agent 的便签中提取最佳与最差状态 tier。

    帮助性状态（helping_statuses）取最高 tier 作为正面加成，
    阻碍性状态（hindering_statuses）取最高 tier 作为负面减成。

    Args:
        tag_note: Tag 匹配 Agent 的分析便签

    Returns:
        (best_tier, worst_tier) 元组，值范围为 0-6
    """
    helping = tag_note.structured.get("helping_statuses", [])
    hindering = tag_note.structured.get("hindering_statuses", [])

    best_tier = max(
        (s["tier"] for s in helping if isinstance(s, dict) and s.get("tier")), default=0
    )
    worst_tier = max(
        (s["tier"] for s in hindering if isinstance(s, dict) and s.get("tier")), default=0
    )
    return best_tier, worst_tier
