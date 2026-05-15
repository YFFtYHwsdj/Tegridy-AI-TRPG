from __future__ import annotations

from src.agents.base import BaseAgent
from src.agents.prompts.evolution import EVOLUTION_PROMPT
from src.context import AgentContext
from src.models import AgentNote


class EvolutionAgent(BaseAgent):
    system_prompt = EVOLUTION_PROMPT
    agent_name = "成长演化Agent"
    json_mode = True

    def execute(
        self,
        player_input: str,
        ctx: AgentContext,
        active_theme_name: str,
    ) -> AgentNote:
        """执行主题进化的交互流。"""
        # 如果是第一次唤醒，player_input 可能为空或为系统占位符
        user_msg = (
            f"玩家回复: {player_input}" if player_input else "玩家触发了主题突破，请提供选项。"
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
