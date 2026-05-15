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
        t, _ = self.gs.get_entity_by_id("missing")
        self.assertEqual(t, "unknown")

    def test_get_entity_by_id_challenge(self):
        from src.models import Challenge

        self.gs.challenges["chal1"] = Challenge(name="Test Challenge", limits={"A": 1})
        t, _ = self.gs.get_entity_by_id("chal1")
        self.assertEqual(t, "challenge")

    def test_scene_count(self):
        self.assertEqual(self.gs.scene_count, 0)
        self.gs.append_narrative_block("s1", "desc1", "comp1", ["narr1"])
        self.assertEqual(self.gs.scene_count, 1)

    def test_build_narrative_context_edge_cases(self):
        # 无场景时
        self.assertEqual(self.gs.build_narrative_context(), "")

        # 添加3个场景，测试不同组合
        self.gs.append_narrative_block("s1", "desc1", "comp1", ["narr1"])
        self.gs.append_narrative_block("s2", "desc2", "", ["narr2"])  # 无压缩
        self.gs.append_narrative_block("s3", "desc3", "", [])  # 无压缩，无叙事

        ctx = self.gs.build_narrative_context()
        self.assertIn("[场景1] desc1", ctx)
        self.assertIn("comp1", ctx)
        self.assertIn("[场景2] desc2", ctx)
        self.assertIn("（无压缩摘要）", ctx)
        self.assertIn("[场景3] desc3", ctx)
        self.assertIn("（无叙事记录）", ctx)

    def test_build_graph_context(self):
        self.gs.places["loc1"] = Place(place_id="loc1", name="起点", connections={"loc2": "向北"})
        self.gs.places["loc2"] = Place(place_id="loc2", name="终点")

        ctx = self.gs.build_graph_context("loc1", [], [])
        self.assertIn("起点", ctx)
        self.assertIn("终点", ctx)

    def test_build_graph_context_depth_and_items(self):
        # 构建 0 -> 1 -> 2 -> 3 跳的结构
        self.gs.places["loc0"] = Place(
            place_id="loc0", name="P0", connections={"loc1": "前往"}, notes="地点笔记"
        )
        self.gs.places["loc1"] = Place(place_id="loc1", name="P1", connections={"npc2": "里面有"})
        self.gs.npcs["npc2"] = NPC(
            npc_id="npc2", name="N2", relationships={"item3": "持有"}, notes="NPC笔记"
        )
        self.gs.items["item3"] = GameItem(
            item_id="item3", name="I3", relationships={"loc4": "指向"}, notes="物品笔记"
        )
        self.gs.places["loc4"] = Place(place_id="loc4", name="P4")  # 第4跳，应该被截断

        # 同样也测试通过 items 入口直接传入图
        ctx = self.gs.build_graph_context("loc0", [], ["item3"])

        # 应该包含 0, 1, 2跳的实体
        self.assertIn("P0", ctx)
        self.assertIn("地点笔记", ctx)
        self.assertIn("P1", ctx)
        self.assertIn("N2", ctx)
        self.assertIn("NPC笔记", ctx)
        self.assertIn("I3", ctx)
        self.assertIn("物品笔记", ctx)

        # loc4 对于 loc0 来说是3跳会被截断。但我们加了 item3 为 0跳起点，loc4 是 1跳，所以会包含
        # 我们这里重新单独测试一次纯截断：
        ctx2 = self.gs.build_graph_context("loc0", [], [])
        self.assertNotIn("P4", ctx2)


if __name__ == "__main__":
    unittest.main()
