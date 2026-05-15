"""世界演化推演与图边融合引擎。

负责在场景结束后，阅读完整叙事历史并更新 GlobalState。
包含 WorldAnalyzerAgent (提议关系和重写笔记) 和
EdgeMergeAgent (处理图边碰撞与融合)。
"""

from __future__ import annotations

from src.agents.base import BaseAgent
from src.agents.prompts.world_updater import EDGE_MERGE_PROMPT, WORLD_ANALYZER_PROMPT
from src.context import MessageBuilder
from src.models import AgentNote
from src.state.global_state import GlobalState
from src.state.scene_state import SceneState


class WorldAnalyzerAgent(BaseAgent):
    """世界演化推演者。"""

    system_prompt = WORLD_ANALYZER_PROMPT
    agent_name = "世界推演者Agent"

    def execute(self, scene: SceneState, global_state: GlobalState) -> AgentNote:
        context_block = global_state.build_graph_context(
            scene.place_id, scene.active_npc_ids, scene.active_item_ids
        )
        narrative_block = "\n".join(scene.narrative_history)

        builder = MessageBuilder()
        builder.add_block("当前场景图上下文", context_block, wrap_title=True)
        builder.add_block("刚刚结束的场景叙事", narrative_block, wrap_title=True)
        return self._call_llm(builder.build())


class EdgeMergeAgent(BaseAgent):
    """图边融合者。"""

    system_prompt = EDGE_MERGE_PROMPT
    agent_name = "图边融合者Agent"

    def execute(
        self,
        entity_a_id: str,
        entity_a_desc: str,
        entity_b_id: str,
        entity_b_desc: str,
        relations: list[str],
    ) -> AgentNote:
        rels_text = "\n".join(f"- {r}" for r in relations)

        builder = MessageBuilder()
        builder.add_block("实体 A", f"ID: {entity_a_id}\n描述: {entity_a_desc}", wrap_title=True)
        builder.add_block("实体 B", f"ID: {entity_b_id}\n描述: {entity_b_desc}", wrap_title=True)
        builder.add_block("待合并的关系", rels_text, wrap_title=True)

        return self._call_llm(builder.build())
