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


class TestItemManagerLocations(unittest.TestCase):
    def setUp(self):
        from src.pipeline.managers.item_manager import ItemManager
        from tests.helpers import MockLLMClient

        self.llm = MockLLMClient()
        self.state = GameState()
        self.state.global_state = GlobalState()
        self.state.scene = SceneState(place_id="loc1")
        self.state.character = CharacterState(name="Hero")
        self.manager = ItemManager(self.state, self.llm)

    def test_update_item_location_text(self):
        from src.models import GameItem

        item = GameItem(item_id="flashlight", name="手电筒", location="地上")
        self.state.global_state.items["flashlight"] = item
        self.state.scene.active_item_ids.append("flashlight")
        self.manager.update_item_location_text("flashlight", "桌子上")
        self.assertEqual(item.location, "桌子上")

    def test_pop_insert_character_item(self):
        from src.models import GameItem

        item = GameItem(item_id="gun", name="枪")
        self.manager._insert_item("gun", item, "character")
        self.assertIn("gun", self.state.character.items_visible)

        popped = self.manager._pop_item("gun", "character")
        self.assertEqual(popped.name, "枪")
        self.assertNotIn("gun", self.state.character.items_visible)

    def test_pop_insert_npc_item(self):
        from src.models import NPC, GameItem

        npc = NPC(npc_id="miko", name="Miko")
        self.state.global_state.npcs["miko"] = npc
        self.state.scene.active_npc_ids.append("miko")

        item = GameItem(item_id="key", name="钥匙")
        self.manager._insert_item("key", item, "npc.miko")
        self.assertIn("key", npc.items_visible)

        popped = self.manager._pop_item("key", "npc.miko")
        self.assertEqual(popped.name, "钥匙")
        self.assertNotIn("key", npc.items_visible)


class TestItemManagerEmergent(unittest.TestCase):
    def setUp(self):
        from src.pipeline.managers.item_manager import ItemManager
        from tests.helpers import MockLLMClient

        self.llm = MockLLMClient()
        self.llm.responses.append(
            (
                '{"item_id": "new_gun", "name": "新枪", "tags": ["火力猛"], "weakness_tags": [{"name": "易卡壳"}], "location": "地上"}',
                {},
            )
        )
        self.state = GameState()
        self.state.global_state = GlobalState()
        self.state.scene = SceneState(place_id="loc1")
        self.manager = ItemManager(self.state, self.llm)

    def test_create_emergent_item(self):
        from src.context import AgentContext

        ctx = AgentContext()
        item = self.manager.create_emergent_item("new_gun", ctx)
        self.assertIsNotNone(item)
        self.assertEqual(item.name, "新枪")
        self.assertEqual(item.tags[0].name, "火力猛")
        self.assertEqual(item.weakness_tags[0].name, "易卡壳")
        self.assertEqual(item.location, "地上")

    def test_create_emergent_item_none_ctx(self):
        item = self.manager.create_emergent_item("new_gun", None)
        self.assertIsNone(item)


class TestItemManagerRemainingBranches(unittest.TestCase):
    def setUp(self):
        from src.pipeline.managers.item_manager import ItemManager
        from tests.helpers import MockLLMClient

        self.llm = MockLLMClient()
        self.state = GameState()
        self.state.global_state = GlobalState()
        self.state.scene = SceneState(place_id="loc1")
        self.state.character = CharacterState(name="Hero")
        self.manager = ItemManager(self.state, self.llm)

    def test_reveal_item_already_active(self):
        self.state.scene.active_item_ids.append("item1")
        self.assertTrue(self.manager.reveal_item("item1"))

    def test_reveal_item_in_global_not_active(self):
        from src.models import GameItem

        self.state.global_state.items["item2"] = GameItem(item_id="item2", name="Item 2")
        self.assertTrue(self.manager.reveal_item("item2"))
        self.assertIn("item2", self.state.scene.active_item_ids)

    def test_transfer_item_invalid_data(self):
        self.manager.transfer_item({"item_id": "", "from": "scene", "to": "character"})
        self.manager.transfer_item({"item_id": "i1", "from": "", "to": "character"})
        self.manager.transfer_item({"item_id": "i1", "from": "scene", "to": ""})
        # Should return without doing anything

    def test_transfer_item_creates_emergent(self):
        from src.context import AgentContext

        self.llm.responses.append(
            ('{"item_id": "magic_sword", "name": "魔剑", "tags": [], "weakness_tags": []}', {})
        )
        ctx = AgentContext()
        self.manager.transfer_item(
            {"item_id": "magic_sword", "from": "nowhere", "to": "character"}, ctx=ctx
        )
        self.assertIn("magic_sword", self.state.character.items_visible)

    def test_transfer_item_fails_emergent(self):
        from src.context import AgentContext

        self.llm.responses.append(("{}", {}))  # Empty structured data
        ctx = AgentContext()
        self.manager.transfer_item(
            {"item_id": "magic_sword", "from": "nowhere", "to": "character"}, ctx=ctx
        )
        self.assertNotIn("magic_sword", self.state.character.items_visible)

    def test_update_item_location_character(self):
        from src.models import GameItem

        item = GameItem(item_id="c_item", name="C Item", location="腰间")
        self.state.character.items_visible["c_item"] = item
        self.manager.update_item_location_text("c_item", "手里")
        self.assertEqual(item.location, "手里")

    def test_update_item_location_npc(self):
        from src.models import NPC, GameItem

        npc = NPC(npc_id="miko", name="Miko")
        item = GameItem(item_id="n_item", name="N Item", location="口袋")
        npc.items_visible["n_item"] = item
        self.state.global_state.npcs["miko"] = npc
        self.state.scene.active_npc_ids.append("miko")

        self.manager.update_item_location_text("n_item", "手上")
        self.assertEqual(item.location, "手上")
