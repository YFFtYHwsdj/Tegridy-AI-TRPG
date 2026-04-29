from __future__ import annotations

import json

from src.agents.base import BaseAgent
from src.agents.prompts import LITE_NARRATOR_PROMPT, NARRATOR_PROMPT, QUICK_NARRATOR_PROMPT
from src.context import AgentContext
from src.models import AgentNote, RollResult

_HIDDEN_NOTICE = """注意：标记为(隐藏)的线索、物品及其详情尚未被玩家角色发现。
叙事中不要直接提及这些信息。如果玩家的行动在逻辑上自然应该触达它们，
通过 revelation_decisions 标记揭示。"""


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

        user_msg = f"""{ctx.assets_block}
{ctx.context_block}

叙事历史:
{ctx.narrative_block}

{_HIDDEN_NOTICE}

效果推演推理: {effect_note.reasoning}
效果: {json.dumps(effect_note.structured.get("effects", []), ensure_ascii=False)}
叙事提示: {effect_note.structured.get("narrative_hints", "")}

后果推理: {cons_reasoning}
后果: {json.dumps(cons_structured.get("consequences", []), ensure_ascii=False)}

---
玩家行动: {ctx.player_input}
掷骰: {roll_summary}

请将以上结构化的游戏结果翻译为沉浸式的叙事文本。
如果玩家的行动在叙事中自然应该触达隐藏线索或物品，在 revelation_decisions 中标记它们。
如果物品在叙事中发生了转移，在 item_transfers 中标记。"""
        return self._call_llm(user_msg)

    def execute_split(
        self,
        sub_results: list[dict],
        ctx: AgentContext,
    ) -> AgentNote:
        """多子行动统一叙事 —— 将多个子行动的解算结果编织为一段连贯叙事。

        复用 NARRATOR_PROMPT 作为 system prompt，仅改变 user message 格式：
        将多组掷骰/效果/后果格式化为带编号的子行动块，追加编织指引。

        Args:
            sub_results: 每个子行动的结果字典列表，每个 dict 包含：
                - summary: 子行动摘要
                - roll_summary: 掷骰结果文本
                - effects_json: 效果 JSON 字符串
                - narrative_hints: 叙事提示
                - consequences_json: 后果 JSON 字符串
            ctx: 当前场景上下文

        Returns:
            包含统一叙事的 AgentNote
        """
        # 将每个子行动的结果格式化为带编号的文本块
        blocks = []
        for i, sub in enumerate(sub_results, 1):
            blocks.append(f"--- 子行动 {i}: {sub['summary']} ---")
            blocks.append(f"掷骰: {sub['roll_summary']}")
            blocks.append(f"效果: {sub['effects_json']}")
            blocks.append(f"叙事提示: {sub['narrative_hints']}")
            blocks.append(f"后果: {sub['consequences_json']}")
            blocks.append("")

        sub_block = "\n".join(blocks)

        user_msg = f"""{ctx.assets_block}

叙事历史:
{ctx.narrative_block}

{_HIDDEN_NOTICE}

{ctx.context_block}

以下是一个复合行动被拆分为多个子行动的解算结果。
请将所有子行动编织为一段连贯的叙事弧线（200-400字），
而非逐个子行动各写一段。子行动之间存在因果和时序关系。

{sub_block}
---
玩家行动: {ctx.player_input}

请将以上所有子行动的结构化结果翻译为一段沉浸式的叙事文本。
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
        gatekeeper_block = f"\n守门人判断: {gatekeeper_reasoning}\n" if gatekeeper_reasoning else ""
        user_msg = f"""{ctx.assets_block}
{ctx.context_block}

叙事历史:
{ctx.narrative_block}

{_HIDDEN_NOTICE}{gatekeeper_block}
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

        user_msg = f"""{ctx.assets_block}
{ctx.context_block}

叙事历史:
{ctx.narrative_block}

{_HIDDEN_NOTICE}

意图: {intent_note.structured.get("action_summary", "")}

后果推理: {cons_reasoning}
后果: {json.dumps(cons_structured.get("consequences", []), ensure_ascii=False)}

---
玩家行动: {ctx.player_input}
掷骰: {roll_summary}

请将掷骰结果翻译为沉浸式的叙事文本。"""
        return self._call_llm(user_msg)
