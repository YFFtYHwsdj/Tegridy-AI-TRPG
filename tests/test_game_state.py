import unittest
from src.state.game_state import GameState, MAX_HISTORY_ENTRIES, HISTORY_BUFFER
from src.models import Character, Challenge, Limit, Tag
from src.context import AgentContext


class TestGameState(unittest.TestCase):

    def setUp(self):
        self.state = GameState()
        self.character = Character(
            name="Kael",
            description="佣兵",
            power_tags=[Tag(name="快速拔枪", tag_type="power")],
            weakness_tags=[Tag(name="信用破产", tag_type="weakness")],
        )
        self.challenge = Challenge(
            name="Miko 与她的保镖",
            description="中间人",
            limits=[Limit(name="伤害", max_tier=4)],
        )

    def test_defaults(self):
        state = GameState()
        self.assertIsNone(state.character)
        self.assertIsNone(state.challenge)
        self.assertEqual(state.scene_context, "")
        self.assertEqual(state.narrative_history, [])

    def test_setup(self):
        self.state.setup(
            self.character, self.challenge, "赛博朋克酒吧场景"
        )
        self.assertIs(self.state.character, self.character)
        self.assertIs(self.state.challenge, self.challenge)
        self.assertEqual(self.state.scene_context, "赛博朋克酒吧场景")
        self.assertEqual(self.state.narrative_history, [])

    def test_setup_clears_previous_history(self):
        self.state.narrative_history = ["旧条目"]
        self.state.setup(self.character, self.challenge, "新场景")
        self.assertEqual(self.state.narrative_history, [])

    def test_append_narrative(self):
        self.state.append_narrative("你走进酒吧")
        self.assertEqual(len(self.state.narrative_history), 1)
        self.assertEqual(self.state.narrative_history[0], "你走进酒吧")

    def test_append_within_limit(self):
        for i in range(MAX_HISTORY_ENTRIES):
            self.state.append_narrative(f"事件{i}")
        self.assertEqual(len(self.state.narrative_history), MAX_HISTORY_ENTRIES)

    def test_append_within_buffer(self):
        total = MAX_HISTORY_ENTRIES + HISTORY_BUFFER
        for i in range(total):
            self.state.append_narrative(f"事件{i}")
        self.assertEqual(len(self.state.narrative_history), total)

    def test_append_overflow_trims_oldest(self):
        total = MAX_HISTORY_ENTRIES + HISTORY_BUFFER + 3
        for i in range(total):
            self.state.append_narrative(f"事件{i}")
        self.assertEqual(
            len(self.state.narrative_history),
            MAX_HISTORY_ENTRIES + HISTORY_BUFFER,
        )
        self.assertEqual(self.state.narrative_history[0], f"事件{total - (MAX_HISTORY_ENTRIES + HISTORY_BUFFER)}")

    def test_make_context_has_player_input(self):
        self.state.setup(self.character, self.challenge, "酒吧场景")
        ctx = self.state.make_context("我要拔枪")
        self.assertIsInstance(ctx, AgentContext)
        self.assertEqual(ctx.player_input, "我要拔枪")
        self.assertIs(ctx.character, self.character)
        self.assertIs(ctx.challenge, self.challenge)

    def test_make_context_no_player_input(self):
        self.state.setup(self.character, self.challenge, "酒吧场景")
        ctx = self.state.make_context()
        self.assertEqual(ctx.player_input, "")

    def test_build_context_block_with_broken_limits(self):
        self.state.setup(self.character, self.challenge, "酒吧场景")
        self.challenge.mark_limits_broken(["伤害"])
        block = self.state._build_context_block()
        self.assertIn("已突破极限: 伤害", block)

    def test_build_context_block_with_transformation(self):
        self.state.setup(self.character, self.challenge, "酒吧场景")
        self.challenge.transformation = "Miko 放下了戒备"
        block = self.state._build_context_block()
        self.assertIn("挑战转变: Miko 放下了戒备", block)

    def test_build_context_block_no_setup(self):
        block = self.state._build_context_block()
        self.assertEqual(block, "")

    def test_build_context_block_empty_limits(self):
        challenge = Challenge(name="简单", description="test", limits=[])
        self.state.setup(self.character, challenge, "测试场景")
        block = self.state._build_context_block()
        self.assertIn("（无极限设置）", block)

    def test_build_narrative_block_empty(self):
        block = self.state._build_narrative_block()
        self.assertEqual(block, "（无历史）")

    def test_build_narrative_block_with_history(self):
        self.state.append_narrative("事件A")
        self.state.append_narrative("事件B")
        block = self.state._build_narrative_block()
        self.assertIn("[1] 事件A", block)
        self.assertIn("[2] 事件B", block)

    def test_build_narrative_block_truncates_to_max(self):
        total = MAX_HISTORY_ENTRIES + HISTORY_BUFFER + 5
        for i in range(total):
            self.state.append_narrative(f"事件{i}")
        block = self.state._build_narrative_block()
        lines = block.split("\n")
        self.assertEqual(len(lines), MAX_HISTORY_ENTRIES)
        self.assertIn("[1]", lines[0])
        self.assertIn(f"[{MAX_HISTORY_ENTRIES}]", lines[-1])


if __name__ == "__main__":
    unittest.main()
