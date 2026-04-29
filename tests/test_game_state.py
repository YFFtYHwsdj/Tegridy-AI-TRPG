import unittest

from src.context import AgentContext
from src.models import Challenge, Character, Limit, PowerTag, WeaknessTag
from src.state.game_state import GameState
from src.state.scene_state import SceneState


class TestGameState(unittest.TestCase):
    def setUp(self):
        self.state = GameState()
        self.character = Character(
            name="Kael",
            description="佣兵",
            power_tags=[PowerTag(name="快速拔枪")],
            weakness_tags=[WeaknessTag(name="信用破产")],
        )
        self.challenge = Challenge(
            name="Miko 与她的保镖",
            description="中间人",
            limits=[Limit(name="伤害", max_tier=4)],
        )

    def _make_scene(self, description="酒吧场景"):
        scene = SceneState(scene_description=description)
        scene.add_challenge(self.challenge)
        return scene

    def test_defaults(self):
        state = GameState()
        self.assertIsNone(state.character)
        self.assertIsNotNone(state.scene)
        self.assertEqual(state.scene.scene_description, "")
        self.assertEqual(state.scene.narrative_history, [])

    def test_setup(self):
        scene = self._make_scene("赛博朋克酒吧场景")
        self.state.setup(self.character, scene)
        self.assertIs(self.state.character, self.character)
        self.assertIs(self.state.scene.primary_challenge(), self.challenge)
        self.assertEqual(self.state.scene.scene_description, "赛博朋克酒吧场景")
        self.assertEqual(self.state.scene.narrative_history, [])

    def test_setup_clears_previous_history(self):
        self.state.scene.narrative_history = ["旧条目"]
        scene = self._make_scene("新场景")
        self.state.setup(self.character, scene)
        self.assertEqual(self.state.scene.narrative_history, [])

    def test_scene_history_archives_previous_scene(self):
        scene_a = self._make_scene("酒吧场景")
        self.state.setup(self.character, scene_a)
        self.state.append_narrative("你走进了酒吧")
        first_scene = self.state.scene
        scene_b = self._make_scene("后巷场景")
        self.state.setup(self.character, scene_b)
        self.assertEqual(len(self.state.scene_history), 1)
        self.assertIs(self.state.scene_history[0], first_scene)
        self.assertEqual(self.state.scene_history[0].scene_description, "酒吧场景")

    def test_scene_history_empty_on_first_setup(self):
        scene = self._make_scene("酒吧场景")
        self.state.setup(self.character, scene)
        self.assertEqual(len(self.state.scene_history), 0)

    def test_scene_history_multiple_archives(self):
        self.state.setup(self.character, self._make_scene("场景A"))
        self.state.setup(self.character, self._make_scene("场景B"))
        self.state.setup(self.character, self._make_scene("场景C"))
        self.assertEqual(len(self.state.scene_history), 2)
        self.assertEqual(self.state.scene_history[0].scene_description, "场景A")
        self.assertEqual(self.state.scene_history[1].scene_description, "场景B")
        self.assertEqual(self.state.scene.scene_description, "场景C")

    def test_append_narrative(self):
        self.state.append_narrative("你走进酒吧")
        self.assertEqual(len(self.state.scene.narrative_history), 1)
        self.assertEqual(self.state.scene.narrative_history[0], "你走进酒吧")

    def test_append_no_truncation(self):
        for i in range(100):
            self.state.append_narrative(f"事件{i}")
        self.assertEqual(len(self.state.scene.narrative_history), 100)

    def test_make_context_has_player_input(self):
        scene = self._make_scene("酒吧场景")
        self.state.setup(self.character, scene)
        ctx = self.state.make_context("我要拔枪")
        self.assertIsInstance(ctx, AgentContext)
        self.assertEqual(ctx.player_input, "我要拔枪")
        self.assertIs(ctx.character, self.character)
        self.assertIs(ctx.challenge, self.challenge)
        self.assertIsNotNone(ctx.assets_block)

    def test_make_context_no_player_input(self):
        scene = self._make_scene("酒吧场景")
        self.state.setup(self.character, scene)
        ctx = self.state.make_context()
        self.assertEqual(ctx.player_input, "")
        self.assertIsNotNone(ctx.assets_block)

    def test_build_context_block_with_broken_limits(self):
        scene = self._make_scene("酒吧场景")
        self.state.setup(self.character, scene)
        self.challenge.mark_limits_broken(["伤害"])
        block = self.state.scene._build_context_block(self.character, self.challenge)
        self.assertIn("已突破极限: 伤害", block)

    def test_build_context_block_with_transformation(self):
        scene = self._make_scene("酒吧场景")
        self.state.setup(self.character, scene)
        self.challenge.transformation = "Miko 放下了戒备"
        block = self.state.scene._build_context_block(self.character, self.challenge)
        self.assertIn("挑战转变: Miko 放下了戒备", block)

    def test_build_context_block_no_setup(self):
        block = self.state.scene._build_context_block(None, None)
        self.assertEqual(block, "")

    def test_build_context_block_empty_limits(self):
        challenge = Challenge(name="简单", description="test", limits=[])
        scene = SceneState(scene_description="测试场景")
        scene.add_challenge(challenge)
        self.state.setup(self.character, scene)
        block = self.state.scene._build_context_block(self.character, challenge)
        self.assertIn("（无极限设置）", block)

    def test_build_narrative_block_empty(self):
        block = self.state.scene._build_narrative_block()
        self.assertEqual(block, "（无历史）")

    def test_build_narrative_block_with_history(self):
        self.state.append_narrative("事件A")
        self.state.append_narrative("事件B")
        block = self.state.scene._build_narrative_block()
        self.assertIn("[1] 事件A", block)
        self.assertIn("[2] 事件B", block)

    def test_build_narrative_block_full_history(self):
        for i in range(10):
            self.state.append_narrative(f"事件{i}")
        block = self.state.scene._build_narrative_block()
        lines = block.split("\n")
        self.assertEqual(len(lines), 10)
        self.assertIn("[1] 事件0", lines[0])
        self.assertIn("[10] 事件9", lines[-1])


if __name__ == "__main__":
    unittest.main()
