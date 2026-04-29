"""ConsoleDisplay 测试 —— 调试信息输出验证。

验证 ConsoleDisplay 各方法通过日志系统的 DEBUG 通道正确输出内容。
输出内容的终端可见性由日志系统的 ConsoleHandler 等级控制，
不在 ConsoleDisplay 内部维护 debug_mode 状态。
"""

from __future__ import annotations

import logging
import unittest
from unittest.mock import MagicMock, patch

from src.display.console import ConsoleDisplay
from src.models import AgentNote, Challenge, Limit, RollResult, Status, StoryTag


def _collect_debug_output(mock_debug) -> str:
    """从 mock_debug.call_args_list 中拼接所有 debug 调用的参数文本。

    Logger.debug 使用 printf 风格（如 debug("模板 %s", arg1)），
    需要将格式串和参数一起收集才能检出实际内容。
    """
    parts = []
    for call in mock_debug.call_args_list:
        for arg in call.args:
            parts.append(str(arg))
    return "\n".join(parts)


class TestConsoleDisplayOutput(unittest.TestCase):
    """测试 ConsoleDisplay 的 debug 输出。"""

    def setUp(self):
        self.logger = logging.getLogger("aitrpg.game")
        self.display = ConsoleDisplay(self.logger)

    def test_methods_always_call_debug(self):
        """所有方法始终调用 logger.debug（由 handler 等级控制终端可见性）。"""
        with patch.object(self.logger, "debug") as mock_debug:
            self.display.print_tag_and_roll(MagicMock(), MagicMock())
            self.display.print_effects(MagicMock())
            self.display.print_consequences(MagicMock())
            self.display.print_strategy(MagicMock())
            self.display.print_status(self._make_state_mock())

        self.assertTrue(mock_debug.called)

    def _make_state_mock(self):
        """创建带角色和挑战的 state mock，避免 print_status 因 None 提前返回。"""
        state = MagicMock()
        character = MagicMock()
        character.name = "Kael"
        character.statuses = {}
        character.story_tags = {}
        character.items_visible = {}
        state.character = character

        challenge = Challenge(
            name="测试挑战",
            description="测试",
            limits=[Limit(name="伤害", max_tier=3)],
        )
        scene = MagicMock()
        scene.primary_challenge.return_value = challenge
        scene.scene_items_visible = {}
        state.scene = scene
        return state

    def test_outputs_matched_tags(self):
        """输出匹配的标签名称。"""
        with patch.object(self.logger, "debug") as mock_debug:
            tag_note = AgentNote(
                reasoning="匹配",
                structured={
                    "matched_power_tags": [{"name": "快速拔枪"}, {"name": "前公司安保"}],
                    "matched_weakness_tags": [{"name": "信用破产"}],
                    "helping_statuses": [],
                    "hindering_statuses": [],
                },
            )
            roll = RollResult(power=2, dice=(5, 4), total=11, outcome="full_success")
            self.display.print_tag_and_roll(tag_note, roll)

        output = _collect_debug_output(mock_debug)
        self.assertIn("快速拔枪", output)
        self.assertIn("信用破产", output)

    def test_outputs_roll_info(self):
        """输出掷骰结果。"""
        with patch.object(self.logger, "debug") as mock_debug:
            tag_note = AgentNote(
                reasoning="匹配",
                structured={
                    "matched_power_tags": [],
                    "matched_weakness_tags": [],
                    "helping_statuses": [],
                    "hindering_statuses": [],
                },
            )
            roll = RollResult(power=1, dice=(3, 4), total=8, outcome="partial_success")
            self.display.print_tag_and_roll(tag_note, roll)

        output = _collect_debug_output(mock_debug)
        self.assertIn("partial_success", output)


class TestConsoleDisplayEffects(unittest.TestCase):
    """测试 print_effects 输出。"""

    def setUp(self):
        self.logger = logging.getLogger("aitrpg.game")
        self.display = ConsoleDisplay(self.logger)

    def test_outputs_effect_summary(self):
        """输出效果摘要。"""
        with patch.object(self.logger, "debug") as mock_debug:
            effect_note = AgentNote(
                reasoning="效果",
                structured={
                    "effects": [
                        {
                            "operation": "inflict_status",
                            "label": "受伤",
                            "effect_type": "attack",
                            "tier": 2,
                        },
                    ]
                },
            )
            self.display.print_effects(effect_note)

        output = _collect_debug_output(mock_debug)
        self.assertIn("受伤", output)
        self.assertIn("attack", output)

    def test_none_effect_note(self):
        """effect_note 为 None 时不报错。"""
        with patch.object(self.logger, "debug"):
            self.display.print_effects(None)


