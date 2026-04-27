from __future__ import annotations

from src.agents.base import BaseAgent
from src.agents.prompts import RESOLUTION_MODE_PROMPT
from src.context import AgentContext
from src.models import AgentNote


class ResolutionModeAgent(BaseAgent):
    system_prompt = RESOLUTION_MODE_PROMPT
    agent_name = "结算模式路由器"

    def execute(
        self,
        intent_note: AgentNote,
        ctx: AgentContext,
    ) -> AgentNote:
        action_type = intent_note.structured.get("action_type", "unknown")
        action_summary = intent_note.structured.get("action_summary", "")

        user_msg = f"""{ctx.context_block}

叙事历史:
{ctx.narrative_block}

---
意图解析结果:
  action_type: {action_type}
  action_summary: {action_summary}
  is_split_action: {intent_note.structured.get('is_split_action', False)}

玩家输入: {ctx.player_input}

请判断此行动应该用快速结算还是跟踪结算。"""
        return self._call_llm(user_msg)
