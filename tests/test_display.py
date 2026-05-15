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
from src.models import AgentNote, RollResult, Status, StoryTag


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
            self.display.print_outcome(MagicMock())
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

        npc = MagicMock()
        npc.name = "测试NPC"
        npc.statuses = {}
        npc.story_tags = {}
        scene = MagicMock()
        scene.npcs = {npc.name: npc}
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


class TestConsoleDisplayOutcome(unittest.TestCase):
    """测试 print_outcome 输出。"""

    def setUp(self):
        self.logger = logging.getLogger("aitrpg.game")
        self.display = ConsoleDisplay(self.logger)

    def test_outputs_outcome_summary(self):
        """输出效果和后果摘要。"""
        with patch.object(self.logger, "debug") as mock_debug:
            outcome_note = AgentNote(
                reasoning="结算推演",
                structured={
                    "effects": [
                        {
                            "operation": "inflict_status",
                            "label": "受伤",
                            "effect_type": "attack",
                            "tier": 2,
                        },
                    ],
                    "consequences": [
                        {"threat_manifested": "保镖介入", "narrative_description": "保镖向前一步"},
                    ],
                },
            )
            self.display.print_outcome(outcome_note)

        output = _collect_debug_output(mock_debug)
        self.assertIn("受伤", output)
        self.assertIn("attack", output)
        self.assertIn("保镖介入", output)

    def test_none_outcome_note(self):
        """outcome_note 为 None 时不报错。"""
        with patch.object(self.logger, "debug") as mock_debug:
            self.display.print_outcome(None)
            mock_debug.assert_not_called()


class TestConsoleDisplayStrategy(unittest.TestCase):
    """测试 print_strategy 输出。"""

    def setUp(self):
        self.logger = logging.getLogger("aitrpg.game")
        self.display = ConsoleDisplay(self.logger)

    def test_outputs_narrator_strategy(self):
        """输出叙事策略（从 reasoning 字段截取）。"""
        with patch.object(self.logger, "debug") as mock_debug:
            narrator_note = AgentNote(
                reasoning="聚焦紧张对峙氛围，渲染环境压迫感",
                structured={},
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

        npc = MagicMock()
        npc.name = "测试NPC"
        npc.statuses = kwargs.get("challenge_statuses", {})
        npc.story_tags = kwargs.get("challenge_tags", {})

        scene = MagicMock()
        scene.npcs = {npc.name: npc}
        scene.active_npc_ids = ["test_npc_id"]
        scene.scene_items_visible = {}

        global_state = MagicMock()
        global_state.npcs = {"test_npc_id": npc}

        state.scene = scene
        state.global_state = global_state
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
            state = self._make_state()
            state.scene.story_tags = {"掩体": StoryTag(name="掩体", description="翻倒的桌子")}
            self.display.print_status(state)

        output = _collect_debug_output(mock_debug)
        self.assertIn("掩体", output)

    def test_print_status_no_character(self):
        with patch.object(self.logger, "debug") as mock_debug:
            state = self._make_state()
            state.character = None
            self.display.print_status(state)
        output = _collect_debug_output(mock_debug)
        self.assertEqual(output, "")

    def test_print_status_with_items(self):
        from src.models import GameItem

        with patch.object(self.logger, "debug") as mock_debug:
            state = self._make_state(items={"item1": GameItem(item_id="1", name="物品1")})
            self.display.print_status(state)
        output = _collect_debug_output(mock_debug)
        self.assertIn("物品1", output)

    def test_print_status_no_story_tags(self):
        with patch.object(self.logger, "debug") as mock_debug:
            state = self._make_state()
            state.scene.story_tags = {}
            state.character.story_tags = {}
            self.display.print_status(state)
        output = _collect_debug_output(mock_debug)
        self.assertIn("故事标签: （无）", output)

    def test_print_status_npc_with_status(self):
        with patch.object(self.logger, "debug") as mock_debug:
            state = self._make_state(
                challenge_statuses={"受伤": Status(name="受伤", current_tier=2, ticked_boxes={2})}
            )
            self.display.print_status(state)
        output = _collect_debug_output(mock_debug)
        self.assertIn("受伤", output)


class TestConsoleDisplayExtra(unittest.TestCase):
    def setUp(self):
        self.logger = logging.getLogger("aitrpg.game")
        self.display = ConsoleDisplay(self.logger)

    def test_print_tag_and_roll_with_status(self):
        with patch.object(self.logger, "debug") as mock_debug:
            tag_note = AgentNote(
                reasoning="",
                structured={
                    "matched_power_tags": [],
                    "matched_weakness_tags": [],
                    "helping_statuses": [{"name": "专注"}],
                    "hindering_statuses": [{"name": "流血"}],
                },
            )
            self.display.print_tag_and_roll(
                tag_note, RollResult(power=1, dice=(1, 1), total=3, outcome="failure")
            )
        output = _collect_debug_output(mock_debug)
        self.assertIn("专注", output)
        self.assertIn("流血", output)

    def test_print_outcome_quick_no_effects(self):
        with patch.object(self.logger, "debug") as mock_debug:
            outcome_note = AgentNote(reasoning="", structured={"effects": [], "consequences": []})
            self.display.print_outcome(outcome_note, quick=True)
        output = _collect_debug_output(mock_debug)
        self.assertIn("快速结算不花费力量", output)

    def test_print_outcome_no_effects(self):
        with patch.object(self.logger, "debug") as mock_debug:
            outcome_note = AgentNote(reasoning="", structured={"effects": [], "consequences": []})
            self.display.print_outcome(outcome_note, quick=False)
        output = _collect_debug_output(mock_debug)
        self.assertIn("效果: 无", output)

    def test_split_action_messages(self):
        with patch.object(self.logger, "debug") as mock_debug:
            self.display.print_split_action_header(3)
            self.display.print_split_sub_header(1, 3, "冲锋")
            self.display.print_split_blocked("冲锋", "被绊倒")
            self.display.print_incapacitated_break()
        output = _collect_debug_output(mock_debug)
        self.assertIn("拆分为 %d 个子行动", output)
        self.assertIn("子行动 %d/%d: %s", output)
        self.assertIn("无法继续: %s", output)
        self.assertIn("角色已丧失行动能力，剩余子行动中断", output)


if __name__ == "__main__":
    unittest.main()
