"""ConsoleDisplay 测试 —— 调试模式下的信息输出验证。

验证 ConsoleDisplay 在 debug_mode 开关下的行为：
    - debug_mode=False 时所有输出被跳过
    - debug_mode=True 时正确格式化并输出各阶段信息
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from src.display.console import ConsoleDisplay
from src.models import AgentNote, RollResult, Status, StoryTag


class TestConsoleDisplayDebugMode(unittest.TestCase):
    """测试调试模式开关。"""

    def test_debug_mode_false_skips_all_output(self):
        """非调试模式下所有 print 方法不输出。"""
        display = ConsoleDisplay(debug_mode=False)

        with patch("builtins.print") as mock_print:
            display.print_tag_and_roll(MagicMock(), MagicMock())
            display.print_effects(MagicMock())
            display.print_consequences(MagicMock())
            display.print_strategy(MagicMock())
            display.print_status(MagicMock())

        mock_print.assert_not_called()

    def test_debug_mode_true_outputs_content(self):
        """调试模式下有输出。"""
        display = ConsoleDisplay(debug_mode=True)

        with patch("builtins.print") as mock_print:
            tag_note = AgentNote(
                reasoning="标签匹配",
                structured={
                    "matched_power_tags": [{"name": "快速拔枪"}],
                    "matched_weakness_tags": [],
                    "helping_statuses": [],
                    "hindering_statuses": [],
                },
            )
            roll = RollResult(power=2, dice=(5, 4), total=11, outcome="full_success")
            display.print_tag_and_roll(tag_note, roll)

        self.assertTrue(mock_print.called)


class TestConsoleDisplayTagAndRoll(unittest.TestCase):
    """测试 print_tag_and_roll 输出。"""

    def test_outputs_matched_tags(self):
        """输出匹配的标签名称。"""
        display = ConsoleDisplay(debug_mode=True)

        with patch("builtins.print") as mock_print:
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
            display.print_tag_and_roll(tag_note, roll)

        output = "\n".join(str(call.args[0]) for call in mock_print.call_args_list if call.args)
        self.assertIn("快速拔枪", output)
        self.assertIn("信用破产", output)

    def test_outputs_roll_info(self):
        """输出掷骰结果。"""
        display = ConsoleDisplay(debug_mode=True)

        with patch("builtins.print") as mock_print:
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
            display.print_tag_and_roll(tag_note, roll)

        output = "\n".join(str(call.args[0]) for call in mock_print.call_args_list if call.args)
        self.assertIn("partial_success", output)


class TestConsoleDisplayEffects(unittest.TestCase):
    """测试 print_effects 输出。"""

    def test_outputs_effect_summary(self):
        """输出效果摘要。"""
        display = ConsoleDisplay(debug_mode=True)

        with patch("builtins.print") as mock_print:
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
            display.print_effects(effect_note)

        output = "\n".join(str(call.args[0]) for call in mock_print.call_args_list if call.args)
        self.assertIn("受伤", output)
        self.assertIn("attack", output)

    def test_none_effect_note(self):
        """effect_note 为 None 时不报错。"""
        display = ConsoleDisplay(debug_mode=True)

        with patch("builtins.print"):
            display.print_effects(None)


class TestConsoleDisplayEffectsOrQuick(unittest.TestCase):
    """测试 print_effects_or_quick_note 输出。"""

    def test_quick_mode_shows_quick_message(self):
        """快速模式下显示快速结算提示。"""
        display = ConsoleDisplay(debug_mode=True)

        with patch("builtins.print") as mock_print:
            display.print_effects_or_quick_note(None, quick=True)

        output = "\n".join(str(call.args[0]) for call in mock_print.call_args_list if call.args)
        self.assertIn("快速结算", output)

    def test_standard_mode_shows_effects(self):
        """标准模式下显示效果。"""
        display = ConsoleDisplay(debug_mode=True)

        with patch("builtins.print") as mock_print:
            effect_note = AgentNote(
                reasoning="效果",
                structured={"effects": [{"operation": "inflict_status", "label": "受伤"}]},
            )
            display.print_effects_or_quick_note(effect_note, quick=False)

        output = "\n".join(str(call.args[0]) for call in mock_print.call_args_list if call.args)
        self.assertIn("受伤", output)


class TestConsoleDisplayConsequences(unittest.TestCase):
    """测试 print_consequences 输出。"""

    def test_outputs_consequence_summary(self):
        """输出后果摘要。"""
        display = ConsoleDisplay(debug_mode=True)

        with patch("builtins.print") as mock_print:
            consequence_note = AgentNote(
                reasoning="后果",
                structured={
                    "consequences": [
                        {"threat_manifested": "保镖介入", "narrative_description": "保镖向前一步"},
                    ]
                },
            )
            display.print_consequences(consequence_note)

        output = "\n".join(str(call.args[0]) for call in mock_print.call_args_list if call.args)
        self.assertIn("保镖介入", output)

    def test_none_consequence_note(self):
        """consequence_note 为 None 时不报错。"""
        display = ConsoleDisplay(debug_mode=True)

        with patch("builtins.print"):
            display.print_consequences(None)


class TestConsoleDisplayStrategy(unittest.TestCase):
    """测试 print_strategy 输出。"""

    def test_outputs_narrator_strategy(self):
        """输出叙事策略。"""
        display = ConsoleDisplay(debug_mode=True)

        with patch("builtins.print") as mock_print:
            narrator_note = AgentNote(
                reasoning="聚焦紧张对峙氛围",
                structured={"scene_update": "气氛紧张"},
            )
            display.print_strategy(narrator_note)

        output = "\n".join(str(call.args[0]) for call in mock_print.call_args_list if call.args)
        self.assertIn("叙事策略", output)


class TestConsoleDisplayStatus(unittest.TestCase):
    """测试 print_status 输出。"""

    def test_outputs_character_statuses(self):
        """输出角色状态。"""
        display = ConsoleDisplay(debug_mode=True)

        with patch("builtins.print") as mock_print:
            state = MagicMock()
            character = MagicMock()
            character.statuses = {"受伤": Status(name="受伤", current_tier=2, ticked_boxes={2})}
            character.story_tags = {}
            state.character = character
            state.scene = MagicMock()
            state.scene.active_challenges = {}
            display.print_status(state)

        output = "\n".join(str(call.args[0]) for call in mock_print.call_args_list if call.args)
        self.assertIn("受伤", output)

    def test_outputs_story_tags(self):
        """输出故事标签。"""
        display = ConsoleDisplay(debug_mode=True)

        with patch("builtins.print") as mock_print:
            state = MagicMock()
            character = MagicMock()
            character.statuses = {}
            character.story_tags = {"掩体": StoryTag(name="掩体", description="翻倒的桌子")}
            state.character = character
            state.scene = MagicMock()
            state.scene.active_challenges = {}
            display.print_status(state)

        output = "\n".join(str(call.args[0]) for call in mock_print.call_args_list if call.args)
        self.assertIn("掩体", output)


if __name__ == "__main__":
    unittest.main()
