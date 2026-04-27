from __future__ import annotations

from src.models import AgentNote


def resolve_sub_action_info(
    intent_note: AgentNote,
    sub_action: dict | None = None,
) -> tuple[str, str, str]:
    if sub_action:
        action_type = sub_action.get("action_type", "unknown")
        action_summary = sub_action.get("action_summary", "")
        fragment = sub_action.get("fragment", "")
        index = sub_action.get("_index", 0)
        split_info = f"""注意：这是一个拆分行动中的第 {index + 1} 个子行动。
玩家原始完整输入已被拆分为多个子行动，当前只处理以下片段：
  "{fragment}"
请只针对这个子行动进行判断。"""
    else:
        action_type = intent_note.structured.get("action_type", "unknown")
        action_summary = intent_note.structured.get("action_summary", "")
        split_info = ""
    return action_type, action_summary, split_info
