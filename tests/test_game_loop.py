"""GameLoop 测试 —— 主循环的路由逻辑、命令处理、Move/非Move分流。

验证 GameLoop 的核心行为：
    - 系统命令处理（/quit, /debug, /help）
    - Move 判定和流水线路由
    - 非 Move 叙事处理
    - 极限突破处理
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from src.game_loop import GameLoop
from tests.helpers import MockLLMClient, make_test_character, make_test_scene


class TestGameLoopCommands(unittest.TestCase):
    """测试系统命令处理。"""

    def setUp(self):
        self.mock_llm = MockLLMClient()
        self.loop = GameLoop(self.mock_llm)

    def test_quit_command(self):
        """/quit 返回 QUIT。"""
        result = self.loop._handle_command("/quit")
        self.assertEqual(result, "QUIT")

    def test_exit_command(self):
        """/exit 返回 QUIT。"""
        result = self.loop._handle_command("/exit")
        self.assertEqual(result, "QUIT")

    def test_debug_command_toggles_mode(self):
        """/debug 切换调试模式。"""
        initial = self.loop.debug_mode
        self.loop._handle_command("/debug")
        self.assertEqual(self.loop.debug_mode, not initial)

    def test_help_command(self):
        """/help 显示帮助信息。"""
        with patch("builtins.print"):
            result = self.loop._handle_command("/help")
        self.assertEqual(result, "")

    def test_unknown_command(self):
        """未知命令显示错误提示。"""
        with patch("builtins.print"):
            result = self.loop._handle_command("/unknown")
        self.assertEqual(result, "")


class TestGameLoopSetup(unittest.TestCase):
    """测试 setup 方法。"""

    def setUp(self):
        self.mock_llm = MockLLMClient(
            [
                (
                    "=====REASONING=====\n场景建立\n=====STRUCTURED=====\n"
                    '{"scene_establishment": "霓虹灯闪烁的酒吧...", "spotlight_handoff": "你要做什么？"}',
                    {},
                ),
            ]
        )
        self.loop = GameLoop(self.mock_llm)

    def test_setup_sets_character_and_scene(self):
        """setup 正确设置角色和场景。"""
        character = make_test_character()
        scene = make_test_scene()
        from src.models import Challenge, Limit

        challenge = Challenge(
            name="测试挑战",
            description="测试",
            limits=[Limit(name="伤害", max_tier=3)],
        )
        scene.add_challenge(challenge)

        with patch("builtins.print"):
            self.loop.setup(character, scene)

        self.assertIs(self.loop.state.character, character)
        self.assertEqual(self.loop.state.scene.scene_description, "赛博朋克酒吧")

    def test_setup_calls_rhythm_agent(self):
        """setup 调用 RhythmAgent 生成开场叙事。"""
        character = make_test_character()
        scene = make_test_scene()
        from src.models import Challenge, Limit

        challenge = Challenge(
            name="测试挑战",
            description="测试",
            limits=[Limit(name="伤害", max_tier=3)],
        )
        scene.add_challenge(challenge)

        with patch("builtins.print"):
            self.loop.setup(character, scene)

        self.assertEqual(len(self.mock_llm.call_history), 1)

    def test_setup_appends_scene_establishment(self):
        """开场叙事被追加到场景历史。"""
        character = make_test_character()
        scene = make_test_scene()
        from src.models import Challenge, Limit

        challenge = Challenge(
            name="测试挑战",
            description="测试",
            limits=[Limit(name="伤害", max_tier=3)],
        )
        scene.add_challenge(challenge)

        with patch("builtins.print"):
            self.loop.setup(character, scene)

        self.assertTrue(len(self.loop.state.scene.narrative_history) > 0)


class TestGameLoopProcessAction(unittest.TestCase):
    """测试 process_action 的玩家行动处理。"""

    def setUp(self):
        self.mock_llm = MockLLMClient()
        self.loop = GameLoop(self.mock_llm)

        # 初始化游戏状态
        character = make_test_character()
        scene = make_test_scene()
        from src.models import Challenge, Limit

        challenge = Challenge(
            name="测试挑战",
            description="测试",
            limits=[Limit(name="伤害", max_tier=3)],
        )
        scene.add_challenge(challenge)
        self.loop.setup(character, scene)

        # Mock 各 Agent
        self.loop.gatekeeper = MagicMock()
        self.loop.intent_agent = MagicMock()
        self.loop.resolution_agent = MagicMock()
        self.loop.lite_narrator = MagicMock()
        self.loop.limit_break_agent = MagicMock()

        # Mock Pipeline
        self.loop.pipeline = MagicMock()

    def test_empty_input_returns_empty(self):
        """空输入返回空字符串。"""
        result = self.loop.process_action("")
        self.assertEqual(result, ("", False))

    def test_command_routing(self):
        """以 / 开头的输入走命令处理。"""
        result = self.loop.process_action("/quit")
        self.assertEqual(result, ("QUIT", False))

    def test_non_move_calls_lite_narrator(self):
        """守门人判定非 Move 时调用 LiteNarratorAgent。"""
        self.loop.gatekeeper.execute.return_value = MagicMock(
            reasoning="低风险观察",
            structured={"is_move": False, "rationale": "纯叙事"},
        )
        self.loop.lite_narrator.execute.return_value = MagicMock(
            structured={"narrative": "你环顾四周...", "revelation_decisions": {}}
        )

        with patch("builtins.print"):
            self.loop.process_action("看看周围")

        self.loop.lite_narrator.execute.assert_called_once()

    def test_move_calls_intent_agent(self):
        """Move 调用 IntentAgent 解析意图。"""
        self.loop.gatekeeper.execute.return_value = MagicMock(
            reasoning="这是Move",
            structured={"is_move": True},
        )
        self.loop.intent_agent.execute.return_value = MagicMock(
            structured={
                "action_type": "combat",
                "action_summary": "拔枪",
                "is_split_action": False,
            }
        )
        self.loop.resolution_agent.execute.return_value = MagicMock(
            structured={"resolution_mode": "detailed"}
        )
        self.loop.pipeline.run_single_move_pipeline.return_value = MagicMock(
            tag_note=MagicMock(),
            roll=MagicMock(outcome="partial_success", power=1, dice=(3, 4), total=8),
            effect_note=MagicMock(structured={"effects": []}),
            consequence_note=None,
            narrator_note=MagicMock(
                structured={"narrative": "你拔出了枪...", "revelation_decisions": {}}
            ),
        )

        with patch("builtins.print"):
            self.loop.process_action("我要拔枪")

        self.loop.intent_agent.execute.assert_called_once()

    def test_quick_resolution_calls_quick_pipeline(self):
        """resolution_mode=quick 时调用 run_quick_pipeline。"""
        self.loop.gatekeeper.execute.return_value = MagicMock(
            reasoning="这是Move",
            structured={"is_move": True},
        )
        self.loop.intent_agent.execute.return_value = MagicMock(
            structured={
                "action_type": "combat",
                "action_summary": "拔枪",
                "is_split_action": False,
            }
        )
        self.loop.resolution_agent.execute.return_value = MagicMock(
            structured={"resolution_mode": "quick"}
        )
        self.loop.pipeline.run_quick_pipeline.return_value = MagicMock(
            tag_note=MagicMock(),
            roll=MagicMock(outcome="partial_success", power=1, dice=(3, 4), total=8),
            effect_note=None,
            consequence_note=None,
            narrator_note=MagicMock(
                structured={"narrative": "你拔出了枪...", "revelation_decisions": {}}
            ),
        )

        with patch("builtins.print"):
            self.loop.process_action("我要拔枪")

        self.loop.pipeline.run_quick_pipeline.assert_called_once()

    def test_split_action_calls_process_split_moves(self):
        """is_split_action=True 时调用 _process_split_moves。"""
        self.loop.gatekeeper.execute.return_value = MagicMock(
            reasoning="这是Move",
            structured={"is_move": True},
        )
        self.loop.intent_agent.execute.return_value = MagicMock(
            structured={
                "action_type": "compound",
                "action_summary": "先拔枪再射击",
                "is_split_action": True,
                "split_actions": [
                    {
                        "action_type": "combat",
                        "action_summary": "拔枪",
                        "fragment": "拔枪",
                        "_index": 0,
                    },
                    {
                        "action_type": "combat",
                        "action_summary": "射击",
                        "fragment": "射击",
                        "_index": 1,
                    },
                ],
            }
        )
        self.loop.pipeline.process_split_actions.return_value = [
            MagicMock(
                tag_note=MagicMock(),
                roll=MagicMock(outcome="partial_success"),
                effect_note=MagicMock(structured={"effects": []}),
                consequence_note=None,
                narrator_note=MagicMock(structured={"narrative": "你拔出了枪..."}),
            ),
        ]

        with patch("builtins.print"):
            self.loop.process_action("先拔枪再射击")

        self.loop.pipeline.process_split_actions.assert_called_once()

    def test_move_appends_narrative_to_state(self):
        """叙事文本被追加到场景历史。"""
        self.loop.gatekeeper.execute.return_value = MagicMock(
            reasoning="这是Move",
            structured={"is_move": True},
        )
        self.loop.intent_agent.execute.return_value = MagicMock(
            structured={
                "action_type": "combat",
                "action_summary": "拔枪",
                "is_split_action": False,
            }
        )
        self.loop.resolution_agent.execute.return_value = MagicMock(
            structured={"resolution_mode": "detailed"}
        )
        self.loop.pipeline.run_single_move_pipeline.return_value = MagicMock(
            tag_note=MagicMock(),
            roll=MagicMock(outcome="partial_success", power=1, dice=(3, 4), total=8),
            effect_note=MagicMock(structured={"effects": []}),
            consequence_note=None,
            narrator_note=MagicMock(
                structured={"narrative": "你迅速拔枪...", "revelation_decisions": {}}
            ),
        )

        with patch("builtins.print"):
            self.loop.process_action("我要拔枪")

        self.assertIn("你迅速拔枪...", self.loop.state.scene.narrative_history)


class TestGameLoopToggleDebug(unittest.TestCase):
    """测试调试模式切换。"""

    def setUp(self):
        self.mock_llm = MockLLMClient()
        self.loop = GameLoop(self.mock_llm)

    def test_toggle_debug_returns_new_state(self):
        """toggle_debug 返回切换后的状态。"""
        initial = self.loop.debug_mode
        result = self.loop.toggle_debug()
        self.assertEqual(result, not initial)

    def test_double_toggle_restores(self):
        """两次切换恢复原始状态。"""
        initial = self.loop.debug_mode
        self.loop.toggle_debug()
        self.loop.toggle_debug()
        self.assertEqual(self.loop.debug_mode, initial)


if __name__ == "__main__":
    unittest.main()
