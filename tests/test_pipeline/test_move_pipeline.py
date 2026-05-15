"""MovePipeline 测试 —— 流水线编排、Agent 调用顺序、状态变更验证。

验证 MovePipeline 的核心行为：
    - 标准/快速流水线的 Agent 调用顺序
    - 条件分支（后果生成、校验应用）
    - 拆分 action 的执行和继续性检查
    - validate_and_apply 向 ItemManager 的委托
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from src.models import RollResult
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

        pipeline.outcome_agent = MagicMock()
        pipeline.outcome_agent.execute.return_value = make_agent_note(
            structured={
                "effects": [
                    {"operation": "inflict_status", "target": "挑战", "label": "受伤", "tier": 2}
                ],
                "consequences": [{"threat_manifested": "保镖介入"}],
                "narrative_hints": "测试叙事提示",
            }
        )

        pipeline.narrator = MagicMock()
        pipeline.narrator.execute.return_value = make_agent_note(
            structured={"narrative": "你迅速拔枪...", "revelation_decisions": {}}
        )

        pipeline.item_manager = MagicMock()
        pipeline.clue_manager = MagicMock()
        pipeline.story_tag_manager = MagicMock()
        pipeline.character_manager = MagicMock()
        pipeline.npc_manager = MagicMock()

        return pipeline

    @patch("src.pipeline.move_pipeline.roll_dice")
    def test_calls_all_agents_in_order(self, mock_roll_dice):
        """标准流水线按顺序调用各 Agent。"""
        mock_roll_dice.return_value = RollResult(
            power=1, dice=(4, 3), total=8, outcome="partial_success"
        )
        mock_llm = MockLLMClient()
        state = make_test_game_state()
        pipeline = self._make_pipeline(state, mock_llm)

        intent_note = make_agent_note(structured={"action_type": "combat"})
        ctx = state.make_context("我要拔枪")
        pipeline.run_single_move_pipeline(intent_note, ctx)

        pipeline.tag_agent.execute.assert_called_once()
        pipeline.outcome_agent.execute.assert_called_once()
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
        pipeline.outcome_agent.execute.assert_called_once()

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

        pipeline.outcome_agent.execute.assert_called_once()

    def test_calls_validate_and_apply(self):
        """流水线末端调用 validate_and_apply。"""
        mock_llm = MockLLMClient()
        state = make_test_game_state()
        pipeline = self._make_pipeline(state, mock_llm)
        pipeline.validate_and_apply = MagicMock()

        intent_note = make_agent_note(structured={"action_type": "combat"})
        ctx = state.make_context("我要拔枪")
        pipeline.run_single_move_pipeline(intent_note, ctx)

        pipeline.validate_and_apply.assert_called_once()

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
        self.assertIsNotNone(result.outcome_note)
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

        pipeline.quick_outcome_agent = MagicMock()
        pipeline.quick_outcome_agent.execute.return_value = make_agent_note(
            structured={"consequences": [{"threat_manifested": "保镖介入"}]}
        )

        pipeline.quick_narrator = MagicMock()
        pipeline.quick_narrator.execute.return_value = make_agent_note(
            structured={"narrative": "你迅速拔枪...", "revelation_decisions": {}}
        )

        pipeline.item_manager = MagicMock()

        return pipeline
        return pipeline

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

        pipeline.quick_outcome_agent.execute.assert_called_once()

    def test_uses_quick_narrator(self):
        """快速流水线使用 QuickNarratorAgent。"""
        mock_llm = MockLLMClient()
        state = make_test_game_state()
        pipeline = self._make_pipeline(state, mock_llm)

        intent_note = make_agent_note(structured={"action_type": "combat"})
        ctx = state.make_context("我要拔枪")
        pipeline.run_quick_pipeline(intent_note, ctx)

        pipeline.quick_narrator.execute.assert_called_once()


class TestMovePipelineSplitActions(unittest.TestCase):
    """测试 process_split_actions 拆分 action（统一叙事版）。"""

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

        pipeline.outcome_agent = MagicMock()
        pipeline.outcome_agent.execute.return_value = make_agent_note(
            structured={
                "effects": [{"label": "受伤", "effect_type": "attack", "tier": 1}],
                "narrative_hints": "测试叙事提示",
                "consequences": [],
            }
        )

        # 统一叙述者 mock
        pipeline.narrator = MagicMock()
        pipeline.narrator.execute_split.return_value = make_agent_note(
            structured={"narrative": "统一叙事文本...", "revelation_decisions": {}}
        )

        pipeline.continuation_check = MagicMock()
        pipeline.continuation_check.execute.return_value = make_agent_note(
            structured={"can_continue": True}
        )

        pipeline.item_manager = MagicMock()
        pipeline.clue_manager = MagicMock()
        pipeline.story_tag_manager = MagicMock()
        pipeline.character_manager = MagicMock()
        pipeline.npc_manager = MagicMock()

        return pipeline

    def test_executes_each_sub_action_resolution(self):
        """多个子 action 每个都独立执行解算（tag + roll + effect）。"""
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
        # 每个子行动各调用一次 tag_agent 和 outcome_agent
        self.assertEqual(pipeline.tag_agent.execute.call_count, 2)
        self.assertEqual(pipeline.outcome_agent.execute.call_count, 2)

    def test_narrator_called_once_with_execute_split(self):
        """统一叙述者 execute_split 只调用 1 次（而非 N 次 execute）。"""
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

        # execute_split 调用 1 次
        pipeline.narrator.execute_split.assert_called_once()
        # execute（单次叙述者）不应被调用
        pipeline.narrator.execute.assert_not_called()

    def test_last_result_contains_unified_narrator_note(self):
        """最后一个 result 包含统一叙述者的 narrator_note。"""
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

        # 最后一个 result 有 narrator_note
        self.assertIsNotNone(results[-1].narrator_note)
        self.assertEqual(results[-1].narrator_note.structured.get("narrative"), "统一叙事文本...")
        # 非最后的 result 没有 narrator_note
        self.assertIsNone(results[0].narrator_note)

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
        # 统一叙述者仍然调用 1 次（对已完成的 2 个子行动）
        pipeline.narrator.execute_split.assert_called_once()

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

    def test_validate_and_apply_called_once(self):
        """validate_and_apply 仅在统一叙事后调用一次。"""
        mock_llm = MockLLMClient()
        state = make_test_game_state()
        pipeline = self._make_pipeline(state, mock_llm)

        pipeline.validate_and_apply = MagicMock()

        intent_note = make_agent_note(
            structured={"action_type": "compound", "is_split_action": True}
        )
        split_actions = [
            {"action_type": "combat", "action_summary": "拔枪", "fragment": "拔枪", "_index": 0},
            {"action_type": "combat", "action_summary": "射击", "fragment": "射击", "_index": 1},
        ]

        pipeline.process_split_actions(intent_note, split_actions)

        # validate_and_apply 只调用 1 次（统一叙事后）
        pipeline.validate_and_apply.assert_called_once()


if __name__ == "__main__":
    unittest.main()


class TestMovePipelineApplyEffects(unittest.TestCase):
    def setUp(self):
        from src.pipeline.move_pipeline import MovePipeline
        from tests.helpers import MockLLMClient

        self.llm = MockLLMClient()
        self.state = make_test_game_state()
        self.pipeline = MovePipeline(self.llm, self.state, MagicMock())
        self.pipeline.character_manager = MagicMock()
        self.pipeline.npc_manager = MagicMock()
        self.pipeline.story_tag_manager = MagicMock()
        self.ctx = self.state.make_context()

    def test_apply_effects_inflict_status_character(self):
        effects = [{"operation": "inflict_status", "target": "自身", "label": "受伤", "tier": 2}]
        self.pipeline._apply_effects(effects, self.ctx)
        self.pipeline.character_manager.apply_status.assert_called_with("受伤", 2)

    def test_apply_effects_nudge_status_npc(self):
        from src.models import NPC

        npc = NPC(npc_id="miko", name="Miko")
        self.state.global_state.npcs["miko"] = npc
        self.state.scene.active_npc_ids.append("miko")

        effects = [{"operation": "nudge_status", "target": "Miko", "label": "疲劳"}]
        self.pipeline._apply_effects(effects, self.ctx)
        self.pipeline.npc_manager.nudge_status.assert_called_with("miko", "疲劳")

    def test_apply_effects_reduce_status_character(self):
        effects = [
            {
                "operation": "reduce_status",
                "target": "self",
                "status_to_reduce": "受伤",
                "reduce_by": 1,
            }
        ]
        self.pipeline._apply_effects(effects, self.ctx)
        self.pipeline.character_manager.reduce_status.assert_called_with("受伤", 1)

    def test_apply_effects_add_story_tag_scene(self):
        effects = [
            {
                "operation": "add_story_tag",
                "target": "场景",
                "story_tag_name": "起火",
                "story_tag_description": "大火",
                "is_single_use": False,
            }
        ]
        self.pipeline._apply_effects(effects, self.ctx)
        self.pipeline.story_tag_manager.add_scene_tag.assert_called_with("起火", "大火", False)

    def test_apply_effects_scratch_story_tag_character(self):
        effects = [
            {"operation": "scratch_story_tag", "target": "自身", "story_tag_to_scratch": "起火"}
        ]
        self.pipeline._apply_effects(effects, self.ctx)
        self.pipeline.character_manager.remove_personal_tag.assert_called_with("起火")

    def test_apply_effects_ignores_invalid_target(self):
        effects = [
            {"operation": "inflict_status", "target": "不存在的NPC", "label": "受伤", "tier": 2}
        ]
        self.pipeline._apply_effects(effects, self.ctx)
        self.pipeline.npc_manager.apply_status.assert_not_called()
        self.pipeline.character_manager.apply_status.assert_not_called()

    def test_apply_results(self):
        outcome_note = make_agent_note(
            structured={
                "effects": [
                    {"operation": "inflict_status", "target": "自身", "label": "擦伤", "tier": 1}
                ],
                "consequences": [
                    {
                        "effects": [
                            {
                                "operation": "reduce_status",
                                "target": "自身",
                                "status_to_reduce": "擦伤",
                                "reduce_by": 1,
                            }
                        ]
                    }
                ],
            }
        )
        self.pipeline.apply_results(outcome_note, self.ctx)
        self.pipeline.character_manager.apply_status.assert_called_with("擦伤", 1)
        self.pipeline.character_manager.reduce_status.assert_called_with("擦伤", 1)

    def test_apply_results_with_errors(self):
        outcome_note = make_agent_note(
            structured={
                "effects": [
                    {"operation": "inflict_status", "target": "自身", "label": "受伤", "tier": 2}
                ]
            }
        )
        self.pipeline._apply_effects = MagicMock(return_value=["Error 1"])
        errors = self.pipeline.apply_results(outcome_note, self.ctx)
        self.assertEqual(len(errors), 1)
        self.assertIn("Error 1", errors[0])

    def test_process_auto_mitigation(self):
        import src.engine

        # Ensure roll fails so no mitigation
        with patch("src.pipeline.move_pipeline.roll_dice") as mock_roll:
            mock_roll.return_value = src.models.RollResult(
                power=1, dice=(1, 1), total=2, outcome="failure"
            )
            outcome_note = make_agent_note(
                structured={
                    "consequences": [
                        {
                            "mitigation_tags": ["防御"],
                            "effects": [
                                {
                                    "operation": "inflict_status",
                                    "target": "自身",
                                    "label": "擦伤",
                                    "tier": 1,
                                }
                            ],
                        }
                    ]
                }
            )
            self.pipeline._process_auto_mitigation(outcome_note, self.ctx)
            # failure = 0 mitigation
            effs = outcome_note.structured["consequences"][0]["effects"]
            self.assertEqual(len(effs), 1)
            self.assertEqual(effs[0]["tier"], 1)

        # Ensure roll partial success
        with patch("src.pipeline.move_pipeline.roll_dice") as mock_roll:
            mock_roll.return_value = src.models.RollResult(
                power=1, dice=(3, 4), total=8, outcome="partial_success"
            )
            outcome_note = make_agent_note(
                structured={
                    "consequences": [
                        {
                            "mitigation_tags": ["防御"],
                            "effects": [
                                {
                                    "operation": "inflict_status",
                                    "target": "自身",
                                    "label": "擦伤",
                                    "tier": 1,
                                }
                            ],
                        }
                    ]
                }
            )
            self.pipeline._process_auto_mitigation(outcome_note, self.ctx)
            # partial = power = 1 mitigation, tier 1 - 1 = 0, so it's filtered out
            effs = outcome_note.structured["consequences"][0]["effects"]
            self.assertEqual(len(effs), 0)

    def test_apply_effects_inflict_status_npc(self):
        from src.models import NPC

        npc = NPC(npc_id="miko", name="Miko")
        self.state.global_state.npcs["miko"] = npc
        self.state.scene.active_npc_ids.append("miko")

        effects = [{"operation": "inflict_status", "target": "Miko", "label": "受伤", "tier": 2}]
        self.pipeline._apply_effects(effects, self.ctx)
        self.pipeline.npc_manager.apply_status.assert_called_with("miko", "受伤", 2)

    def test_apply_effects_reduce_status_npc(self):
        from src.models import NPC

        npc = NPC(npc_id="miko", name="Miko")
        self.state.global_state.npcs["miko"] = npc
        self.state.scene.active_npc_ids.append("miko")

        effects = [
            {
                "operation": "reduce_status",
                "target": "Miko",
                "status_to_reduce": "受伤",
                "reduce_by": 1,
            }
        ]
        self.pipeline._apply_effects(effects, self.ctx)
        self.pipeline.npc_manager.reduce_status.assert_called_with("miko", "受伤", 1)

    def test_apply_effects_add_story_tag_npc(self):
        from src.models import NPC

        npc = NPC(npc_id="miko", name="Miko")
        self.state.global_state.npcs["miko"] = npc
        self.state.scene.active_npc_ids.append("miko")

        effects = [
            {
                "operation": "add_story_tag",
                "target": "Miko",
                "story_tag_name": "标记",
                "story_tag_description": "",
                "is_single_use": False,
            }
        ]
        self.pipeline._apply_effects(effects, self.ctx)
        self.pipeline.npc_manager.add_personal_tag.assert_called_with("miko", "标记", "", False)

    def test_apply_effects_scratch_story_tag_npc(self):
        from src.models import NPC

        npc = NPC(npc_id="miko", name="Miko")
        self.state.global_state.npcs["miko"] = npc
        self.state.scene.active_npc_ids.append("miko")

        effects = [
            {"operation": "scratch_story_tag", "target": "Miko", "story_tag_to_scratch": "标记"}
        ]
        self.pipeline._apply_effects(effects, self.ctx)
        self.pipeline.npc_manager.remove_personal_tag.assert_called_with("miko", "标记")

    def test_apply_effects_scratch_story_tag_scene(self):
        effects = [
            {"operation": "scratch_story_tag", "target": "场景", "story_tag_to_scratch": "起火"}
        ]
        self.pipeline._apply_effects(effects, self.ctx)
        self.pipeline.story_tag_manager.remove_scene_tag.assert_called_with("起火")

    def test_apply_effects_discover(self):
        effects = [{"operation": "discover", "target": "自身", "detail": "找到了线索"}]
        with patch("src.pipeline.move_pipeline.log_system") as mock_log:
            self.pipeline._apply_effects(effects, self.ctx)
            mock_log.assert_called()

    def test_apply_effects_extra_feat(self):
        effects = [{"operation": "extra_feat", "target": "自身", "description": "进行了一次跳跃"}]
        with patch("src.pipeline.move_pipeline.log_system") as mock_log:
            self.pipeline._apply_effects(effects, self.ctx)
            mock_log.assert_called()

    def test_apply_effects_exception(self):
        effects = [{"operation": "inflict_status", "target": "自身", "label": "受伤", "tier": 2}]
        self.pipeline.character_manager.apply_status.side_effect = Exception("Test Exception")
        errors = self.pipeline._apply_effects(effects, self.ctx)
        self.assertEqual(len(errors), 1)
        self.assertIn("Test Exception", errors[0])
