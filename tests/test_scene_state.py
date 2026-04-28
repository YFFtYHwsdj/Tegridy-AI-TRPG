import unittest

from src.models import NPC, Challenge, Clue, GameItem, Limit
from src.state.scene_state import HISTORY_BUFFER, MAX_HISTORY_ENTRIES, SceneState


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

    def test_append_within_limit(self):
        scene = SceneState()
        for i in range(MAX_HISTORY_ENTRIES):
            scene.append_narrative(f"事件{i}")
        self.assertEqual(len(scene.narrative_history), MAX_HISTORY_ENTRIES)

    def test_append_overflow_trims(self):
        scene = SceneState()
        total = MAX_HISTORY_ENTRIES + HISTORY_BUFFER + 5
        for i in range(total):
            scene.append_narrative(f"事件{i}")
        self.assertEqual(len(scene.narrative_history), MAX_HISTORY_ENTRIES + HISTORY_BUFFER)
        self.assertEqual(
            scene.narrative_history[0], f"事件{total - (MAX_HISTORY_ENTRIES + HISTORY_BUFFER)}"
        )

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


if __name__ == "__main__":
    unittest.main()
