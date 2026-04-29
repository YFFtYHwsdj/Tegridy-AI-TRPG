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
from src.formatter import format_statuses
from src.models import (
    NPC,
    AgentNote,
    Challenge,
    Character,
    Clue,
    GameItem,
    Limit,
    PowerTag,
)
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
        character: Character | None,
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
            power_names = ", ".join(t.name for t in character.power_tags)
            weakness_names = ", ".join(t.name for t in character.weakness_tags)
            status_text = format_statuses(character.statuses)
            story_tag_names = ", ".join(character.story_tags.keys())
            char_block = (
                f"当前角色: {character.name}\n"
                f"角色描述: {character.description}\n"
                f"力量标签: {power_names}\n"
                f"弱点标签: {weakness_names}\n"
                f"当前状态: {status_text}\n"
                f"故事标签: {story_tag_names if story_tag_names else '（无）'}"
            )

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
        - Limit 的 max_tier 强制钳制在 1-6 范围内

    Args:
        creator_output: SceneCreatorAgent.structured 字典

    Returns:
        完整的 SceneState 对象（即使 LLM 输出不完整也不会崩溃）
    """
    from src.logger import get_logger

    _log = get_logger()

    scene = SceneState(scene_description=str(creator_output.get("scene_description", "")).strip())

    # --- Challenge ---
    chal_data = creator_output.get("challenge")
    if isinstance(chal_data, dict):
        chal_name = str(chal_data.get("name", "未知挑战"))
        chal_desc = str(chal_data.get("description", ""))
        chal_notes = str(chal_data.get("notes", ""))

        limits = []
        raw_limits = chal_data.get("limits")
        if isinstance(raw_limits, list):
            for lim in raw_limits:
                if isinstance(lim, dict):
                    lim_name = str(lim.get("name", ""))
                    lim_tier = lim.get("max_tier", 3)
                    if isinstance(lim_tier, (int, float)):
                        lim_tier = max(1, min(6, int(lim_tier)))
                    else:
                        lim_tier = 3
                    if lim_name:
                        limits.append(Limit(name=lim_name, max_tier=lim_tier))

        base_tags = []
        raw_tags = chal_data.get("base_tags")
        if isinstance(raw_tags, list):
            for tag in raw_tags:
                if isinstance(tag, dict):
                    tag_name = str(tag.get("name", ""))
                    tag_desc = str(tag.get("description", ""))
                    if tag_name:
                        base_tags.append(PowerTag(name=tag_name, description=tag_desc))

        challenge = Challenge(
            name=chal_name,
            description=chal_desc,
            limits=limits,
            base_tags=base_tags,
            notes=chal_notes,
        )
        scene.add_challenge(challenge)
    else:
        _log.warning("SceneCreator 输出缺少 challenge 字段或格式不正确")

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
