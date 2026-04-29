from __future__ import annotations

import json

from src.agents.base import BaseAgent
from src.agents.prompts import VALIDATOR_PROMPT
from src.models import AgentNote


class ValidatorAgent(BaseAgent):
    """叙事校验与修正器 —— 审查叙述者提议并输出最终的揭示和转移决策。

    角色定位：叙述者的 STRUCTURED 只是提议，Validator 是最终决策者。
    检查泄露、矛盾、揭示完整性和转移完整性，输出直接可执行的
    revelation_decisions 和 item_transfers。
    """

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
        """校验叙述者输出并返回最终的揭示和转移决策。

        收集场景状态信息（隐藏/可见线索物品、NPC 知识范围），
        拼装为结构化 user_msg 交给 LLM 校验。

        Args:
            narrator_note: 叙述者 Agent 的分析便签
            hidden_clues: 所有隐藏线索 {clue_id: Clue}
            hidden_items: NPC 身上所有隐藏物品 {item_id: GameItem}
            visible_clues: 已揭示线索 {clue_id: Clue}
            visible_items: 角色身上可见物品 {item_id: GameItem}
            scene_items_hidden: 场景隐藏物品 {item_id: GameItem}
            scene_items_visible: 场景可见物品 {item_id: GameItem}
            npcs: 场景中所有 NPC {npc_id: NPC}

        Returns:
            AgentNote: 包含最终 revelation_decisions 和 item_transfers 的便签
        """
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
        narrative_text = narrator_note.structured.get("narrative", "")

        user_msg = f"""=== 需要校验的叙事 ===
{narrative_text}

=== Narrator 的提议（供参考） ===
提议揭示: {json.dumps(revelations, ensure_ascii=False)}
提议物品转移: {json.dumps(transfers, ensure_ascii=False)}

=== 场景隐藏信息 ===
隐藏线索: {hidden_clue_summary}
NPC身上隐藏物品: {hidden_item_summary}
场景隐藏物品: {scene_hidden_summary}

=== 已揭示信息（叙事不能与之矛盾） ===
已发现线索: {visible_clue_summary}
角色身上物品: {visible_item_summary}
场景可见物品: {scene_visible_summary}

=== NPC 知识范围（用于判断泄露：NPC 有权说的不算泄露） ===
{npc_knowledge_block}

---
请校验以上叙事文本，输出最终的 revelation_decisions 和 item_transfers。"""
        return self._call_llm(user_msg)
