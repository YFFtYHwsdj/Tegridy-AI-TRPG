"""标签匹配 Agent —— 负责判断角色特质状态如何影响当前行动。"""

from __future__ import annotations

from src.agents._utils import resolve_sub_action_info
from src.agents.base import BaseAgent
from src.agents.prompts import TAG_MATCHER_PROMPT
from src.context import AgentContext
from src.formatter import format_role_tags, format_statuses
from src.models import AgentNote


class TagMatcherAgent(BaseAgent):
    """匹配相关的力量标签、弱点标签，以及具有影响的当前状态。"""

    system_prompt = TAG_MATCHER_PROMPT
    agent_name = "标签匹配Agent"

    def execute(
        self,
        intent_note: AgentNote,
        ctx: AgentContext,
        sub_action: dict | None = None,
    ) -> AgentNote:
        """执行标签与状态匹配。

        从角色的力量、弱点标签及当前状态中，筛选出对本次行动有帮助或阻碍的因素，以计算骰子加值。

        Args:
            intent_note: 意图解析的结果便签
            ctx: 当前场景的上下文
            sub_action: 子动作信息（如果有拆分）

        Returns:
            AgentNote: 包含匹配结果的分析便签
        """
        power_tags_str = format_role_tags(ctx.character.power_tags) if ctx.character else ""
        weakness_tags_str = format_role_tags(ctx.character.weakness_tags) if ctx.character else ""
        status_str = format_statuses(ctx.character.statuses) if ctx.character else ""

        action_type, action_summary, split_info = resolve_sub_action_info(intent_note, sub_action)

        builder = ctx.build_message(include_global=False)

        builder.add_block("角色力量标签", power_tags_str)
        builder.add_block("角色弱点标签", weakness_tags_str)
        builder.add_block("角色当前状态", status_str)

        builder.add_text("---")
        intent_details = (
            f"行动类型: {action_type}\n"
            f"行动摘要: {action_summary}\n"
            f"是否拆分: {intent_note.structured.get('is_split_action', False)}\n"
            f"{split_info}"
        ).strip()
        builder.add_block("意图解析", intent_details)

        builder.add_text("请判断哪些标签帮助/阻碍本次行动，以及角色当前状态中哪些帮助哪些阻碍。")

        return self._call_llm(builder.build())
