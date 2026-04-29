"""MovePipeline 测试 —— 流水线编排、Agent 调用顺序、状态变更验证。

验证 MovePipeline 的核心行为：
    - 标准/快速流水线的 Agent 调用顺序
    - 条件分支（后果生成、校验应用）
    - 拆分 action 的执行和继续性检查
    - 揭示和物品转移的状态变更
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from src.models import Clue, GameItem, RollResult
from src.pipeline.move_pipeline import MovePipeline
from src.pipeline.pipeline_result import PipelineResult
from tests.helpers import (
    MockLLMClient,
    make_agent_note,
    make_test_game_state,
)


class TestMovePipelineTagAndRoll(unittest.TestCase):
    """测试 _run_tag_and_roll 阶段。"""

    def test_calls_tag_agent(self):
        """验证 tag_agent.execute 被调用。"""
        mock_llm = MockLLMClient()
        state = make_test_game_state()
        pipeline = MovePipeline(mock_llm, state, MagicMock())

        # Mock tag_agent 返回预设结果
        pipeline.tag_agent = MagicMock()
        pipeline.tag_agent.execute.return_value = make_agent_note(
            structured={
                "matched_power_tags": [{"name": "快速拔枪"}],
                "matched_weakness_tags": [],
                "helping_statuses": [],
                "hindering_statuses": [],
            }
        )

        intent_note = make_agent_note(structured={"action_type": "combat"})
        ctx = state.make_context("我要拔枪")
        pipeline._run_tag_and_roll(intent_note, ctx)

        pipeline.tag_agent.execute.assert_called_once()

    def test_calculates_power_from_tags(self):
        """验证力量计算使用 tag_note 中的标签。"""
        mock_llm = MockLLMClient()
        state = make_test_game_state()
        pipeline = MovePipeline(mock_llm, state, MagicMock())

        pipeline.tag_agent = MagicMock()
        pipeline.tag_agent.execute.return_value = make_agent_note(
            structured={
                "matched_power_tags": [{"name": "快速拔枪"}, {"name": "前公司安保"}],
                "matched_weakness_tags": [],
                "helping_statuses": [],
                "hindering_statuses": [],
            }
        )

        intent_note = make_agent_note(structured={"action_type": "combat"})
        ctx = state.make_context("我要拔枪")
        _, roll = pipeline._run_tag_and_roll(intent_note, ctx)

        # 2 个力量标签，无弱点，无状态影响 → power = 2
        self.assertEqual(roll.power, 2)

    def test_returns_roll_result(self):
        """验证返回有效的 RollResult。"""
        mock_llm = MockLLMClient()
        state = make_test_game_state()
        pipeline = MovePipeline(mock_llm, state, MagicMock())

        pipeline.tag_agent = MagicMock()
        pipeline.tag_agent.execute.return_value = make_agent_note(
            structured={
                "matched_power_tags": [],
                "matched_weakness_tags": [],
                "helping_statuses": [],
                "hindering_statuses": [],
            }
        )

        intent_note = make_agent_note(structured={"action_type": "combat"})
        ctx = state.make_context("我要拔枪")
        tag_note, roll = pipeline._run_tag_and_roll(intent_note, ctx)

        self.assertIsNotNone(tag_note)
        self.assertIsInstance(roll, RollResult)
        self.assertEqual(roll.power, 1)  # 无标签时默认 power=1


class TestMovePipelineSingleMove(unittest.TestCase):
    """测试 run_single_move_pipeline 完整流水线。"""

    def _make_pipeline(self, state, mock_llm: MockLLMClient) -> MovePipeline:
        """创建带 Mock Agent 的流水线。"""
        pipeline = MovePipeline(mock_llm, state, MagicMock())

        pipeline.tag_agent = MagicMock()
        pipeline.tag_agent.execute.return_value = make_agent_note(
            structured={
                "matched_power_tags": [{"name": "快速拔枪"}],
                "matched_weakness_tags": [],
                "helping_statuses": [],
                "hindering_statuses": [],
            }
        )

        pipeline.effect_agent = MagicMock()
        pipeline.effect_agent.execute.return_value = make_agent_note(
            structured={
                "effects": [
                    {"operation": "inflict_status", "target": "挑战", "label": "受伤", "tier": 2}
                ]
            }
        )

        pipeline.consequence_agent = MagicMock()
        pipeline.consequence_agent.execute.return_value = make_agent_note(
            structured={"consequences": [{"threat_manifested": "保镖介入"}]}
        )

        pipeline.narrator = MagicMock()
        pipeline.narrator.execute.return_value = make_agent_note(
            structured={"narrative": "你迅速拔枪...", "revelation_decisions": {}}
        )

        pipeline.validator = MagicMock()
        pipeline.validator.execute.return_value = make_agent_note(structured={"verdict": "accept"})

        return pipeline

    def test_calls_all_agents_in_order(self):
        """标准流水线按顺序调用各 Agent。"""
        mock_llm = MockLLMClient()
        state = make_test_game_state()
        pipeline = self._make_pipeline(state, mock_llm)

        intent_note = make_agent_note(structured={"action_type": "combat"})
        ctx = state.make_context("我要拔枪")
        pipeline.run_single_move_pipeline(intent_note, ctx)

        pipeline.tag_agent.execute.assert_called_once()
        pipeline.effect_agent.execute.assert_called_once()
        pipeline.consequence_agent.execute.assert_called_once()
        pipeline.narrator.execute.assert_called_once()

    @patch("src.pipeline.move_pipeline.roll_dice")
    def test_skips_consequence_on_full_success(self, mock_roll_dice):
        """完全成功时不调用 ConsequenceAgent。"""
        mock_roll_dice.return_value = RollResult(
            power=3, dice=(6, 6), total=15, outcome="full_success"
        )
        mock_llm = MockLLMClient()
        state = make_test_game_state()
        pipeline = self._make_pipeline(state, mock_llm)

        intent_note = make_agent_note(structured={"action_type": "combat"})
        ctx = state.make_context("我要拔枪")
        result = pipeline.run_single_move_pipeline(intent_note, ctx)

        self.assertEqual(result.roll.outcome, "full_success")
        pipeline.consequence_agent.execute.assert_not_called()

    @patch("src.pipeline.move_pipeline.roll_dice")
    def test_calls_consequence_on_partial_success(self, mock_roll_dice):
        """部分成功时调用 ConsequenceAgent。"""
        mock_roll_dice.return_value = RollResult(
            power=1, dice=(3, 3), total=7, outcome="partial_success"
        )
        mock_llm = MockLLMClient()
        state = make_test_game_state()
        pipeline = self._make_pipeline(state, mock_llm)

        intent_note = make_agent_note(structured={"action_type": "combat"})
        ctx = state.make_context("我要拔枪")
        pipeline.run_single_move_pipeline(intent_note, ctx)

        pipeline.consequence_agent.execute.assert_called_once()

    def test_skips_validator_when_no_revelations(self):
        """无揭示/转移时跳过 validator，直接应用。"""
        mock_llm = MockLLMClient()
        state = make_test_game_state()
        pipeline = self._make_pipeline(state, mock_llm)

        intent_note = make_agent_note(structured={"action_type": "combat"})
        ctx = state.make_context("我要拔枪")
        pipeline.run_single_move_pipeline(intent_note, ctx)

        pipeline.validator.execute.assert_not_called()

    def test_calls_validator_when_has_revelations(self):
        """有揭示操作时调用 validator。"""
        mock_llm = MockLLMClient()
        state = make_test_game_state()
        pipeline = self._make_pipeline(state, mock_llm)

        # 让 narrator 返回有揭示的 note
        pipeline.narrator.execute.return_value = make_agent_note(
            structured={
                "narrative": "你发现了线索",
                "revelation_decisions": {"reveal_clue_ids": ["hidden_clue"]},
            }
        )
        state.scene.clues_hidden["hidden_clue"] = Clue(clue_id="hidden_clue", name="隐藏线索")

        intent_note = make_agent_note(structured={"action_type": "combat"})
        ctx = state.make_context("我要拔枪")
        pipeline.run_single_move_pipeline(intent_note, ctx)

        pipeline.validator.execute.assert_called_once()

    @patch("src.pipeline.move_pipeline.roll_dice")
    def test_returns_pipeline_result(self, mock_roll_dice):
        """返回包含所有阶段数据的 PipelineResult。"""
        mock_roll_dice.return_value = RollResult(
            power=1, dice=(3, 3), total=7, outcome="partial_success"
        )
        mock_llm = MockLLMClient()
        state = make_test_game_state()
        pipeline = self._make_pipeline(state, mock_llm)

        intent_note = make_agent_note(structured={"action_type": "combat"})
        ctx = state.make_context("我要拔枪")
        result = pipeline.run_single_move_pipeline(intent_note, ctx)

        self.assertIsInstance(result, PipelineResult)
        self.assertIsNotNone(result.tag_note)
        self.assertIsNotNone(result.roll)
        self.assertIsNotNone(result.effect_note)
        self.assertIsNotNone(result.consequence_note)
        self.assertIsNotNone(result.narrator_note)


class TestMovePipelineQuickPipeline(unittest.TestCase):
    """测试 run_quick_pipeline 快速流水线。"""

    def _make_pipeline(self, state, mock_llm: MockLLMClient) -> MovePipeline:
        """创建带 Mock Agent 的流水线。"""
        pipeline = MovePipeline(mock_llm, state, MagicMock())

        pipeline.tag_agent = MagicMock()
        pipeline.tag_agent.execute.return_value = make_agent_note(
            structured={
                "matched_power_tags": [{"name": "快速拔枪"}],
                "matched_weakness_tags": [],
                "helping_statuses": [],
                "hindering_statuses": [],
            }
        )

        pipeline.quick_consequence_agent = MagicMock()
        pipeline.quick_consequence_agent.execute.return_value = make_agent_note(
            structured={"consequences": [{"threat_manifested": "保镖介入"}]}
        )

        pipeline.quick_narrator = MagicMock()
        pipeline.quick_narrator.execute.return_value = make_agent_note(
            structured={"narrative": "你迅速拔枪...", "revelation_decisions": {}}
        )

        pipeline.validator = MagicMock()
        pipeline.validator.execute.return_value = make_agent_note(structured={"verdict": "accept"})

        return pipeline

    def test_skips_effect_agent(self):
        """快速流水线不调用 EffectActualizationAgent。"""
        mock_llm = MockLLMClient()
        state = make_test_game_state()
        pipeline = self._make_pipeline(state, mock_llm)

        intent_note = make_agent_note(structured={"action_type": "combat"})
        ctx = state.make_context("我要拔枪")
        result = pipeline.run_quick_pipeline(intent_note, ctx)

        self.assertIsNone(result.effect_note)

    @patch("src.pipeline.move_pipeline.roll_dice")
    def test_uses_quick_consequence(self, mock_roll_dice):
        """快速流水线使用 QuickConsequenceAgent。"""
        mock_roll_dice.return_value = RollResult(
            power=1, dice=(3, 3), total=7, outcome="partial_success"
        )
        mock_llm = MockLLMClient()
        state = make_test_game_state()
        pipeline = self._make_pipeline(state, mock_llm)

        intent_note = make_agent_note(structured={"action_type": "combat"})
        ctx = state.make_context("我要拔枪")
        pipeline.run_quick_pipeline(intent_note, ctx)

        pipeline.quick_consequence_agent.execute.assert_called_once()

    def test_uses_quick_narrator(self):
        """快速流水线使用 QuickNarratorAgent。"""
        mock_llm = MockLLMClient()
        state = make_test_game_state()
        pipeline = self._make_pipeline(state, mock_llm)

        intent_note = make_agent_note(structured={"action_type": "combat"})
        ctx = state.make_context("我要拔枪")
        pipeline.run_quick_pipeline(intent_note, ctx)

        pipeline.quick_narrator.execute.assert_called_once()


class TestMovePipelineValidateAndApply(unittest.TestCase):
    """测试 validate_and_apply 方法。"""

    def _make_pipeline(self, state) -> MovePipeline:
        """创建带 Mock validator 的流水线。"""
        mock_llm = MockLLMClient()
        pipeline = MovePipeline(mock_llm, state, MagicMock())

        pipeline.validator = MagicMock()
        pipeline.validator.execute.return_value = make_agent_note(structured={"verdict": "accept"})

        return pipeline

    def test_rejects_invalid_revelation(self):
        """validator 返回 reject 时不执行揭示。"""
        state = make_test_game_state()
        pipeline = self._make_pipeline(state)
        pipeline.validator.execute.return_value = make_agent_note(structured={"verdict": "reject"})

        narrator_note = make_agent_note(
            structured={
                "narrative": "你发现了线索",
                "revelation_decisions": {"reveal_clue_ids": ["hidden_clue"]},
            }
        )

        # 预先放置一个隐藏线索
        state.scene.clues_hidden["hidden_clue"] = Clue(clue_id="hidden_clue", name="隐藏线索")

        pipeline.validate_and_apply(narrator_note)

        # 线索应仍在隐藏中
        self.assertIn("hidden_clue", state.scene.clues_hidden)
        self.assertNotIn("hidden_clue", state.scene.clues_visible)

    def test_apply_revelations_moves_clue(self):
        """揭示线索从 clues_hidden 移动到 clues_visible。"""
        state = make_test_game_state()
        pipeline = self._make_pipeline(state)

        state.scene.clues_hidden["secret"] = Clue(clue_id="secret", name="秘密")

        narrator_note = make_agent_note(
            structured={
                "narrative": "你发现了秘密",
                "revelation_decisions": {"reveal_clue_ids": ["secret"]},
            }
        )

        pipeline.validate_and_apply(narrator_note)

        self.assertNotIn("secret", state.scene.clues_hidden)
        self.assertIn("secret", state.scene.clues_visible)

    def test_apply_revelations_moves_scene_item(self):
        """揭示物品从 scene_items_hidden 移动到 scene_items_visible。"""
        state = make_test_game_state()
        pipeline = self._make_pipeline(state)

        state.scene.scene_items_hidden["medkit"] = GameItem(item_id="medkit", name="急救包")

        narrator_note = make_agent_note(
            structured={
                "narrative": "你发现了急救包",
                "revelation_decisions": {"reveal_item_ids": ["medkit"]},
            }
        )

        pipeline.validate_and_apply(narrator_note)

        self.assertNotIn("medkit", state.scene.scene_items_hidden)
        self.assertIn("medkit", state.scene.scene_items_visible)

    def test_apply_revelations_moves_npc_hidden_item(self):
        """揭示 NPC 隐藏物品到 NPC 可见物品。"""
        state = make_test_game_state()
        pipeline = self._make_pipeline(state)

        from src.models import NPC

        npc = NPC(npc_id="miko", name="Miko")
        npc.items_hidden["key"] = GameItem(item_id="key", name="钥匙")
        state.scene.npcs["miko"] = npc

        narrator_note = make_agent_note(
            structured={
                "narrative": "你发现了钥匙",
                "revelation_decisions": {"reveal_item_ids": ["key"]},
            }
        )

        pipeline.validate_and_apply(narrator_note)

        self.assertNotIn("key", npc.items_hidden)
        self.assertIn("key", npc.items_visible)


class TestMovePipelineSplitActions(unittest.TestCase):
    """测试 process_split_actions 拆分 action。"""

    def _make_pipeline(self, state, mock_llm: MockLLMClient) -> MovePipeline:
        """创建带 Mock Agent 的流水线。"""
        pipeline = MovePipeline(mock_llm, state, MagicMock())

        pipeline.tag_agent = MagicMock()
        pipeline.tag_agent.execute.return_value = make_agent_note(
            structured={
                "matched_power_tags": [{"name": "快速拔枪"}],
                "matched_weakness_tags": [],
                "helping_statuses": [],
                "hindering_statuses": [],
            }
        )

        pipeline.effect_agent = MagicMock()
        pipeline.effect_agent.execute.return_value = make_agent_note(structured={"effects": []})

        pipeline.consequence_agent = MagicMock()
        pipeline.consequence_agent.execute.return_value = make_agent_note(
            structured={"consequences": []}
        )

        pipeline.narrator = MagicMock()
        pipeline.narrator.execute.return_value = make_agent_note(
            structured={"narrative": "...", "revelation_decisions": {}}
        )

        pipeline.continuation_check = MagicMock()
        pipeline.continuation_check.execute.return_value = make_agent_note(
            structured={"can_continue": True}
        )

        pipeline.validator = MagicMock()
        pipeline.validator.execute.return_value = make_agent_note(structured={"verdict": "accept"})

        return pipeline

    def test_executes_each_sub_action(self):
        """多个子 action 每个都执行一次流水线。"""
        mock_llm = MockLLMClient()
        state = make_test_game_state()
        pipeline = self._make_pipeline(state, mock_llm)

        intent_note = make_agent_note(
            structured={"action_type": "compound", "is_split_action": True}
        )
        split_actions = [
            {"action_type": "combat", "action_summary": "拔枪", "fragment": "拔枪", "_index": 0},
            {"action_type": "combat", "action_summary": "射击", "fragment": "射击", "_index": 1},
        ]

        results = pipeline.process_split_actions(intent_note, split_actions)

        self.assertEqual(len(results), 2)
        self.assertEqual(pipeline.tag_agent.execute.call_count, 2)

    def test_stops_on_continuation_rejection(self):
        """continuation_check 返回不可继续时中断后续子 action。"""
        mock_llm = MockLLMClient()
        state = make_test_game_state()
        pipeline = self._make_pipeline(state, mock_llm)

        # 第二个子 action 时返回不可继续
        pipeline.continuation_check.execute.side_effect = [
            make_agent_note(structured={"can_continue": True}),
            make_agent_note(structured={"can_continue": False}),
        ]

        intent_note = make_agent_note(
            structured={"action_type": "compound", "is_split_action": True}
        )
        split_actions = [
            {"action_type": "combat", "action_summary": "拔枪", "fragment": "拔枪", "_index": 0},
            {"action_type": "combat", "action_summary": "射击", "fragment": "射击", "_index": 1},
            {"action_type": "combat", "action_summary": "逃跑", "fragment": "逃跑", "_index": 2},
        ]

        results = pipeline.process_split_actions(intent_note, split_actions)

        # 只执行了前两个（第二个检查返回 False 后中断）
        self.assertEqual(len(results), 2)

    def test_passes_last_sub_summary(self):
        """每一步传递上一步的摘要给 continuation_check。"""
        mock_llm = MockLLMClient()
        state = make_test_game_state()
        pipeline = self._make_pipeline(state, mock_llm)

        intent_note = make_agent_note(
            structured={"action_type": "compound", "is_split_action": True}
        )
        split_actions = [
            {"action_type": "combat", "action_summary": "拔枪", "fragment": "拔枪", "_index": 0},
            {"action_type": "combat", "action_summary": "射击", "fragment": "射击", "_index": 1},
        ]

        pipeline.process_split_actions(intent_note, split_actions)

        # 对于2个子action，continuation_check在第2步前被调用1次
        # 应收到第一步的摘要（第3个位置参数）
        self.assertEqual(pipeline.continuation_check.execute.call_count, 1)
        call_args = pipeline.continuation_check.execute.call_args.args
        self.assertEqual(len(call_args), 3)
        # 第3个位置参数是上一步的摘要，包含掷骰结果信息
        self.assertIsNotNone(call_args[2])
        self.assertIn("掷骰结果", call_args[2])


if __name__ == "__main__":
    unittest.main()
