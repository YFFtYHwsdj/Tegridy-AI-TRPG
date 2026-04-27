from __future__ import annotations

import json
from src.agents.base import BaseAgent
from src.agents.prompts import EFFECT_ACTUALIZATION_PROMPT
from src.agents._utils import resolve_sub_action_info
from src.context import AgentContext
from src.formatter import (
    format_role_tags,
    format_statuses,
    format_story_tags,
    format_challenge_state,
    format_limit_gap,
)
from src.models import AgentNote, RollResult


class EffectActualizationAgent(BaseAgent):
    system_prompt = EFFECT_ACTUALIZATION_PROMPT
    agent_name = "效果推演Agent"

    def execute(
        self,
        intent_note: AgentNote,
        tag_note: AgentNote,
        roll_result: RollResult,
        ctx: AgentContext,
        sub_action: dict | None = None,
    ) -> AgentNote:
        if roll_result.outcome == "failure":
            return AgentNote(
                reasoning="掷骰结果为失败，不产生效果",
                structured={"effects": [], "narrative_hints": ""}
            )

        power_tags_str = format_role_tags(ctx.character.power_tags) if ctx.character else ""
        weakness_tags_str = format_role_tags(ctx.character.weakness_tags) if ctx.character else ""
        char_status_str = format_statuses(ctx.character.statuses) if ctx.character else ""
        char_story_tags_str = format_story_tags(ctx.character.story_tags) if ctx.character else ""
        available_power = max(roll_result.power, 0)
        roll_info = f"power={roll_result.power}, dice={roll_result.dice}, total={roll_result.total}, outcome={roll_result.outcome}"

        action_type, action_summary, split_info = resolve_sub_action_info(intent_note, sub_action)

        user_msg = f"""{ctx.context_block}

叙事历史:
{ctx.narrative_block}

角色能力标签:
{power_tags_str}

角色弱点标签:
{weakness_tags_str}

角色当前状态:
{char_status_str}

角色故事标签:
{char_story_tags_str}

意图解析:
  reasoning: {intent_note.reasoning}
  action_type: {action_type}
  action_summary: {action_summary}
{split_info}

标签匹配:
  reasoning: {tag_note.reasoning}
  matched_power_tags: {json.dumps(tag_note.structured.get('matched_power_tags', []), ensure_ascii=False)}
  matched_weakness_tags: {json.dumps(tag_note.structured.get('matched_weakness_tags', []), ensure_ascii=False)}

挑战: {format_challenge_state(ctx.challenge) if ctx.challenge else '(无)'}

挑战极限与状态差距:
{format_limit_gap(ctx.challenge) if ctx.challenge else '  (无极限)'}

---
掷骰结果: {roll_info}
可用力量: {available_power} (你生成所有效果的总力量花费必须 ≤ {available_power}。参考规则中的力量花费速查)

请推演此行动在故事中实际产生什么效果。首先选择合适的效果类型和操作，然后在可用力量预算内确定具体参数。"""
        return self._call_llm(user_msg)
