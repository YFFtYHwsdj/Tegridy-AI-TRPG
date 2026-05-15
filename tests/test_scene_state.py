import unittest

from src.models import NPC, GameItem
from src.state.character_state import CharacterState
from src.state.global_state import GlobalState
from src.state.scene_state import SceneState


class TestSceneState(unittest.TestCase):
    def test_defaults(self):
        scene = SceneState()
        self.assertEqual(scene.place_id, "")
        self.assertEqual(scene.situation, "")
        self.assertEqual(scene.active_npc_ids, [])
        self.assertEqual(scene.active_item_ids, [])
        self.assertEqual(scene.narrative_history, [])
        self.assertEqual(scene.compression, "")

    def test_append_narrative(self):
        scene = SceneState()
        scene.append_narrative("第一句")
        scene.append_narrative("第二句")
        self.assertEqual(len(scene.narrative_history), 2)
        self.assertEqual(scene.narrative_history[0], "第一句")
        self.assertEqual(scene.narrative_history[1], "第二句")

    def test_build_assets_block_empty(self):
        scene = SceneState()
        global_state = GlobalState()
        block = scene._build_assets_block(global_state, None)
        self.assertIn("场景人物: （无）", block)
        self.assertIn("场景物品: （无）", block)

    def test_build_assets_block_with_data(self):
        npc = NPC(npc_id="miko", name="Miko", description="酒保")
        item = GameItem(item_id="data_pad", name="数据板", description="包含机密", location="桌上")

        global_state = GlobalState()
        global_state.npcs["miko"] = npc
        global_state.items["data_pad"] = item

        scene = SceneState(
            place_id="test_loc",
            situation="酒吧",
            active_npc_ids=["miko"],
            active_item_ids=["data_pad"],
        )

        character = CharacterState(name="Kael")
        c_item = GameItem(item_id="gun", name="手枪", description="武器")
        character.items_visible["gun"] = c_item

        block = scene._build_assets_block(global_state, character)

        self.assertIn("Miko", block)
        self.assertIn("酒保", block)
        self.assertIn("数据板", block)
        self.assertIn("桌上", block)
        self.assertIn("手枪", block)

    def test_make_context(self):
        scene = SceneState(place_id="loc1", situation="酒吧")
        scene.append_narrative("走入酒吧。")

        global_state = GlobalState()

        character = CharacterState(name="Kael")
        ctx = scene.make_context(character, global_state, "我要点酒")

        self.assertIn("当前状况: 酒吧", ctx.context_block)
        self.assertIn("走入酒吧。", ctx.narrative_block)
        self.assertEqual(ctx.player_input, "我要点酒")
        self.assertIs(ctx.character, character)


if __name__ == "__main__":
    unittest.main()
