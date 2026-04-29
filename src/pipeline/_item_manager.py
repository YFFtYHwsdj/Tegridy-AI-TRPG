"""物品与揭示管理器 —— 叙事生效引擎。

本模块从 MovePipeline 中提取出来，负责将叙述者 Agent 的输出
（揭示决策、物品转移）应用到游戏状态。这是流水线的最后一个阶段，
独立管理可降低 MovePipeline 的认知负荷并提升可测试性。

职责：
    - 线索/物品揭示（从 hidden 字典移动到 visible 字典）
    - 物品位置转移（场景 ↔ 角色 ↔ NPC）
    - emergent 物品创建（LLM 即兴引入的新物品自动生成数据）
"""

from __future__ import annotations

from src.llm_client import LLMClient
from src.logger import log_system
from src.state.game_state import GameState


class ItemManager:
    """物品与揭示管理器。

    处理叙述者产出的结构化决策，将其转换为游戏状态的变更。
    不依赖流水线的其他阶段（Tag 匹配、效果推演等），
    仅依赖 LLMClient（用于 emergent 物品创建）和 GameState。
    """

    def __init__(self, state: GameState, llm: LLMClient):
        self.state = state
        self.llm = llm

    def validate_and_apply(self, narrator_note, ctx=None):
        """应用叙事输出中的揭示和物品转移。

        MovePipeline 的入口委托方法，保持与原有接口兼容。

        Args:
            narrator_note: 叙述者 Agent 的分析便签
            ctx: 当前场景上下文（用于 emergent 物品创建）
        """
        self.apply_revelations(narrator_note.structured)
        self.apply_item_transfers(narrator_note.structured, ctx)

    def apply_revelations(self, structured: dict):
        """执行最终决策中的揭示操作。

        从 structured dict 的 revelation_decisions 中提取揭示指令，
        将隐藏的线索/物品从隐藏字典转移到可见字典。

        Args:
            structured: 包含 revelation_decisions 的 dict
        """
        scene = self.state.scene
        decisions = structured.get("revelation_decisions", {})

        for clue_id in decisions.get("reveal_clue_ids", []):
            if clue_id in scene.clues_hidden:
                clue = scene.clues_hidden.pop(clue_id)
                scene.clues_visible[clue_id] = clue

        for item_id in decisions.get("reveal_item_ids", []):
            found = False
            if item_id in scene.scene_items_hidden:
                item = scene.scene_items_hidden.pop(item_id)
                scene.scene_items_visible[item_id] = item
                found = True
            else:
                for npc in scene.npcs.values():
                    if item_id in npc.items_hidden:
                        item = npc.items_hidden.pop(item_id)
                        npc.items_visible[item_id] = item
                        found = True
                        break
            if not found:
                log_system(f"未找到物品 '{item_id}'", level="warning")

    def apply_item_transfers(self, structured: dict, ctx=None):
        """执行最终决策中的物品转移。

        处理物品在不同位置之间的移动（场景 ↔ 角色 ↔ NPC），
        支持自动创建 emergent 物品（叙述者即兴引入的新物品）。

        Args:
            structured: 包含 item_transfers 的 dict
            ctx: 当前场景上下文（用于 emergent 物品创建）
        """
        _scene = self.state.scene
        transfers = structured.get("item_transfers", [])
        location_updates = structured.get("location_text_updates", [])

        loc_map = {u["item_id"]: u["new_location"] for u in location_updates if isinstance(u, dict)}

        for t in transfers:
            if not isinstance(t, dict):
                continue
            item_id = t.get("item_id") or t.get("item", "")
            from_loc = t.get("from", "")
            to_loc = t.get("to", "")
            if not item_id or not from_loc or not to_loc:
                continue

            item = self.pop_item(item_id, from_loc)
            if item is None:
                created = self.create_emergent_item(item_id, ctx)
                if not created:
                    log_system(f"未找到且无法创建 '{item_id}' (from={from_loc})", level="warning")
                    continue
                item = created
                log_system(f"转移时自动创建 '{item_id}'", level="debug")

            if item_id in loc_map:
                item.location = loc_map[item_id]

            self.insert_item(item_id, item, to_loc)

    def create_emergent_item(self, item_name: str, ctx=None):
        """创建 emergent 物品 —— 叙述者即兴引入的新物品。

        LLM 叙述者可能在叙事中引入原数据中不存在的物品。
        此时调用 ItemCreator Agent 根据上下文自动生成物品数据。

        Args:
            item_name: 物品名称
            ctx: 当前场景上下文（用于 ItemCreatorAgent）

        Returns:
            新创建的 GameItem 对象，创建失败返回 None
        """
        from src.agents.item_creator import ItemCreatorAgent

        if not hasattr(self, "item_creator"):
            self.item_creator = ItemCreatorAgent(self.llm)

        creator_note = self.item_creator.execute(item_name, ctx)
        item_data = creator_note.structured
        if not item_data:
            return None

        from src.models import GameItem, Tag

        tags = []
        for t in item_data.get("tags", []):
            if isinstance(t, dict):
                tags.append(
                    Tag(
                        name=t.get("name", ""),
                        tag_type=t.get("tag_type", "power"),
                        description=t.get("description", ""),
                    )
                )
            elif isinstance(t, str):
                tags.append(Tag(name=t, tag_type="power"))

        weakness = None
        w = item_data.get("weakness")
        if w and isinstance(w, dict):
            weakness = Tag(
                name=w.get("name", ""),
                tag_type="weakness",
                description=w.get("description", ""),
            )

        item_id = item_data.get("item_id") or item_name
        return GameItem(
            item_id=item_id,
            name=item_name,
            description=item_data.get("description", ""),
            tags=tags,
            weakness=weakness,
            location=item_data.get("location", ""),
        )

    def pop_item(self, item_id: str, location: str):
        """从指定位置取出物品（从可见或隐藏字典中移除）。

        支持的位置格式：
            - "scene": 场景物品
            - "character": 角色物品
            - "npc.<npc_id>": 指定 NPC 的物品

        Args:
            item_id: 物品 ID
            location: 位置标识符

        Returns:
            取出的物品对象，未找到返回 None
        """
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

    def insert_item(self, item_id: str, item, location: str):
        """将物品插入到指定位置的可见字典。

        支持的位置格式同 pop_item。

        Args:
            item_id: 物品 ID
            item: 物品对象
            location: 目标位置标识符
        """
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
