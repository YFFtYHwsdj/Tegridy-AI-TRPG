import unittest

from src.models import NPC, GameItem
from src.pipeline.managers.item_manager import ItemManager
from src.state.character_state import CharacterState
from src.state.game_state import GameState
from src.state.global_state import GlobalState
from src.state.scene_state import SceneState
from tests.helpers import MockLLMClient


class TestItemManagerItemTransfers(unittest.TestCase):
    def setUp(self):
        self.llm = MockLLMClient()
        self.state = GameState()
        self.state.global_state = GlobalState()
        self.state.scene = SceneState(place_id="loc1")
        self.state.character = CharacterState(name="Kael")
        self.manager = ItemManager(self.state, self.llm)

    def test_pop_item_from_scene(self):
        item = GameItem(item_id="flashlight", name="手电筒")
        self.state.global_state.items["flashlight"] = item
        self.state.scene.active_item_ids.append("flashlight")

        popped = self.manager._pop_item("flashlight", "scene")
        self.assertIsNotNone(popped)
        self.assertEqual(popped.item_id, "flashlight")
        self.assertNotIn("flashlight", self.state.scene.active_item_ids)

    def test_pop_item_returns_none_when_not_found(self):
        result = self.manager._pop_item("nonexistent", "scene")
        self.assertIsNone(result)

    def test_insert_item_to_scene(self):
        item = GameItem(item_id="flashlight", name="手电筒")
        self.manager._insert_item("flashlight", item, "scene")
        self.assertIn("flashlight", self.state.scene.active_item_ids)
        self.assertIn("flashlight", self.state.global_state.items)

    def test_transfer_scene_to_character(self):
        item = GameItem(item_id="flashlight", name="手电筒")
        self.state.global_state.items["flashlight"] = item
        self.state.scene.active_item_ids.append("flashlight")

        self.manager.transfer_item({"item_id": "flashlight", "from": "scene", "to": "character"})

        self.assertNotIn("flashlight", self.state.scene.active_item_ids)
        self.assertIn("flashlight", self.state.character.items_visible)


class TestItemManagerRevelations(unittest.TestCase):
    def setUp(self):
        self.llm = MockLLMClient()
        self.state = GameState()
        self.state.global_state = GlobalState()
        self.state.scene = SceneState(place_id="loc1")
        self.manager = ItemManager(self.state, self.llm)

    def test_reveals_npc_hidden_item(self):
        npc = NPC(npc_id="miko", name="Miko")
        npc.items_hidden["keycard"] = GameItem(item_id="keycard", name="门禁卡")
        self.state.global_state.npcs["miko"] = npc
        self.state.scene.active_npc_ids.append("miko")

        result = self.manager.reveal_item("keycard")
        self.assertTrue(result)
        self.assertNotIn("keycard", npc.items_hidden)
        self.assertIn("keycard", npc.items_visible)

    def test_validate_and_apply_is_idempotent_for_missing_ids(self):
        result = self.manager.reveal_item("nonexistent")
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
