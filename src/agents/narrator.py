from __future__ import annotations

import json
from src.agents.base import BaseAgent
from src.agents.prompts import NARRATOR_PROMPT, LITE_NARRATOR_PROMPT, QUICK_NARRATOR_PROMPT
from src.context import AgentContext
from src.models import AgentNote, RollResult


class NarratorAgent(BaseAgent):
    system_prompt = NARRATOR_PROMPT
    agent_name = "叙述者Agent"

    def execute(
        self,
        intent_note: AgentNote,
        effect_note: AgentNote,
        roll_result: RollResult,
        ctx: AgentContext,
        consequence_note: AgentNote | None = None,
    ) -> AgentNote:
        roll_summary = f"{roll_result.dice[0]}+{roll_result.dice[1]}+{roll_result.power}={roll_result.total} ({roll_result.outcome})"

        cons_reasoning = ""
        cons_structured = {}
        if consequence_note:
            cons_reasoning = consequence_note.reasoning
            cons_structured = consequence_note.structured

        user_msg = f"""{ctx.context_block}

叙事历史:
{ctx.narrative_block}

效果推演推理: {effect_note.reasoning}
效果: {json.dumps(effect_note.structured.get('effects', []), ensure_ascii=False)}
叙事提示: {effect_note.structured.get('narrative_hints', '')}

后果推理: {cons_reasoning}
后果: {json.dumps(cons_structured.get('consequences', []), ensure_ascii=False)}

---
玩家行动: {ctx.player_input}
掷骰: {roll_summary}

请将以上结构化的游戏结果翻译为沉浸式的叙事文本。"""
        return self._call_llm(user_msg)


class LiteNarratorAgent(BaseAgent):
    system_prompt = LITE_NARRATOR_PROMPT
    agent_name = "叙述者(轻量)"

    def execute(
        self,
        player_input: str,
        ctx: AgentContext,
        gatekeeper_reasoning: str,
    ) -> AgentNote:
        user_msg = f"""{ctx.context_block}

叙事历史:
{ctx.narrative_block}

守门人判断: {gatekeeper_reasoning}

玩家输入（叙事性交互，不掷骰）: {player_input}

请生成一段叙事回应，推动场景前进。"""
        return self._call_llm(user_msg)


class QuickNarratorAgent(BaseAgent):
    system_prompt = QUICK_NARRATOR_PROMPT
    agent_name = "叙述者Agent(快速)"

    def execute(
        self,
        intent_note: AgentNote,
        roll_result: RollResult,
        ctx: AgentContext,
        consequence_note: AgentNote | None = None,
    ) -> AgentNote:
        roll_summary = f"{roll_result.dice[0]}+{roll_result.dice[1]}+{roll_result.power}={roll_result.total} ({roll_result.outcome})"

        cons_reasoning = ""
        cons_structured = {}
        if consequence_note:
            cons_reasoning = consequence_note.reasoning
            cons_structured = consequence_note.structured

        user_msg = f"""{ctx.context_block}

叙事历史:
{ctx.narrative_block}

意图: {intent_note.structured.get('action_summary', '')}

后果推理: {cons_reasoning}
后果: {json.dumps(cons_structured.get('consequences', []), ensure_ascii=False)}

---
玩家行动: {ctx.player_input}
掷骰: {roll_summary}

请将掷骰结果翻译为沉浸式的叙事文本。"""
        return self._call_llm(user_msg)
