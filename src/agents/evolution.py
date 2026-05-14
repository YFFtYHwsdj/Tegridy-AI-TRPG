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

        rendered_prompt = self.system_prompt.format(
            global_block=ctx.global_block,
            active_theme_name=active_theme_name,
        )

        messages = [
            {"role": "system", "content": rendered_prompt},
        ]

        # 将本次 session 之前的相关对话记录喂给大模型
        # 由于是多轮对话，ctx.narrative_block 可以包含这几轮的聊天历史
        messages.append(
            {"role": "user", "content": f"对话上下文:\n{ctx.narrative_block}\n\n{user_msg}"}
        )

        # 为了保证它按照 JSON 格式输出
        structured_data = self._invoke_llm(messages, expected_format="json")

        reasoning = structured_data.get("reasoning", "")
        return AgentNote(reasoning=reasoning, structured=structured_data)
