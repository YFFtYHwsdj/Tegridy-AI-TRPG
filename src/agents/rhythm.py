from __future__ import annotations

from src.agents.base import BaseAgent
from src.agents.prompts import RHYTHM_SYSTEM_PROMPT
from src.context import AgentContext
from src.models import AgentNote


class RhythmAgent(BaseAgent):
    system_prompt = RHYTHM_SYSTEM_PROMPT
    agent_name = "节奏Agent"

    def execute(self, ctx: AgentContext) -> AgentNote:
        builder = ctx.build_message(include_global=False)
        builder.add_text("请用生动的叙事建立场景，最后把聚光灯交给玩家。")
        return self._call_llm(builder.build())
