from __future__ import annotations

import json

from src.agents._utils import resolve_sub_action_info
from src.agents.base import BaseAgent
from src.agents.prompts import OUTCOME_PROMPT, QUICK_OUTCOME_PROMPT
from src.context import AgentContext
from src.formatter import (
    format_role_tags,
    format_statuses,
)
from src.models import AgentNote, RollResult


class OutcomeAgent(BaseAgent):
    system_prompt = OUTCOME_PROMPT
    agent_name = "结算推演Agent"

    def execute(
        self,
        intent_note: AgentNote,
        tag_note: AgentNote,
        roll_result: RollResult,
        ctx: AgentContext,
        sub_action: dict | None = None,
    ) -> AgentNote:
        power_tags_str = format_role_tags(ctx.character.power_tags) if ctx.character else ""
        weakness_tags_str = format_role_tags(ctx.character.weakness_tags) if ctx.character else ""
        char_status_str = format_statuses(ctx.character.statuses) if ctx.character else ""
        available_power = max(roll_result.power, 0)
        roll_info = f"power={roll_result.power}, dice={roll_result.dice}, total={roll_result.total}, outcome={roll_result.outcome}"

        action_type, action_summary, split_info = resolve_sub_action_info(intent_note, sub_action)

        user_msg = f"""{ctx.assets_block}
{ctx.context_block}

叙事历史:
{ctx.narrative_block}

角色能力标签:
{power_tags_str}

角色弱点标签:
{weakness_tags_str}

角色当前状态:
{char_status_str}



意图解析:
  reasoning: {intent_note.reasoning}
  action_type: {action_type}
  action_summary: {action_summary}
{split_info}

标签匹配:
  reasoning: {tag_note.reasoning}
  matched_power_tags: {json.dumps(tag_note.structured.get("matched_power_tags", []), ensure_ascii=False)}
  matched_weakness_tags: {json.dumps(tag_note.structured.get("matched_weakness_tags", []), ensure_ascii=False)}



---
掷骰结果: {roll_info}
可用力量: {available_power} (你生成所有效果的总力量花费必须 ≤ {available_power}。参考规则中的力量花费速查)

请一次性推演本次行动的效果（如果有）和后果（如果有）。
注意：大成功(10+)不应有后果；失败(6-)不应有增益效果。"""

        note = self._call_llm(user_msg)

        # 强制代码校验：根据掷骰结果拦截不符合规则的输出
        if roll_result.outcome == "full_success":
            note.structured["consequences"] = []
        elif roll_result.outcome == "failure":
            note.structured["effects"] = []

        return note


class QuickOutcomeAgent(BaseAgent):
    system_prompt = QUICK_OUTCOME_PROMPT
    agent_name = "结算推演Agent(快速)"

    def execute(
        self,
        intent_note: AgentNote,
        roll_result: RollResult,
        ctx: AgentContext,
    ) -> AgentNote:
        roll_info = f"power={roll_result.power}, dice={roll_result.dice}, total={roll_result.total}, outcome={roll_result.outcome}"

        # 快速模式下只需要简单信息
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

        note = self._call_llm(user_msg)

        # 强制代码校验
        if roll_result.outcome == "full_success":
            note.structured["consequences"] = []
        return note
