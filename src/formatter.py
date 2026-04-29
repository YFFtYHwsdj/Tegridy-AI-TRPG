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


def format_limit_progress(limit, current: int) -> str:
    """格式化极限进度条。

    使用 █ 和 ░ 字符渲染进度条。
    例如: "时间压力: [███░░░] 3/6"

    Args:
        limit: Limit 对象
        current: 当前进度值

    Returns:
        单行格式化文本
    """
    prog = "/".join("█" * current + "░" * (limit.max_tier - current))
    return f"{limit.name}: [{prog}] {current}/{limit.max_tier}"


def format_challenge_state(challenge) -> str:
    """格式化挑战的完整状态信息。

    包含挑战名、描述、便签、极限进度、标签和状态。

    Args:
        challenge: Challenge 对象

    Returns:
        格式化的多行文本块
    """
    lines = [
        f"挑战: {challenge.name}",
        f"描述: {challenge.description}",
    ]
    if challenge.notes:
        lines.append(f"便签: {challenge.notes}")
    lines.append("极限:")
    progress = challenge.get_limit_progress()
    for limit in challenge.limits:
        current = progress[limit.name]
        lines.append(f"  - {format_limit_progress(limit, current)}")
    if challenge.base_tags:
        lines.append(f"基础标签: {', '.join(t.name for t in challenge.base_tags)}")
    lines.append(f"故事标签: {format_story_tags(challenge.story_tags)}")
    lines.append(f"当前状态: {format_statuses(challenge.statuses)}")
    return "\n".join(lines)


def format_challenge_for_consequence(challenge) -> str:
    """格式化挑战信息，供后果 Agent 专用。

    与 format_challenge_state 的区别：
    - 将便签作为「威胁来源」强调呈现
    - 不显示基础标签（后果 Agent 不需要角色的力量/弱点标签）
    - 简化极限信息为一行的汇总

    Args:
        challenge: Challenge 对象

    Returns:
        格式化的多行文本块
    """
    lines = [
        f"挑战: {challenge.name}",
        f"描述: {challenge.description}",
    ]
    if challenge.notes:
        lines.append(f"便签（威胁来源）: {challenge.notes}")
    else:
        lines.append("便签（威胁来源）: (无明确威胁描述，请从挑战性质推导)")

    progress = challenge.get_limit_progress()
    limits_str = (
        ", ".join(format_limit_progress(limit, progress[limit.name]) for limit in challenge.limits)
        if challenge.limits
        else "(无极限)"
    )
    lines.append(f"极限进度: {limits_str}")
    lines.append(f"故事标签: {format_story_tags(challenge.story_tags)}")
    lines.append(f"当前状态: {format_statuses(challenge.statuses)}")
    return "\n".join(lines)


def format_limit_gap(challenge) -> str:
    """格式化极限差距信息 —— 显示还需多少级才能触发每个极限。

    Args:
        challenge: Challenge 对象

    Returns:
        格式化的多行文本
    """
    lines = []
    progress = challenge.get_limit_progress()
    for limit in challenge.limits:
        current = progress[limit.name]
        gap = limit.max_tier - current
        if current > 0:
            matching = challenge.get_matching_statuses(limit.name)
            status_names = [s.name for s in matching if s.current_tier > 0]
            lines.append(
                f"  {limit.name}: 当前{current}/{limit.max_tier} "
                f"(需要+{gap}级到达极限, 已有状态: {', '.join(status_names)})"
            )
        else:
            lines.append(
                f"  {limit.name}: 当前{current}/{limit.max_tier} (需要+{gap}级到达极限, 尚无状态)"
            )
    return "\n".join(lines) if lines else "  (无极限)"
