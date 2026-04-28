from __future__ import annotations

from src.agents._utils import resolve_sub_action_info
from src.agents.base import BaseAgent
from src.agents.prompts import TAG_MATCHER_PROMPT
from src.context import AgentContext
from src.formatter import format_role_tags, format_statuses
from src.models import AgentNote


class TagMatcherAgent(BaseAgent):
    system_prompt = TAG_MATCHER_PROMPT
    agent_name = "标签匹配Agent"

    def execute(
        self,
        intent_note: AgentNote,
        ctx: AgentContext,
        sub_action: dict | None = None,
    ) -> AgentNote:
        power_tags_str = format_role_tags(ctx.character.power_tags) if ctx.character else ""
        weakness_tags_str = format_role_tags(ctx.character.weakness_tags) if ctx.character else ""
        status_str = format_statuses(ctx.character.statuses) if ctx.character else ""

        action_type, action_summary, split_info = resolve_sub_action_info(intent_note, sub_action)

        user_msg = f"""{ctx.context_block}

叙事历史:
{ctx.narrative_block}

角色力量标签:
{power_tags_str}

角色弱点标签:
{weakness_tags_str}

角色当前状态:
{status_str}

---
意图解析:
  行动类型: {action_type}
  行动摘要: {action_summary}
  是否拆分: {intent_note.structured.get("is_split_action", False)}
{split_info}

请判断哪些标签帮助/阻碍本次行动，以及角色当前状态中哪些帮助哪些阻碍。"""
        return self._call_llm(user_msg)
