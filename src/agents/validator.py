from __future__ import annotations

import json

from src.agents.base import BaseAgent
from src.agents.prompts import VALIDATOR_PROMPT
from src.models import AgentNote


class ValidatorAgent(BaseAgent):
    system_prompt = VALIDATOR_PROMPT
    agent_name = "叙事验证Agent"

    def execute(
        self,
        narrator_note: AgentNote,
        hidden_clues: dict,
        hidden_items: dict,
        visible_clues: dict,
        visible_items: dict,
        scene_items_hidden: dict,
        scene_items_visible: dict,
        npcs: dict,
    ) -> AgentNote:
        hidden_clue_summary = (
            ", ".join(f"{cid}({c.name}: {c.description})" for cid, c in hidden_clues.items())
            if hidden_clues
            else "（无隐藏线索）"
        )
        hidden_item_summary = (
            ", ".join(f"{iid}({i.name}: {i.description})" for iid, i in hidden_items.items())
            if hidden_items
            else "（无隐藏物品）"
        )
        scene_hidden_summary = (
            ", ".join(f"{iid}({i.name})" for iid, i in scene_items_hidden.items())
            if scene_items_hidden
            else "（无）"
        )

        visible_clue_summary = (
            ", ".join(f"{cid}({c.name})" for cid, c in visible_clues.items())
            if visible_clues
            else "（无）"
        )
        visible_item_summary = (
            ", ".join(f"{iid}({i.name})" for iid, i in visible_items.items())
            if visible_items
            else "（无）"
        )
        scene_visible_summary = (
            ", ".join(f"{iid}({i.name})" for iid, i in scene_items_visible.items())
            if scene_items_visible
            else "（无）"
        )

        npc_knowledge_parts = []
        for npc in npcs.values():
            known_c = ", ".join(npc.known_clue_ids) if npc.known_clue_ids else "无"
            known_i = ", ".join(npc.known_item_ids) if npc.known_item_ids else "无"
            npc_knowledge_parts.append(
                f"  {npc.name}({npc.npc_id}) — 知道的线索: [{known_c}], 知道的物品: [{known_i}]"
            )
        npc_knowledge_block = "\n".join(npc_knowledge_parts) if npc_knowledge_parts else "（无NPC）"

        revelations = narrator_note.structured.get("revelation_decisions", {})
        transfers = narrator_note.structured.get("item_transfers", [])
        narrative_contains = narrator_note.structured.get("narrative_contains", {})
        narrative_text = narrator_note.structured.get("narrative", "")

        user_msg = f"""=== 需要验证的叙事 ===
{narrative_text}

=== Narrator 的结构化决策 ===
揭示决策: {json.dumps(revelations, ensure_ascii=False)}
物品转移: {json.dumps(transfers, ensure_ascii=False)}
叙事内容提及: {json.dumps(narrative_contains, ensure_ascii=False)}

=== 场景隐藏信息（不应该在叙事中泄露） ===
隐藏线索: {hidden_clue_summary}
NPC身上隐藏物品: {hidden_item_summary}
场景隐藏物品: {scene_hidden_summary}

=== 已揭示信息（叙事不能与之矛盾） ===
已发现线索: {visible_clue_summary}
角色身上物品: {visible_item_summary}
场景可见物品: {scene_visible_summary}

=== NPC 知识范围 ===
{npc_knowledge_block}

---
请逐项检查。先列出检查结果，再给出最终裁决。"""
        return self._call_llm(user_msg)
