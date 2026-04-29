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
        self.assertIsNotNone(state.global_state)
        self.assertEqual(state.global_state.scene_count, 0)

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

    def test_setup_does_not_affect_global_state(self):
        """首次 setup 不应向 GlobalState 写入任何内容。"""
        scene = self._make_scene("酒吧场景")
        self.state.setup(self.character, scene)
        self.assertEqual(self.state.global_state.scene_count, 0)

    # --- transition_to 测试 ---

    def test_transition_to_archives_scene_to_global_state(self):
        """场景切换应将当前场景的叙事推入 GlobalState。"""
        scene_a = self._make_scene("酒吧场景")
        self.state.setup(self.character, scene_a)
        self.state.append_narrative("你走进了酒吧")
        self.state.append_narrative("Miko 抬头看着你")

        scene_b = self._make_scene("后巷场景")
        self.state.transition_to(scene_b)

        self.assertEqual(self.state.global_state.scene_count, 1)
        self.assertEqual(self.state.scene.scene_description, "后巷场景")

    def test_transition_to_preserves_narrative_in_global_state(self):
        """场景切换后 GlobalState 中应包含旧场景的完整叙事。"""
        scene_a = self._make_scene("酒吧场景")
        self.state.setup(self.character, scene_a)
        self.state.append_narrative("叙事A")
        self.state.append_narrative("叙事B")

        scene_b = self._make_scene("后巷场景")
        self.state.transition_to(scene_b)

        block = self.state.global_state.build_block()
        self.assertIn("叙事A", block)
        self.assertIn("叙事B", block)
        self.assertIn("酒吧场景", block)

    def test_transition_to_records_previous_scenes_on_new_scene(self):
        """新场景的 previous_scenes 应包含旧场景的 SceneSummary。"""
        scene_a = self._make_scene("酒吧场景")
        self.state.setup(self.character, scene_a)
        scene_a.compression = "压缩摘要A"
        self.state.append_narrative("叙事条目")

        scene_b = self._make_scene("后巷场景")
        self.state.transition_to(scene_b)

        self.assertEqual(len(scene_b.previous_scenes), 1)
        self.assertEqual(scene_b.previous_scenes[0].scene_description, "酒吧场景")
        self.assertEqual(scene_b.previous_scenes[0].compression, "压缩摘要A")
        self.assertEqual(scene_b.previous_scenes[0].narrative_count, 1)

    def test_transition_to_chains_previous_scenes(self):
        """连续切换时 previous_scenes 应累积前驱链。"""
        scene_a = self._make_scene("场景A")
        self.state.setup(self.character, scene_a)
        scene_a.compression = "摘要A"

        scene_b = self._make_scene("场景B")
        self.state.transition_to(scene_b)
        scene_b.compression = "摘要B"

        scene_c = self._make_scene("场景C")
        self.state.transition_to(scene_c)

        self.assertEqual(len(scene_c.previous_scenes), 2)
        self.assertEqual(scene_c.previous_scenes[0].scene_description, "场景A")
        self.assertEqual(scene_c.previous_scenes[1].scene_description, "场景B")
        self.assertEqual(self.state.global_state.scene_count, 2)

    def test_transition_to_multiple_archives_global_state(self):
        """多次切换应累积 GlobalState 中的场景块。"""
        for desc in ["场景A", "场景B", "场景C"]:
            scene = self._make_scene(desc)
            if self.state.scene.scene_description:
                self.state.transition_to(scene)
            else:
                self.state.setup(self.character, scene)
            self.state.append_narrative(f"{desc}的叙事")

        self.assertEqual(self.state.global_state.scene_count, 2)
        self.assertEqual(self.state.scene.scene_description, "场景C")

    # --- append_narrative 测试 ---

    def test_append_narrative(self):
        self.state.append_narrative("你走进酒吧")
        self.assertEqual(len(self.state.scene.narrative_history), 1)
        self.assertEqual(self.state.scene.narrative_history[0], "你走进酒吧")

    def test_append_no_truncation(self):
        for i in range(100):
            self.state.append_narrative(f"事件{i}")
        self.assertEqual(len(self.state.scene.narrative_history), 100)

    # --- make_context 测试 ---

    def test_make_context_has_player_input(self):
        scene = self._make_scene("酒吧场景")
        self.state.setup(self.character, scene)
        ctx = self.state.make_context("我要拔枪")
        self.assertIsInstance(ctx, AgentContext)
        self.assertEqual(ctx.player_input, "我要拔枪")
        self.assertIs(ctx.character, self.character)
        self.assertIs(ctx.challenge, self.challenge)
        self.assertIsNotNone(ctx.assets_block)
        self.assertEqual(ctx.global_block, "")

    def test_make_context_no_player_input(self):
        scene = self._make_scene("酒吧场景")
        self.state.setup(self.character, scene)
        ctx = self.state.make_context()
        self.assertEqual(ctx.player_input, "")
        self.assertIsNotNone(ctx.assets_block)

    def test_make_context_includes_global_block_after_transition(self):
        """切换场景后 make_context 应包含 GlobalState 的历史块。"""
        scene_a = self._make_scene("酒吧场景")
        self.state.setup(self.character, scene_a)
        self.state.append_narrative("酒吧叙事")
        scene_a.compression = "酒吧压缩摘要"

        scene_b = self._make_scene("后巷场景")
        self.state.transition_to(scene_b)

        ctx = self.state.make_context("我要追击")
        self.assertIn("酒吧叙事", ctx.global_block)
        self.assertIn("酒吧压缩摘要", ctx.global_block)
        self.assertIn("=== 故事至今 ===", ctx.global_block)

    # --- _build_context_block 测试 ---

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
