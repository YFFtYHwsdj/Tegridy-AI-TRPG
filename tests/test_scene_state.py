import unittest

from src.models import NPC, Challenge, Clue, GameItem, Limit
from src.state.scene_state import SceneState


class TestSceneState(unittest.TestCase):
    def test_defaults(self):
        scene = SceneState()
        self.assertEqual(scene.scene_description, "")
        self.assertEqual(scene.scene_items_visible, {})
        self.assertEqual(scene.scene_items_hidden, {})
        self.assertEqual(scene.clues_visible, {})
        self.assertEqual(scene.clues_hidden, {})
        self.assertEqual(scene.npcs, {})
        self.assertEqual(scene.active_challenges, {})
        self.assertEqual(scene.narrative_history, [])

    def test_scene_description(self):
        scene = SceneState(scene_description="赛博朋克酒吧")
        self.assertEqual(scene.scene_description, "赛博朋克酒吧")

    def test_append_narrative(self):
        scene = SceneState()
        scene.append_narrative("你走进了酒吧")
        self.assertEqual(len(scene.narrative_history), 1)
        self.assertEqual(scene.narrative_history[0], "你走进了酒吧")

    def test_append_no_truncation(self):
        scene = SceneState()
        for i in range(100):
            scene.append_narrative(f"事件{i}")
        self.assertEqual(len(scene.narrative_history), 100)

    def test_add_and_get_challenge(self):
        scene = SceneState()
        chal = Challenge(name="Miko", description="中间人", limits=[Limit("说服", 3)])
        scene.add_challenge(chal)
        self.assertIn("Miko", scene.active_challenges)
        self.assertIs(scene.get_challenge("Miko"), chal)

    def test_get_challenge_nonexistent(self):
        scene = SceneState()
        self.assertIsNone(scene.get_challenge("不存在"))

    def test_multiple_challenges(self):
        scene = SceneState()
        chal1 = Challenge(name="Miko", description="中间人")
        chal2 = Challenge(name="保镖", description="护卫")
        scene.add_challenge(chal1)
        scene.add_challenge(chal2)
        self.assertEqual(len(scene.active_challenges), 2)
        self.assertIs(scene.get_challenge("Miko"), chal1)
        self.assertIs(scene.get_challenge("保镖"), chal2)

    def test_scene_items_visible(self):
        item = GameItem(item_id="data_pad", name="数据板", location="吧台")
        scene = SceneState(scene_items_visible={"data_pad": item})
        self.assertIn("data_pad", scene.scene_items_visible)
        self.assertEqual(scene.scene_items_visible["data_pad"].name, "数据板")

    def test_scene_items_hidden(self):
        item = GameItem(item_id="medkit", name="急救包", location="暗格")
        scene = SceneState(scene_items_hidden={"medkit": item})
        self.assertIn("medkit", scene.scene_items_hidden)
        self.assertEqual(scene.scene_items_hidden["medkit"].name, "急救包")

    def test_clues_visible_and_hidden(self):
        clue = Clue(clue_id="chip", name="加密芯片", description="刻有密级标记")
        scene = SceneState(
            clues_hidden={"chip": clue},
            clues_visible={},
        )
        self.assertIn("chip", scene.clues_hidden)
        self.assertEqual(len(scene.clues_visible), 0)

    def test_npcs(self):
        npc = NPC(npc_id="miko", name="Miko", description="帮派中间人")
        scene = SceneState(npcs={"miko": npc})
        self.assertIn("miko", scene.npcs)
        self.assertEqual(scene.npcs["miko"].name, "Miko")

    def test_build_assets_block_empty(self):
        scene = SceneState()
        block = scene._build_assets_block(None)
        self.assertIn("=== 场景资产 ===", block)
        self.assertIn("场景人物: （无）", block)
        self.assertIn("线索: （无）", block)
        self.assertIn("场景物品: （无）", block)
        self.assertIn("角色的随身物品: （无）", block)

    def test_build_assets_block_with_data(self):
        npc = NPC(
            npc_id="miko",
            name="Miko",
            description="帮派中间人",
            items_visible={"chip": GameItem(item_id="chip", name="芯片", description="数据芯片")},
            items_hidden={"key": GameItem(item_id="key", name="钥匙", description="暗门钥匙")},
        )
        clue_vis = Clue(clue_id="log", name="通讯记录", description="保镖的短讯")
        clue_hid = Clue(clue_id="motive", name="真正动机", description="Miko想背叛")
        item_vis = GameItem(
            item_id="pad", name="数据板", description="Miko的数据板", location="吧台"
        )
        item_hid = GameItem(
            item_id="medkit", name="急救包", description="军规急救包", location="暗格"
        )

        scene = SceneState(
            npcs={"miko": npc},
            clues_visible={"log": clue_vis},
            clues_hidden={"motive": clue_hid},
            scene_items_visible={"pad": item_vis},
            scene_items_hidden={"medkit": item_hid},
        )

        block = scene._build_assets_block(None)
        self.assertIn("Miko: 帮派中间人", block)
        self.assertIn("芯片(可见)", block)
        self.assertIn("钥匙(隐藏)", block)
        self.assertIn("通讯记录(可见)", block)
        self.assertIn("真正动机(隐藏)", block)
        self.assertIn("数据板 [吧台]", block)
        self.assertIn("军规急救包 (隐藏)", block)

    def test_build_narrative_block_order(self):
        scene = SceneState()
        scene.append_narrative("事件A")
        scene.append_narrative("事件B")
        scene.append_narrative("事件C")
        block = scene._build_narrative_block()
        lines = block.split("\n")
        self.assertEqual(len(lines), 3)
        self.assertIn("[1] 事件A", lines[0])
        self.assertIn("[2] 事件B", lines[1])
        self.assertIn("[3] 事件C", lines[2])


if __name__ == "__main__":
    unittest.main()
