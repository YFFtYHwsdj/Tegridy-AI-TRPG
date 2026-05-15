from __future__ import annotations

from src.agents.base import BaseAgent
from src.agents.prompts import CONTINUATION_CHECK_PROMPT
from src.context import AgentContext
from src.models import AgentNote


class ContinuationCheckAgent(BaseAgent):
    system_prompt = CONTINUATION_CHECK_PROMPT
    agent_name = "可行性检查"

    def execute(
        self,
        next_sub_action: dict,
        ctx: AgentContext,
        last_sub_summary: str,
    ) -> AgentNote:
        builder = ctx.build_message(include_global=False)
        builder.add_text("---")
        builder.add_text(f"上一个子行动已完成。上一个子行动的结果摘要: {last_sub_summary}")

        next_action_details = (
            f"行动类型: {next_sub_action.get('action_type', 'unknown')}\n"
            f"行动摘要: {next_sub_action.get('action_summary', '')}\n"
            f"玩家原始输入片段: {next_sub_action.get('fragment', '')}"
        )
        builder.add_block("下一个待执行的子行动", next_action_details)

        builder.add_text("请判断角色是否还能执行这个子行动。")
        return self._call_llm(builder.build())