class TestConsoleDisplayEffectsOrQuick(unittest.TestCase):
    """测试 print_effects_or_quick_note 输出。"""

    def setUp(self):
        self.logger = logging.getLogger("aitrpg.game")
        self.display = ConsoleDisplay(self.logger)

    def test_quick_mode_shows_quick_message(self):
        """快速模式下显示快速结算提示。"""
        with patch.object(self.logger, "debug") as mock_debug:
            self.display.print_effects_or_quick_note(None, quick=True)

        output = _collect_debug_output(mock_debug)
        self.assertIn("快速结算", output)

    def test_standard_mode_shows_effects(self):
        """标准模式下显示效果。"""
        with patch.object(self.logger, "debug") as mock_debug:
            effect_note = AgentNote(
                reasoning="效果",
                structured={"effects": [{"operation": "inflict_status", "label": "受伤"}]},
            )
            self.display.print_effects_or_quick_note(effect_note, quick=False)

        output = _collect_debug_output(mock_debug)
        self.assertIn("受伤", output)


class TestConsoleDisplayConsequences(unittest.TestCase):
    """测试 print_consequences 输出。"""

    def setUp(self):
        self.logger = logging.getLogger("aitrpg.game")
        self.display = ConsoleDisplay(self.logger)

    def test_outputs_consequence_summary(self):
        """输出后果摘要。"""
        with patch.object(self.logger, "debug") as mock_debug:
            consequence_note = AgentNote(
                reasoning="后果",
                structured={
                    "consequences": [
                        {"threat_manifested": "保镖介入", "narrative_description": "保镖向前一步"},
                    ]
                },
            )
            self.display.print_consequences(consequence_note)

        output = _collect_debug_output(mock_debug)
        self.assertIn("保镖介入", output)

    def test_none_consequence_note(self):
        """consequence_note 为 None 时不报错。"""
        with patch.object(self.logger, "debug"):
            self.display.print_consequences(None)


class TestConsoleDisplayStrategy(unittest.TestCase):
    """测试 print_strategy 输出。"""

    def setUp(self):
        self.logger = logging.getLogger("aitrpg.game")
        self.display = ConsoleDisplay(self.logger)

    def test_outputs_narrator_strategy(self):
        """输出叙事策略。"""
        with patch.object(self.logger, "debug") as mock_debug:
            narrator_note = AgentNote(
                reasoning="聚焦紧张对峙氛围",
                structured={"scene_update": "气氛紧张"},
            )
            self.display.print_strategy(narrator_note)

        output = _collect_debug_output(mock_debug)
        self.assertIn("叙事策略", output)


class TestConsoleDisplayStatus(unittest.TestCase):
    """测试 print_status 输出。"""

    def setUp(self):
        self.logger = logging.getLogger("aitrpg.game")
        self.display = ConsoleDisplay(self.logger)

    def _make_state(self, **kwargs):
        """创建带角色和挑战的 state mock。"""
        state = MagicMock()
        character = MagicMock()
        character.statuses = kwargs.get("statuses", {})
        character.story_tags = kwargs.get("story_tags", {})
        character.items_visible = kwargs.get("items", {})
        character.name = kwargs.get("name", "Kael")
        state.character = character

        challenge = Challenge(
            name="测试挑战",
            description="测试",
            limits=[Limit(name="伤害", max_tier=3)],
        )
        # 可选：在挑战上设置状态和标签
        challenge.statuses = kwargs.get("challenge_statuses", {})
        challenge.story_tags = kwargs.get("challenge_tags", {})

        scene = MagicMock()
        scene.primary_challenge.return_value = challenge
        scene.scene_items_visible = {}
        state.scene = scene
        return state

    def test_outputs_character_statuses(self):
        """输出角色状态。"""
        with patch.object(self.logger, "debug") as mock_debug:
            state = self._make_state(
                statuses={"受伤": Status(name="受伤", current_tier=2, ticked_boxes={2})},
            )
            self.display.print_status(state)

        output = _collect_debug_output(mock_debug)
        self.assertIn("受伤", output)

    def test_outputs_story_tags(self):
        """输出故事标签。"""
        with patch.object(self.logger, "debug") as mock_debug:
            state = self._make_state(
                story_tags={"掩体": StoryTag(name="掩体", description="翻倒的桌子")},
            )
            self.display.print_status(state)

        output = _collect_debug_output(mock_debug)
        self.assertIn("掩体", output)


if __name__ == "__main__":
    unittest.main()
