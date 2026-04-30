"""GameLoop.step() 测试 —— 单步推进 API 的行为验证。

验证 step() 方法的三种结果路径：
    - 退出请求 → StepResult(is_quit=True)
    - 空输入/命令 → StepResult(is_empty=True)
    - 有叙事产出 → 场景导演判定 + 可能的场景切换
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from src.game_loop import GameLoop, StepResult
from tests.helpers import MockLLMClient, make_test_character, make_test_scene


class TestStepResult(unittest.TestCase):
    """测试 StepResult 数据类的默认值。"""

    def test_default_values(self):
        """默认 StepResult 所有字段为零值。"""
        result = StepResult()
        self.assertEqual(result.narrative, "")
        self.assertFalse(result.is_quit)
        self.assertFalse(result.scene_changed)
        self.assertEqual(result.scene_end_reason, "")
        self.assertFalse(result.is_empty)


class TestGameLoopStep(unittest.TestCase):
    """测试 GameLoop.step() 的三种结果路径。"""

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
        self.loop.scene_director = MagicMock()

        # Mock Pipeline
        self.loop.pipeline = MagicMock()

    def test_step_quit_command(self):
        """step('/quit') 返回 is_quit=True。"""
        result = self.loop.step("/quit")
        self.assertTrue(result.is_quit)
        self.assertFalse(result.scene_changed)
        self.assertEqual(result.narrative, "")

    def test_step_empty_input(self):
        """step('') 返回 is_empty=True。"""
        result = self.loop.step("")
        self.assertTrue(result.is_empty)
        self.assertFalse(result.is_quit)

    def test_step_command_returns_empty(self):
        """step('/help') 返回 is_empty=True（命令已处理，无叙事）。"""
        result = self.loop.step("/help")
        self.assertTrue(result.is_empty)
        self.assertFalse(result.is_quit)

    def test_step_non_move_no_scene_change(self):
        """非 Move 行动，场景导演判定不结束，返回叙事文本。"""
        self.loop.gatekeeper.execute.return_value = MagicMock(
            reasoning="低风险观察",
            structured={"is_move": False, "rationale": "纯叙事"},
        )
        self.loop.lite_narrator.execute.return_value = MagicMock(
            structured={"narrative": "你环顾四周...", "revelation_decisions": {}}
        )
        # 场景导演判定不结束
        self.loop.scene_director.execute.return_value = MagicMock(
            structured={"scene_should_end": False}
        )

        result = self.loop.step("看看周围")

        self.assertEqual(result.narrative, "你环顾四周...")
        self.assertFalse(result.scene_changed)
        self.assertFalse(result.is_quit)
        self.assertFalse(result.is_empty)
        # 确认场景导演被调用
        self.loop.scene_director.execute.assert_called_once()

    def test_step_scene_change_triggered(self):
        """场景导演判定结束时，step() 返回 scene_changed=True。"""
        self.loop.gatekeeper.execute.return_value = MagicMock(
            reasoning="低风险",
            structured={"is_move": False},
        )
        self.loop.lite_narrator.execute.return_value = MagicMock(
            structured={"narrative": "你完成了任务...", "revelation_decisions": {}}
        )
        # 场景导演判定结束
        self.loop.scene_director.execute.return_value = MagicMock(
            structured={
                "scene_should_end": True,
                "reason": "挑战解决",
                "transition_hint": "前往下一个区域",
            }
        )

        # Mock _transition_scene 避免触发复杂的内部场景切换流水线
        self.loop._transition_scene = MagicMock()

        result = self.loop.step("我完成任务了")

        self.assertTrue(result.scene_changed)
        self.assertEqual(result.scene_end_reason, "挑战解决")
        self.assertEqual(result.narrative, "你完成了任务...")
        # 确认 _transition_scene 被调用
        self.loop._transition_scene.assert_called_once()
        # 确认 transition_hint 被正确保存
        self.assertEqual(self.loop._transition_hint, "前往下一个区域")

    def test_step_move_with_narrative(self):
        """Move 行动产出叙事，场景不结束。"""
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
        # 场景导演判定不结束
        self.loop.scene_director.execute.return_value = MagicMock(
            structured={"scene_should_end": False}
        )

        result = self.loop.step("我要拔枪")

        self.assertEqual(result.narrative, "你拔出了枪...")
        self.assertFalse(result.scene_changed)
        self.assertFalse(result.is_quit)
        self.assertFalse(result.is_empty)


if __name__ == "__main__":
    unittest.main()
