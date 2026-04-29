from __future__ import annotations

import json

from src.agents.base import BaseAgent
from src.agents.prompts import CONSEQUENCE_PROMPT, QUICK_CONSEQUENCE_PROMPT
from src.context import AgentContext
from src.formatter import format_challenge_for_consequence
from src.models import AgentNote, RollResult


class ConsequenceAgent(BaseAgent):
    system_prompt = CONSEQUENCE_PROMPT
    agent_name = "后果Agent"

    def execute(
        self,
        intent_note: AgentNote,
        effect_note: AgentNote,
        roll_result: RollResult,
        ctx: AgentContext,
    ) -> AgentNote:
        roll_info = f"power={roll_result.power}, dice={roll_result.dice}, total={roll_result.total}, outcome={roll_result.outcome}"

        user_msg = f"""{ctx.assets_block}
{ctx.context_block}

叙事历史:
{ctx.narrative_block}

{format_challenge_for_consequence(ctx.challenge) if ctx.challenge else "(无挑战)"}

效果推演推理: {effect_note.reasoning}
已产生的效果: {json.dumps(effect_note.structured.get("effects", []), ensure_ascii=False)}

---
行动摘要: {intent_note.structured.get("action_summary", "")}
掷骰结果: {roll_info}

请生成后果。优先选择叙事性后果——只有在叙事本身不够有力时才使用机械效果。
一条后果条目中，叙事性和机械效果不可并存。({"(部分成功)" if roll_result.outcome == "partial_success" else "(失败)"})"""
        return self._call_llm(user_msg)


class QuickConsequenceAgent(BaseAgent):
    system_prompt = QUICK_CONSEQUENCE_PROMPT
    agent_name = "后果Agent(快速)"

    def execute(
        self,
        intent_note: AgentNote,
        roll_result: RollResult,
        ctx: AgentContext,
    ) -> AgentNote:
        roll_info = f"power={roll_result.power}, dice={roll_result.dice}, total={roll_result.total}, outcome={roll_result.outcome}"

        user_msg = f"""{ctx.assets_block}
{ctx.context_block}

叙事历史:
{ctx.narrative_block}

---
行动摘要: {intent_note.structured.get("action_summary", "")}
行动类型: {intent_note.structured.get("action_type", "unknown")}
掷骰结果: {roll_info}

请生成后果。优先选择叙事性后果——只有在叙事本身不够有力时才使用机械效果。
一条后果条目中，叙事性和机械效果不可并存。({"(部分成功)" if roll_result.outcome == "partial_success" else "(失败)"})"""
        return self._call_llm(user_msg)
