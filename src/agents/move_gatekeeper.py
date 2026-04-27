from __future__ import annotations

from src.agents.base import BaseAgent
from src.agents.prompts import MOVE_GATEKEEPER_PROMPT
from src.context import AgentContext
from src.models import AgentNote


class MoveGatekeeperAgent(BaseAgent):
    system_prompt = MOVE_GATEKEEPER_PROMPT
    agent_name = "Move守门人"

    def execute(self, player_input: str, ctx: AgentContext) -> AgentNote:
        user_msg = f"""{ctx.context_block}

叙事历史:
{ctx.narrative_block}

---
玩家输入: {player_input}

请判断这个输入是否构成一个需要掷骰的Move。"""
        return self._call_llm(user_msg)
