from __future__ import annotations

from src.agents.base import BaseAgent
from src.agents.prompts import LIMIT_BREAK_PROMPT
from src.context import AgentContext
from src.formatter import format_challenge_state
from src.models import AgentNote, Challenge


class LimitBreakAgent(BaseAgent):
    system_prompt = LIMIT_BREAK_PROMPT
    agent_name = "极限突破Agent"

    def execute(
        self,
        limit_names: list[str],
        challenge: Challenge,
        ctx: AgentContext,
    ) -> AgentNote:
        progress = challenge.get_limit_progress()
        limits_detail = []
        for name in limit_names:
            for limit in challenge.limits:
                if limit.name == name:
                    current = progress[limit.name]
                    limits_detail.append(f"  {limit.name}: {current}/{limit.max_tier} (极限突破!)")
                    break

        user_msg = f"""{ctx.context_block}

叙事历史:
{ctx.narrative_block}

{format_challenge_state(challenge)}

---
突破的极限:
{chr(10).join(limits_detail)}

请生成这个转折时刻的叙事。描述发生了什么——挑战方的某个防御被粉碎了。"""
        return self._call_llm(user_msg)
