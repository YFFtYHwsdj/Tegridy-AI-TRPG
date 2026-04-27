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
        user_msg = f"""{ctx.context_block}

叙事历史:
{ctx.narrative_block}

---
上一个子行动已完成。上一个子行动的结果摘要: {last_sub_summary}

下一个待执行的子行动:
  行动类型: {next_sub_action.get('action_type', 'unknown')}
  行动摘要: {next_sub_action.get('action_summary', '')}
  玩家原始输入片段: {next_sub_action.get('fragment', '')}

请判断角色是否还能执行这个子行动。"""
        return self._call_llm(user_msg)
