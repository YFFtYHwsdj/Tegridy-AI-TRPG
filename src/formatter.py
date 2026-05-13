"""格式化工具 —— 将游戏数据渲染为可读的文本块。

提供各类格式化函数，将 Tag、Status、StoryTag、Limit、Challenge
等数据模型格式化为人类可读的文本（供 Agent 上下文和调试输出使用）。
"""

from __future__ import annotations

import logging

from src.models import PowerTag, WeaknessTag

logger = logging.getLogger("aitrpg.game")


def format_role_tags(tags: list) -> str:
    """格式化标签列表（力量/弱点）。

    通过 isinstance 类型判别确定标签前缀，不依赖 tag_type 字符串字段。

    Args:
        tags: PowerTag 或 WeaknessTag 对象列表

    Returns:
        格式化的多行文本
    """
    lines = []
    for tag in tags:
        desc = f" ({tag.description})" if tag.description else ""
        if isinstance(tag, PowerTag):
            prefix = "power"
        elif isinstance(tag, WeaknessTag):
            prefix = "weakness"
        else:
            logger.warning("format_role_tags 收到未知类型标签: %s", type(tag).__name__)
            prefix = "?"
        lines.append(f"  - [{prefix}] {tag.name}{desc}")
    return "\n".join(lines)


def format_statuses(statuses: dict) -> str:
    """格式化状态字典。

    Args:
        statuses: {状态名: Status对象} 字典

    Returns:
        格式化的多行文本，每行显示状态名、等级和已勾选的 tier
    """
    if not statuses:
        return "  (无当前状态)"
    lines = []
    for name, status in statuses.items():
        ticked = sorted(status.ticked_boxes) if status.ticked_boxes else []
        lines.append(f"  - {name}: 等级{status.current_tier} (勾选: {ticked})")
    return "\n".join(lines)


def format_story_tags(story_tags: dict) -> str:
    """格式化叙事标签字典。

    Args:
        story_tags: {标签名: StoryTag对象} 字典

    Returns:
        格式化的多行文本，标注一次性/消耗品属性
    """
    if not story_tags:
        return "  (无故事标签)"
    lines = []
    for name, tag in story_tags.items():
        qualifiers = []
        if tag.is_single_use:
            qualifiers.append("单次使用")
        if tag.is_consumable:
            qualifiers.append("消耗品")
        qual_str = f" ({', '.join(qualifiers)})" if qualifiers else ""
        desc_str = f" — {tag.description}" if tag.description else ""
        lines.append(f"  - {name}{qual_str}{desc_str}")
    return "\n".join(lines)
