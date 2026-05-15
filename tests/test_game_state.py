import unittest

from src.state.character_state import CharacterState
from src.state.game_state import GameState
from src.state.scene_state import SceneState


class TestGameState(unittest.TestCase):
    def setUp(self):
        self.state = GameState()

    def _make_character(self) -> CharacterState:
        return CharacterState(name="Kael", description="佣兵")

    def _make_scene(self, situation: str) -> SceneState:
        return SceneState(place_id="loc1", situation=situation)

    def test_initial_state(self):
        self.assertIsNone(self.state.character)
        self.assertEqual(self.state.scene.place_id, "")

    def test_setup_assigns_character_and_scene(self):
        char = self._make_character()
        scene = self._make_scene("酒吧场景")
        self.state.setup(char, scene)

        self.assertIs(self.state.character, char)
        self.assertIs(self.state.scene, scene)

    def test_make_context(self):
        char = self._make_character()
        scene = self._make_scene("酒吧场景")
        self.state.setup(char, scene)

        ctx = self.state.make_context("点一杯酒")
        self.assertIs(ctx.character, char)
        self.assertEqual(ctx.player_input, "点一杯酒")
        self.assertIn("当前状况: 酒吧场景", ctx.context_block)
        
        self.state.global_state.worldview = "世界观测试"
        ctx = self.state.make_context("点一杯酒")
        self.assertEqual(ctx.worldview_block, "世界观测试")

    def test_setup_does_not_affect_global_state(self):
        char = self._make_character()
        scene = self._make_scene("酒吧场景")
        self.state.setup(char, scene)

        # 首次 setup 虽然分配了 scene，但那是起始状态，此时并无历史需要写入
        # (GlobalState 现在不负责纯历史累加，而是维护网络)
        self.assertEqual(self.state.global_state.get_entity_by_id("loc1")[1], None)

    def test_transition_to_preserves_narrative_in_global_state(self):
        char = self._make_character()
        scene_a = self._make_scene("酒吧场景")
        scene_a.append_narrative("第一句话")
        self.state.setup(char, scene_a)

        scene_b = self._make_scene("巷子场景")
        self.state.transition_to(scene_b)
        self.assertIs(self.state.scene, scene_b)
        # GlobalState 现在只有实体图，叙事历史被废弃了，但在 SceneState._transition 可能会被 Compressor 压缩
        # 所以我们不需要在这里测试 GlobalState 是否有 narrative_history。


if __name__ == "__main__":
    unittest.main()
