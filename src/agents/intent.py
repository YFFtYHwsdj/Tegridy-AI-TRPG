from __future__ import annotations

from src.agents.base import BaseAgent
from src.agents.prompts import INTENT_PROMPT
from src.context import AgentContext
from src.models import AgentNote


class IntentAgent(BaseAgent):
    system_prompt = INTENT_PROMPT
    agent_name = "意图解析Agent"

    def execute(self, player_input: str, ctx: AgentContext) -> AgentNote:
        user_msg = f"""{ctx.context_block}

叙事历史:
{ctx.narrative_block}

---
玩家输入: {player_input}

请解析玩家的意图。"""
        return self._call_llm(user_msg)
