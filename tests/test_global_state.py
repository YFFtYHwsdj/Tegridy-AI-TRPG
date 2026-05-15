import unittest

from src.models import NPC, GameItem, Place
from src.state.global_state import GlobalState


class TestGlobalState(unittest.TestCase):
    def setUp(self):
        self.gs = GlobalState()
        self.gs.worldview = "=== 世界观设定 ==="

    def test_get_entity_by_id(self):
        self.gs.places["loc1"] = Place(place_id="loc1")
        self.gs.npcs["npc1"] = NPC(npc_id="npc1")
        self.gs.items["item1"] = GameItem(item_id="item1")

        t, _ = self.gs.get_entity_by_id("loc1")
        self.assertEqual(t, "place")
        t, _ = self.gs.get_entity_by_id("npc1")
        self.assertEqual(t, "npc")
        t, _ = self.gs.get_entity_by_id("item1")
        self.assertEqual(t, "item")
        t, _ = self.gs.get_entity_by_id("missing")
        self.assertEqual(t, "unknown")

    def test_build_graph_context(self):
        self.gs.places["loc1"] = Place(place_id="loc1", name="起点", connections={"loc2": "向北"})
        self.gs.places["loc2"] = Place(place_id="loc2", name="终点")

        ctx = self.gs.build_graph_context("loc1", [], [])
        self.assertIn("起点", ctx)
        self.assertIn("终点", ctx)


if __name__ == "__main__":
    unittest.main()
