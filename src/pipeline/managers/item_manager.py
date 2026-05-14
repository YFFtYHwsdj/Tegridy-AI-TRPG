"""物品管理器 —— 负责物品的位置转移和生成。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.logger import log_system

if TYPE_CHECKING:
    from src.context import AgentContext
    from src.llm_client import LLMClient
    from src.state.game_state import GameState


class ItemManager:
    """管理场景、NPC和角色之间的物品转移与揭示。"""

    def __init__(self, state: GameState, llm: LLMClient):
        self.state = state
        self.llm = llm

    def reveal_item(self, item_id: str) -> bool:
        """将隐藏物品揭示为可见物品。

        Args:
            item_id: 物品ID

        Returns:
            bool: 是否成功找到并揭示
        """
        scene = self.state.scene
        if item_id in scene.scene_items_hidden:
            item = scene.scene_items_hidden.pop(item_id)
            scene.scene_items_visible[item_id] = item
            return True

        for npc in scene.npcs.values():
            if item_id in npc.items_hidden:
                item = npc.items_hidden.pop(item_id)
                npc.items_visible[item_id] = item
                return True

        log_system(f"未找到物品 '{item_id}'", level="warning")
        return False

    def transfer_item(self, transfer_data: dict, ctx: AgentContext | None = None):
        """处理物品在不同位置之间的物理转移。

        Args:
            transfer_data: 包含 item_id, from, to 的字典
            ctx: 当前场景上下文（用于 emergent 物品创建）
        """
        item_id = transfer_data.get("item_id") or transfer_data.get("item", "")
        from_loc = transfer_data.get("from", "")
        to_loc = transfer_data.get("to", "")
        if not item_id or not from_loc or not to_loc:
            return

        item = self._pop_item(item_id, from_loc)
        if item is None:
            created = self.create_emergent_item(item_id, ctx)
            if not created:
                log_system(f"未找到且无法创建 '{item_id}' (from={from_loc})", level="warning")
                return
            item = created
            log_system(f"转移时自动创建 '{item_id}'", level="debug")

        self._insert_item(item_id, item, to_loc)

    def update_item_location_text(self, item_id: str, new_location: str):
        """更新物品的自然语言位置描述。

        仅修改文字描述，不进行物理转移字典操作。如果物品在当前场景可见物品或角色物品中，
        更新其 location 字段。

        Args:
            item_id: 物品ID
            new_location: 新的位置描述文本
        """
        item = self._find_visible_item(item_id)
        if item:
            item.location = new_location

    def _find_visible_item(self, item_id: str):
        """在可见字典中查找物品。"""
        scene = self.state.scene
        if item_id in scene.scene_items_visible:
            return scene.scene_items_visible[item_id]
        if self.state.character and item_id in self.state.character.items_visible:
            return self.state.character.items_visible[item_id]
        for npc in scene.npcs.values():
            if item_id in npc.items_visible:
                return npc.items_visible[item_id]
        return None

    def create_emergent_item(self, item_name: str, ctx: AgentContext | None = None):
        """调用 LLM 生成叙述者即兴引入的新物品数据。"""
        from src.agents.item_creator import ItemCreatorAgent
        from src.models import GameItem, PowerTag, WeaknessTag

        if ctx is None:
            return None

        if not hasattr(self, "item_creator"):
            self.item_creator = ItemCreatorAgent(self.llm)

        creator_note = self.item_creator.execute(item_name, ctx)
        item_data = creator_note.structured
        if not item_data:
            return None

        tags = []
        for t in item_data.get("tags", []):
            if isinstance(t, dict):
                tags.append(PowerTag(name=t.get("name", ""), description=t.get("description", "")))
            elif isinstance(t, str):
                tags.append(PowerTag(name=t))

        weakness_tags: list[WeaknessTag] = []
        w_tags_raw = item_data.get("weakness_tags")
        if w_tags_raw and isinstance(w_tags_raw, list):
            for w_extra in w_tags_raw:
                if isinstance(w_extra, dict):
                    weakness_tags.append(
                        WeaknessTag(
                            name=w_extra.get("name", ""), description=w_extra.get("description", "")
                        )
                    )
        elif not w_tags_raw:
            w = item_data.get("weakness")
            if w and isinstance(w, dict):
                weakness_tags.append(
                    WeaknessTag(name=w.get("name", ""), description=w.get("description", ""))
                )

        seen = set()
        deduped = []
        for wt in weakness_tags:
            if wt.name and wt.name not in seen:
                seen.add(wt.name)
                deduped.append(wt)
        weakness_tags = deduped

        item_id = item_data.get("item_id") or item_name
        return GameItem(
            item_id=item_id,
            name=item_name,
            description=item_data.get("description", ""),
            tags=tags,
            weakness_tags=weakness_tags,
            location=item_data.get("location", ""),
        )

    def _pop_item(self, item_id: str, location: str):
        scene = self.state.scene
        if location == "scene":
            for d in (scene.scene_items_visible, scene.scene_items_hidden):
                if item_id in d:
                    return d.pop(item_id)
        elif location == "character":
            char = self.state.character
            if char:
                for d in (char.items_visible, char.items_hidden):
                    if item_id in d:
                        return d.pop(item_id)
        elif location.startswith("npc."):
            npc_id = location[4:]
            npc = scene.npcs.get(npc_id)
            if npc:
                for d in (npc.items_visible, npc.items_hidden):
                    if item_id in d:
                        return d.pop(item_id)
        return None

    def _insert_item(self, item_id: str, item, location: str):
        scene = self.state.scene
        if location == "scene":
            scene.scene_items_visible[item_id] = item
        elif location == "character":
            if self.state.character:
                self.state.character.items_visible[item_id] = item
        elif location.startswith("npc."):
            npc_id = location[4:]
            npc = scene.npcs.get(npc_id)
            if npc:
                npc.items_visible[item_id] = item
