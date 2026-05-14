"""ItemManager 测试 —— 揭示应用、物品转移、emergent 物品创建。

验证 ItemManager 的核心行为：
    - 线索从 hidden 移动到 visible
    - 场景/NPC 隐藏物品揭示
    - 物品在不同位置之间的转移
"""

from __future__ import annotations

import unittest

from src.models import GameItem
from src.pipeline.managers import ItemManager
from tests.helpers import (
    MockLLMClient,
    make_test_game_state,
)


class TestItemManagerRevelations(unittest.TestCase):
    """测试物品揭示。"""

    def _make_manager(self, state) -> ItemManager:
        """创建 ItemManager 实例。"""
        mock_llm = MockLLMClient()
        return ItemManager(state, mock_llm)

    def test_reveals_scene_item(self):
        """物品从 scene_items_hidden 移动到 visible。"""
        state = make_test_game_state()
        manager = self._make_manager(state)

        state.scene.scene_items_hidden["medkit"] = GameItem(item_id="medkit", name="急救包")

        result = manager.reveal_item("medkit")
        self.assertTrue(result)

        self.assertNotIn("medkit", state.scene.scene_items_hidden)
        self.assertIn("medkit", state.scene.scene_items_visible)

    def test_reveals_npc_hidden_item(self):
        """NPC 隐藏物品移动到可见。"""
        state = make_test_game_state()
        manager = self._make_manager(state)

        from src.models import NPC

        npc = NPC(npc_id="miko", name="Miko")
        npc.items_hidden["key"] = GameItem(item_id="key", name="钥匙")
        state.scene.npcs["miko"] = npc

        result = manager.reveal_item("key")
        self.assertTrue(result)

        self.assertNotIn("key", npc.items_hidden)
        self.assertIn("key", npc.items_visible)

    def test_validate_and_apply_is_idempotent_for_missing_ids(self):
        """对不存在的揭示 ID 不会崩溃。"""
        state = make_test_game_state()
        manager = self._make_manager(state)

        result = manager.reveal_item("nonexistent")
        self.assertFalse(result)


class TestItemManagerItemTransfers(unittest.TestCase):
    """测试物品转移方法。"""

    def _make_manager(self, state) -> ItemManager:
        """创建 ItemManager 实例。"""
        mock_llm = MockLLMClient()
        return ItemManager(state, mock_llm)

    def test_pop_item_from_scene(self):
        """从场景中取出物品。"""
        state = make_test_game_state()
        manager = self._make_manager(state)

        item = GameItem(item_id="flashlight", name="手电筒")
        state.scene.scene_items_visible["flashlight"] = item

        result = manager._pop_item("flashlight", "scene")

        self.assertIs(result, item)
        self.assertNotIn("flashlight", state.scene.scene_items_visible)

    def test_pop_item_from_character(self):
        """从角色物品栏中取出物品。"""
        state = make_test_game_state()
        manager = self._make_manager(state)

        item = GameItem(item_id="badge", name="警徽")
        state.character.items_visible["badge"] = item

        result = manager._pop_item("badge", "character")

        self.assertIs(result, item)
        self.assertNotIn("badge", state.character.items_visible)

    def test_pop_item_returns_none_when_not_found(self):
        """物品不存在时返回 None。"""
        state = make_test_game_state()
        manager = self._make_manager(state)

        result = manager._pop_item("nonexistent", "scene")

        self.assertIsNone(result)

    def test_insert_item_to_scene(self):
        """将物品插入到场景。"""
        state = make_test_game_state()
        manager = self._make_manager(state)

        item = GameItem(item_id="flashlight", name="手电筒")
        manager._insert_item("flashlight", item, "scene")

        self.assertIn("flashlight", state.scene.scene_items_visible)
        self.assertIs(state.scene.scene_items_visible["flashlight"], item)

    def test_insert_item_to_character(self):
        """将物品插入到角色物品栏。"""
        state = make_test_game_state()
        manager = self._make_manager(state)

        item = GameItem(item_id="badge", name="警徽")
        manager._insert_item("badge", item, "character")

        self.assertIn("badge", state.character.items_visible)
        self.assertIs(state.character.items_visible["badge"], item)

    def test_transfer_scene_to_character(self):
        """物品从场景转移到角色。"""
        state = make_test_game_state()
        manager = self._make_manager(state)

        item = GameItem(item_id="flashlight", name="手电筒")
        state.scene.scene_items_visible["flashlight"] = item

        manager.transfer_item({"item_id": "flashlight", "from": "scene", "to": "character"})

        self.assertNotIn("flashlight", state.scene.scene_items_visible)
        self.assertIn("flashlight", state.character.items_visible)

    def test_transfer_from_hidden_source(self):
        """从隐藏位置取出物品并转移。"""
        state = make_test_game_state()
        manager = self._make_manager(state)

        item = GameItem(item_id="secret_doc", name="秘密文件")
        state.scene.scene_items_hidden["secret_doc"] = item

        manager.transfer_item({"item_id": "secret_doc", "from": "scene", "to": "character"})

        self.assertNotIn("secret_doc", state.scene.scene_items_hidden)
        self.assertIn("secret_doc", state.character.items_visible)


if __name__ == "__main__":
    unittest.main()
