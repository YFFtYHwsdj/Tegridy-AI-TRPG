"""场景创作 Agent —— 根据前情创建下一个场景。

SceneCreatorAgent 在场景过渡流水线的最后一步被调用。
它接收跨场景历史、角色信息和过渡提示，调用 LLM 生成
下一个场景的完整设定（描述、挑战、NPC、物品、线索）。

同时提供 build_scene_from_creator() 工具函数，
将 LLM 的 JSON 输出安全地转换为强类型 SceneState 对象。
"""

from __future__ import annotations

from src.agents.base import BaseAgent
from src.agents.prompts import SCENE_CREATOR_PROMPT
from src.models import (
    NPC,
    AgentNote,
    Clue,
    GameItem,
    PowerTag,
)
from src.state.character_state import CharacterState
from src.state.scene_state import SceneState


class SceneCreatorAgent(BaseAgent):
    """场景创作者 —— 根据前情生成下一个场景。

    execute() 接收跨场景历史块、角色信息和过渡提示，
    返回包含完整场景定义的 AgentNote。
    调用方使用 build_scene_from_creator() 将结构化输出转为 SceneState。
    """

    system_prompt = SCENE_CREATOR_PROMPT
    agent_name = "场景创作者Agent"

    def execute(
        self,
        global_block: str,
        character: CharacterState | None,
        transition_hint: str = "",
    ) -> AgentNote:
        """创建下一个场景。

        Args:
            global_block: GlobalState.build_block() 产出的跨场景历史块
            character: 玩家角色（提取标签和状态信息供 LLM 参考）
            transition_hint: SceneDirector 产出的过渡提示

        Returns:
            AgentNote，structured 包含 scene_description、challenge、
            npcs、items_visible、items_hidden、clues_hidden
        """
        char_block = ""
        if character is not None:
            char_block = character.build_context_block(include_tracks=False)

        hint_block = ""
        if transition_hint:
            hint_block = f"过渡提示: {transition_hint}"

        user_msg = f"""{global_block}

{char_block}

{hint_block}

---
请根据以上前情创建下一个场景。"""
        return self._call_llm(user_msg)


def build_scene_from_creator(creator_output: dict) -> SceneState:
    """将 SceneCreatorAgent 的 JSON 输出转换为 SceneState 对象。

    对所有 LLM 产出的字段做防御性校验：
        - 缺失字段用默认值填充
        - 类型不匹配时跳过并记录告警

    Args:
        creator_output: SceneCreatorAgent.structured 字典

    Returns:
        完整的 SceneState 对象（即使 LLM 输出不完整也不会崩溃）
    """
    from src.logger import get_logger

    _log = get_logger()

    scene = SceneState(scene_description=str(creator_output.get("scene_description", "")).strip())

    # --- NPCs ---
    raw_npcs = creator_output.get("npcs")
    if isinstance(raw_npcs, list):
        for npc_data in raw_npcs:
            if not isinstance(npc_data, dict):
                continue
            npc_id = str(npc_data.get("npc_id", ""))
            npc_name = str(npc_data.get("name", ""))
            if not npc_id or not npc_name:
                continue

            npc_desc = str(npc_data.get("description", ""))

            tags = []
            raw_npc_tags = npc_data.get("tags")
            if isinstance(raw_npc_tags, list):
                for t in raw_npc_tags:
                    if isinstance(t, dict):
                        tags.append(
                            PowerTag(
                                name=str(t.get("name", "")),
                                description=str(t.get("description", "")),
                            )
                        )

            items_visible: dict[str, GameItem] = {}
            raw_vis = npc_data.get("items_visible")
            if isinstance(raw_vis, list):
                for item_data in raw_vis:
                    if isinstance(item_data, dict):
                        item_id = str(item_data.get("item_id", ""))
                        if item_id:
                            items_visible[item_id] = GameItem(
                                item_id=item_id,
                                name=str(item_data.get("name", "")),
                                description=str(item_data.get("description", "")),
                                location=str(item_data.get("location", "")),
                            )

            items_hidden: dict[str, GameItem] = {}
            raw_hid = npc_data.get("items_hidden")
            if isinstance(raw_hid, list):
                for item_data in raw_hid:
                    if isinstance(item_data, dict):
                        item_id = str(item_data.get("item_id", ""))
                        if item_id:
                            items_hidden[item_id] = GameItem(
                                item_id=item_id,
                                name=str(item_data.get("name", "")),
                                description=str(item_data.get("description", "")),
                                location=str(item_data.get("location", "")),
                            )

            known_clue_ids = npc_data.get("known_clue_ids")
            if not isinstance(known_clue_ids, list):
                known_clue_ids = []
            known_clue_ids = [str(c) for c in known_clue_ids]

            known_item_ids = npc_data.get("known_item_ids")
            if not isinstance(known_item_ids, list):
                known_item_ids = []
            known_item_ids = [str(i) for i in known_item_ids]

            npc = NPC(
                npc_id=npc_id,
                name=npc_name,
                description=npc_desc,
                tags=tags,
                items_visible=items_visible,
                items_hidden=items_hidden,
                known_clue_ids=known_clue_ids,
                known_item_ids=known_item_ids,
            )
            scene.npcs[npc_id] = npc

    # --- Items ---
    for key, target_dict in [
        ("items_visible", scene.scene_items_visible),
        ("items_hidden", scene.scene_items_hidden),
    ]:
        raw = creator_output.get(key)
        if isinstance(raw, list):
            for item_data in raw:
                if isinstance(item_data, dict):
                    item_id = str(item_data.get("item_id", ""))
                    if item_id:
                        target_dict[item_id] = GameItem(
                            item_id=item_id,
                            name=str(item_data.get("name", "")),
                            description=str(item_data.get("description", "")),
                            location=str(item_data.get("location", "")),
                        )

    # --- Clues ---
    raw_clues = creator_output.get("clues_hidden")
    if isinstance(raw_clues, list):
        for clue_data in raw_clues:
            if isinstance(clue_data, dict):
                clue_id = str(clue_data.get("clue_id", ""))
                if clue_id:
                    scene.clues_hidden[clue_id] = Clue(
                        clue_id=clue_id,
                        name=str(clue_data.get("name", "")),
                        description=str(clue_data.get("description", "")),
                    )

    return scene
