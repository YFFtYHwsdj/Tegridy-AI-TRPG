"""自动缓解推演与抵消测试。"""

import unittest
from unittest.mock import MagicMock, patch

from src.models import RollResult
from src.pipeline.move_pipeline import MovePipeline
from tests.helpers import MockLLMClient, make_agent_note, make_test_game_state


class TestAutoMitigation(unittest.TestCase):
    def setUp(self):
        self.mock_llm = MockLLMClient()
        self.state = make_test_game_state()
        self.pipeline = MovePipeline(self.mock_llm, self.state, MagicMock())
        self.ctx = self.state.make_context()

    @patch("src.pipeline.move_pipeline.roll_dice")
    def test_mitigation_failure(self, mock_roll_dice):
        """测试缓解掷骰失败(6-)：无减免。"""
        # Mock 掷骰失败，获得 0 减免效力
        mock_roll_dice.return_value = RollResult(power=1, dice=(2, 3), total=6, outcome="failure")

        outcome_note = make_agent_note(
            structured={
                "consequences": [
                    {
                        "consequence_type": "mechanical",
                        "mitigation_tags": ["防弹衣"],
                        "effects": [{"operation": "inflict_status", "tier": 3, "label": "受伤"}],
                    }
                ]
            }
        )

        self.pipeline._process_auto_mitigation(outcome_note, self.ctx)

        cons = outcome_note.structured["consequences"][0]
        # 应该进行掷骰，power=1 (因为有1个缓解标签)
        mock_roll_dice.assert_called_once_with(1)

        # 失败，没有削弱效果，所以依然是 tier 3
        self.assertEqual(cons["effects"][0]["tier"], 3)
        self.assertIn("获得 0 点减免效力", cons["mitigation_result_text"])

    @patch("src.pipeline.move_pipeline.roll_dice")
    def test_mitigation_partial_success(self, mock_roll_dice):
        """测试缓解掷骰部分成功(7-9)：减免等于效力。"""
        # 2 个标签 -> power 2
        mock_roll_dice.return_value = RollResult(
            power=2, dice=(3, 4), total=9, outcome="partial_success"
        )

        outcome_note = make_agent_note(
            structured={
                "consequences": [
                    {
                        "consequence_type": "mechanical",
                        "mitigation_tags": ["掩体", "钢铁意志"],
                        "effects": [{"operation": "inflict_status", "tier": 3, "label": "受伤"}],
                    }
                ]
            }
        )

        self.pipeline._process_auto_mitigation(outcome_note, self.ctx)

        cons = outcome_note.structured["consequences"][0]
        mock_roll_dice.assert_called_once_with(2)

        # tier 3 减去 power 2 -> 剩余 tier 1
        self.assertEqual(cons["effects"][0]["tier"], 1)
        self.assertIn("获得 2 点减免效力", cons["mitigation_result_text"])

    @patch("src.pipeline.move_pipeline.roll_dice")
    def test_mitigation_full_success_removes_effect(self, mock_roll_dice):
        """测试缓解掷骰完全成功(10+)：效力+1，且若等级归零则移除effect。"""
        # 1 个标签 -> power 1，加上完全成功额外+1，总减免效力为 2
        mock_roll_dice.return_value = RollResult(
            power=1, dice=(5, 6), total=12, outcome="full_success"
        )

        outcome_note = make_agent_note(
            structured={
                "consequences": [
                    {
                        "consequence_type": "mechanical",
                        "mitigation_tags": ["敏捷闪避"],
                        "effects": [{"operation": "inflict_status", "tier": 2, "label": "灼烧"}],
                    }
                ]
            }
        )

        self.pipeline._process_auto_mitigation(outcome_note, self.ctx)

        cons = outcome_note.structured["consequences"][0]

        # 减免效力 2 完全抵消了 tier 2，effect 应该被从列表中移除
        self.assertEqual(len(cons["effects"]), 0)
        self.assertIn("获得 2 点减免效力", cons["mitigation_result_text"])

    @patch("src.pipeline.move_pipeline.roll_dice")
    def test_mitigation_protect_tag(self, mock_roll_dice):
        """测试花费 2 点效力保住一个标签 (scratch_story_tag)。"""
        # 1 个标签，完全成功 -> 2点减免效力
        mock_roll_dice.return_value = RollResult(
            power=1, dice=(6, 6), total=13, outcome="full_success"
        )

        outcome_note = make_agent_note(
            structured={
                "consequences": [
                    {
                        "consequence_type": "mechanical",
                        "mitigation_tags": ["死死抓牢"],
                        "effects": [
                            {"operation": "scratch_story_tag", "story_tag_to_scratch": "神秘护符"}
                        ],
                    }
                ]
            }
        )

        self.pipeline._process_auto_mitigation(outcome_note, self.ctx)

        cons = outcome_note.structured["consequences"][0]
        # scratch_story_tag 被 2 点效力完全抵消，应该被移除
        self.assertEqual(len(cons["effects"]), 0)

    @patch("src.pipeline.move_pipeline.roll_dice")
    def test_mitigation_protect_tag_failure(self, mock_roll_dice):
        """测试只有 1 点效力，不足以保住标签。"""
        # 1 个标签，部分成功 -> 1点减免效力
        mock_roll_dice.return_value = RollResult(
            power=1, dice=(3, 4), total=8, outcome="partial_success"
        )

        outcome_note = make_agent_note(
            structured={
                "consequences": [
                    {
                        "consequence_type": "mechanical",
                        "mitigation_tags": ["死死抓牢"],
                        "effects": [
                            {"operation": "scratch_story_tag", "story_tag_to_scratch": "神秘护符"}
                        ],
                    }
                ]
            }
        )

        self.pipeline._process_auto_mitigation(outcome_note, self.ctx)

        cons = outcome_note.structured["consequences"][0]
        # 只有 1 点效力，不够 2 点抵消，所以 effect 仍然存在
        self.assertEqual(len(cons["effects"]), 1)
        self.assertEqual(cons["effects"][0]["operation"], "scratch_story_tag")


if __name__ == "__main__":
    unittest.main()
