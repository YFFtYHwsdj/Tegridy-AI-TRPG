from __future__ import annotations


def format_role_tags(tags: list) -> str:
    lines = []
    for tag in tags:
        desc = f" ({tag.description})" if tag.description else ""
        lines.append(f"  - [{tag.tag_type}] {tag.name}{desc}")
    return "\n".join(lines)


def format_statuses(statuses: dict) -> str:
    if not statuses:
        return "  (无当前状态)"
    lines = []
    for name, status in statuses.items():
        ticked = sorted(status.ticked_boxes) if status.ticked_boxes else []
        lines.append(f"  - {name}: 等级{status.current_tier} (勾选: {ticked})")
    return "\n".join(lines)


def format_story_tags(story_tags: dict) -> str:
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
    prog = "/".join("█" * current + "░" * (limit.max_tier - current))
    return f"{limit.name}: [{prog}] {current}/{limit.max_tier}"


def format_challenge_state(challenge) -> str:
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


def format_limit_gap(challenge) -> str:
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
                f"  {limit.name}: 当前{current}/{limit.max_tier} "
                f"(需要+{gap}级到达极限, 尚无状态)"
            )
    return "\n".join(lines) if lines else "  (无极限)"
