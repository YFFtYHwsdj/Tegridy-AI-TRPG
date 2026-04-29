"""EffectActualizationAgent 测试 —— 效果推演 Agent 的 prompt 组装和短路逻辑验证。

验证 execute 方法：
    - 失败 outcome 时短路返回，不调用 LLM
    - 成功时调用 LLM 并传入完整上下文
    - prompt 包含掷骰结果、挑战状态、标签匹配结果
"""

from __future__ import annotations

import unittest

from src.agents.effect_actualization import EffectActualizationAgent
from tests.helpers import MockLLMClient, make_agent_note, make_roll_result, make_test_context


class TestEffectActualizationAgentExecute(unittest.TestCase):
    """测试 EffectActualizationAgent.execute 的行为。"""

    def test_failure_outcome_returns_empty_effects_without_llm_call(self):
        """掷骰失败时不调用 LLM，直接返回空效果。"""
        mock_llm = MockLLMClient()
        agent = EffectActualizationAgent(mock_llm)
        ctx = make_test_context()
        intent_note = make_agent_note(structured={"action_type": "combat"})
        tag_note = make_agent_note(structured={"matched_power_tags": []})
        roll = make_roll_result(outcome="failure", power=0)

        result = agent.execute(intent_note, tag_note, roll, ctx)

        self.assertEqual(len(mock_llm.call_history), 0)
        self.assertEqual(result.reasoning, "掷骰结果为失败，不产生效果")
        self.assertEqual(result.structured["effects"], [])

    def test_success_calls_llm_with_full_context(self):
        """成功时调用 LLM，prompt 包含完整上下文。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    "=====REASONING=====\n推演效果\n=====STRUCTURED=====\n"
                    '{"effects": [{"operation": "inflict_status", "target": "挑战", "label": "受伤", "tier": 2}]}',
                    {},
                )
            ]
        )
        agent = EffectActualizationAgent(mock_llm)
        ctx = make_test_context()
        intent_note = make_agent_note(
            structured={"action_type": "combat", "action_summary": "拔枪"}
        )
        tag_note = make_agent_note(structured={"matched_power_tags": [{"name": "快速拔枪"}]})
        roll = make_roll_result(outcome="full_success", power=2)

        agent.execute(intent_note, tag_note, roll, ctx)

        self.assertEqual(len(mock_llm.call_history), 1)

    def test_execute_includes_roll_info(self):
        """user_message 包含掷骰结果详情。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '=====REASONING=====\n推演\n=====STRUCTURED=====\n{"effects": []}',
                    {},
                )
            ]
        )
        agent = EffectActualizationAgent(mock_llm)
        ctx = make_test_context()
        intent_note = make_agent_note(structured={"action_type": "combat"})
        tag_note = make_agent_note(structured={"matched_power_tags": []})
        roll = make_roll_result(outcome="partial_success", power=1, dice=(4, 3))

        agent.execute(intent_note, tag_note, roll, ctx)

        user_msg = mock_llm.call_history[0]["user_message"]
        self.assertIn("power=1", user_msg)
        self.assertIn("(4, 3)", user_msg)
        self.assertIn("partial_success", user_msg)

    def test_execute_includes_challenge_state(self):
        """user_message 包含挑战状态和极限差距。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '=====REASONING=====\n推演\n=====STRUCTURED=====\n{"effects": []}',
                    {},
                )
            ]
        )
        agent = EffectActualizationAgent(mock_llm)
        ctx = make_test_context()
        intent_note = make_agent_note(structured={"action_type": "combat"})
        tag_note = make_agent_note(structured={"matched_power_tags": []})
        roll = make_roll_result(outcome="partial_success")

        agent.execute(intent_note, tag_note, roll, ctx)

        user_msg = mock_llm.call_history[0]["user_message"]
        self.assertIn("Miko 与她的保镖", user_msg)
        self.assertIn("说服或威胁", user_msg)

    def test_execute_includes_tag_matching_results(self):
        """user_message 包含标签匹配 Agent 的输出。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '=====REASONING=====\n推演\n=====STRUCTURED=====\n{"effects": []}',
                    {},
                )
            ]
        )
        agent = EffectActualizationAgent(mock_llm)
        ctx = make_test_context()
        intent_note = make_agent_note(structured={"action_type": "combat"})
        tag_note = make_agent_note(
            structured={
                "matched_power_tags": [{"name": "快速拔枪"}],
                "matched_weakness_tags": [],
            }
        )
        roll = make_roll_result(outcome="partial_success")

        agent.execute(intent_note, tag_note, roll, ctx)

        user_msg = mock_llm.call_history[0]["user_message"]
        self.assertIn("快速拔枪", user_msg)
        self.assertIn("标签匹配", user_msg)

    def test_execute_with_sub_action(self):
        """子 action 场景正确解析。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '=====REASONING=====\n推演\n=====STRUCTURED=====\n{"effects": []}',
                    {},
                )
            ]
        )
        agent = EffectActualizationAgent(mock_llm)
        ctx = make_test_context()
        intent_note = make_agent_note(structured={"action_type": "combat", "is_split_action": True})
        tag_note = make_agent_note(structured={"matched_power_tags": []})
        roll = make_roll_result(outcome="partial_success")
        sub_action = {
            "action_type": "combat",
            "action_summary": "子行动",
            "fragment": "拔枪",
            "_index": 0,
        }

        agent.execute(intent_note, tag_note, roll, ctx, sub_action=sub_action)

        user_msg = mock_llm.call_history[0]["user_message"]
        self.assertIn("拆分", user_msg)

    def test_available_power_is_non_negative(self):
        """可用力量 = max(roll.power, 0)，验证负数被截断。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '=====REASONING=====\n推演\n=====STRUCTURED=====\n{"effects": []}',
                    {},
                )
            ]
        )
        agent = EffectActualizationAgent(mock_llm)
        ctx = make_test_context()
        intent_note = make_agent_note(structured={"action_type": "combat"})
        tag_note = make_agent_note(structured={"matched_power_tags": []})
        roll = make_roll_result(outcome="partial_success", power=-1)

        agent.execute(intent_note, tag_note, roll, ctx)

        user_msg = mock_llm.call_history[0]["user_message"]
        self.assertIn("可用力量: 0", user_msg)

    def test_returns_agent_note(self):
        """验证返回正确解析的 AgentNote。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    "=====REASONING=====\n造成伤害\n=====STRUCTURED=====\n"
                    '{"effects": [{"operation": "inflict_status", "target": "挑战", "label": "受伤", "tier": 2}], '
                    '"narrative_hints": "保镖流血"}',
                    {},
                )
            ]
        )
        agent = EffectActualizationAgent(mock_llm)
        ctx = make_test_context()
        intent_note = make_agent_note(structured={"action_type": "combat"})
        tag_note = make_agent_note(structured={"matched_power_tags": []})
        roll = make_roll_result(outcome="full_success", power=2)

        result = agent.execute(intent_note, tag_note, roll, ctx)

        self.assertEqual(result.reasoning, "造成伤害")
        self.assertEqual(result.structured["effects"][0]["operation"], "inflict_status")
        self.assertEqual(result.structured["narrative_hints"], "保镖流血")


if __name__ == "__main__":
    unittest.main()
