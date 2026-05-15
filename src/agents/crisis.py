from __future__ import annotations

from src.agents.base import BaseAgent
from src.agents.prompts.crisis import CRISIS_PROMPT
from src.context import AgentContext
from src.models import AgentNote


class CrisisAgent(BaseAgent):
    system_prompt = CRISIS_PROMPT
    agent_name = "危机重铸Agent"
    json_mode = True

    def execute(
        self,
        player_input: str,
        ctx: AgentContext,
        active_theme_name: str,
    ) -> AgentNote:
        """执行主题破碎的交互流。"""
        user_msg = (
            f"玩家回复: {player_input}"
            if player_input
            else "系统提示：玩家的该主题已经满足彻底毁灭的条件。请开启危机流程。"
        )

        builder = ctx.build_message(include_global=True)
        builder.add_block("对话上下文", ctx.narrative_block)
        builder.add_text(user_msg)
        user_msg = builder.build()

        original_prompt = self.system_prompt
        self.system_prompt = original_prompt.format(
            active_theme_name=active_theme_name,
        )

        try:
            return self._call_llm(user_msg)
        finally:
            self.system_prompt = original_prompt
