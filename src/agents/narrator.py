from __future__ import annotations

import json
from src.agents.base import BaseAgent
from src.agents.prompts import NARRATOR_PROMPT, LITE_NARRATOR_PROMPT, QUICK_NARRATOR_PROMPT
from src.context import AgentContext
from src.models import AgentNote, RollResult


def _build_hidden_context(ctx: AgentContext) -> str:
    scene = ctx.extra.get("scene_state")
    if scene is None:
        return ""
    parts = []
    hidden_clues = getattr(scene, "clues_hidden", {})
    hidden_items = getattr(scene, "scene_items_hidden", {})
    if hidden_clues:
        clue_list = ", ".join(
            f"{cid}({c.name})" for cid, c in hidden_clues.items()
        )
        parts.append(f"隐藏线索: {clue_list}")
    if hidden_items:
        item_list = ", ".join(
            f"{iid}({i.name})" for iid, i in hidden_items.items()
        )
        parts.append(f"隐藏物品: {item_list}")
    npcs = getattr(scene, "npcs", {})
    for npc in npcs.values():
        if npc.items_hidden:
            item_list = ", ".join(
                f"{iid}({i.name})" for iid, i in npc.items_hidden.items()
            )
            parts.append(f"{npc.name}身上隐藏的物品: {item_list}")
    return "\n".join(parts) if parts else ""


def _build_revealed_context(ctx: AgentContext) -> str:
    scene = ctx.extra.get("scene_state")
    if scene is None:
        return ""
    parts = []
    discovered = getattr(scene, "clues_visible", {})
    found_items = getattr(scene, "scene_items_visible", {})
    char = ctx.character
    char_items = {}
    if char:
        char_items = getattr(char, "items_visible", {})
    if discovered:
        clue_list = ", ".join(
            f"{cid}({c.name})" for cid, c in discovered.items()
        )
        parts.append(f"已发现线索: {clue_list}")
    if found_items:
        item_list = ", ".join(
            f"{iid}({i.name})" for iid, i in found_items.items()
        )
        parts.append(f"场景中已找到物品: {item_list}")
    if char_items:
        item_list = ", ".join(
            f"{iid}({i.name})" for iid, i in char_items.items()
        )
        parts.append(f"角色身上物品: {item_list}")
    return "\n".join(parts) if parts else ""


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

        hidden_block = _build_hidden_context(ctx)
        revealed_block = _build_revealed_context(ctx)

        user_msg = f"""{ctx.context_block}

叙事历史:
{ctx.narrative_block}

{hidden_block}

{revealed_block}

效果推演推理: {effect_note.reasoning}
效果: {json.dumps(effect_note.structured.get('effects', []), ensure_ascii=False)}
叙事提示: {effect_note.structured.get('narrative_hints', '')}

后果推理: {cons_reasoning}
后果: {json.dumps(cons_structured.get('consequences', []), ensure_ascii=False)}

---
玩家行动: {ctx.player_input}
掷骰: {roll_summary}

请将以上结构化的游戏结果翻译为沉浸式的叙事文本。
如果玩家的行动在叙事中自然应该触达隐藏线索或物品，在 revelation_decisions 中标记它们。
如果物品在叙事中发生了转移，在 item_transfers 中标记。"""
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
        hidden_block = _build_hidden_context(ctx)
        revealed_block = _build_revealed_context(ctx)

        user_msg = f"""{ctx.context_block}

叙事历史:
{ctx.narrative_block}

{hidden_block}

{revealed_block}

守门人判断: {gatekeeper_reasoning}

玩家输入（叙事性交互，不掷骰）: {player_input}

请生成一段叙事回应，推动场景前进。
低风险的观察或对话不应揭示关键隐藏信息。"""
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

        hidden_block = _build_hidden_context(ctx)
        revealed_block = _build_revealed_context(ctx)

        user_msg = f"""{ctx.context_block}

叙事历史:
{ctx.narrative_block}

{hidden_block}

{revealed_block}

意图: {intent_note.structured.get('action_summary', '')}

后果推理: {cons_reasoning}
后果: {json.dumps(cons_structured.get('consequences', []), ensure_ascii=False)}

---
玩家行动: {ctx.player_input}
掷骰: {roll_summary}

请将掷骰结果翻译为沉浸式的叙事文本。"""
        return self._call_llm(user_msg)
