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

        base_context = ctx.format_standard_blocks(include_global=True)
        user_msg = f"{base_context}\n\n对话上下文:\n{ctx.narrative_block}\n\n{user_msg}"

        original_prompt = self.system_prompt
        self.system_prompt = original_prompt.format(
            active_theme_name=active_theme_name,
        )

        try:
            return self._call_llm(user_msg)
        finally:
            self.system_prompt = original_prompt
