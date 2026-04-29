"""TagMatcherAgent 测试 —— 标签匹配 Agent 的 prompt 组装验证。

验证 execute 方法正确将角色标签、状态、意图解析结果组装为 user_message。
"""

from __future__ import annotations

import unittest

from src.agents.tag_matcher import TagMatcherAgent
from tests.helpers import MockLLMClient, make_agent_note, make_test_context


class TestTagMatcherAgentExecute(unittest.TestCase):
    """测试 TagMatcherAgent.execute 的 prompt 组装。"""

    def test_includes_power_tags(self):
        """user_message 包含角色力量标签。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    "=====REASONING=====\n分析\n=====STRUCTURED=====\n"
                    '{"matched_power_tags": [{"name": "快速拔枪"}]}',
                    {},
                )
            ]
        )
        agent = TagMatcherAgent(mock_llm)
        ctx = make_test_context()
        intent_note = make_agent_note(structured={"action_type": "combat"})
        agent.execute(intent_note, ctx)

        self.assertIn("快速拔枪", mock_llm.call_history[0]["user_message"])

    def test_includes_weakness_tags(self):
        """user_message 包含角色弱点标签。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '=====REASONING=====\n分析\n=====STRUCTURED=====\n{"matched_power_tags": []}',
                    {},
                )
            ]
        )
        agent = TagMatcherAgent(mock_llm)
        ctx = make_test_context()
        intent_note = make_agent_note(structured={"action_type": "combat"})
        agent.execute(intent_note, ctx)

        self.assertIn("信用破产", mock_llm.call_history[0]["user_message"])

    def test_includes_character_statuses(self):
        """user_message 包含角色当前状态。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '=====REASONING=====\n分析\n=====STRUCTURED=====\n{"matched_power_tags": []}',
                    {},
                )
            ]
        )
        agent = TagMatcherAgent(mock_llm)
        ctx = make_test_context()
        ctx.character.statuses["受伤"] = unittest.mock.MagicMock()
        intent_note = make_agent_note(structured={"action_type": "combat"})
        agent.execute(intent_note, ctx)

        self.assertIn("角色当前状态", mock_llm.call_history[0]["user_message"])

    def test_includes_intent_info(self):
        """user_message 包含 action_type 和 action_summary。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '=====REASONING=====\n分析\n=====STRUCTURED=====\n{"matched_power_tags": []}',
                    {},
                )
            ]
        )
        agent = TagMatcherAgent(mock_llm)
        ctx = make_test_context()
        intent_note = make_agent_note(
            structured={"action_type": "combat", "action_summary": "拔枪射击"}
        )
        agent.execute(intent_note, ctx)

        user_msg = mock_llm.call_history[0]["user_message"]
        self.assertIn("combat", user_msg)
        self.assertIn("拔枪射击", user_msg)

    def test_with_sub_action_includes_split_info(self):
        """子 action 场景包含拆分提示信息。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '=====REASONING=====\n分析\n=====STRUCTURED=====\n{"matched_power_tags": []}',
                    {},
                )
            ]
        )
        agent = TagMatcherAgent(mock_llm)
        ctx = make_test_context()
        intent_note = make_agent_note(structured={"action_type": "combat", "is_split_action": True})
        sub_action = {
            "action_type": "combat",
            "action_summary": "子行动",
            "fragment": "拔枪",
            "_index": 0,
        }
        agent.execute(intent_note, ctx, sub_action=sub_action)

        user_msg = mock_llm.call_history[0]["user_message"]
        self.assertIn("拆分", user_msg)
        self.assertIn("拔枪", user_msg)

    def test_without_character_shows_empty(self):
        """character 为 None 时标签/状态显示为空字符串。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '=====REASONING=====\n分析\n=====STRUCTURED=====\n{"matched_power_tags": []}',
                    {},
                )
            ]
        )
        agent = TagMatcherAgent(mock_llm)
        ctx = make_test_context()
        ctx.character = None
        intent_note = make_agent_note(structured={"action_type": "combat"})
        agent.execute(intent_note, ctx)

        user_msg = mock_llm.call_history[0]["user_message"]
        # 标签部分应为空字符串，但 prompt 结构仍在
        self.assertIn("角色力量标签", user_msg)

    def test_returns_agent_note(self):
        """验证返回正确解析的 AgentNote。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    "=====REASONING=====\n快速拔枪适用\n=====STRUCTURED=====\n"
                    '{"matched_power_tags": [{"name": "快速拔枪"}], '
                    '"matched_weakness_tags": [], '
                    '"helping_statuses": [], '
                    '"hindering_statuses": []}',
                    {},
                )
            ]
        )
        agent = TagMatcherAgent(mock_llm)
        ctx = make_test_context()
        intent_note = make_agent_note(structured={"action_type": "combat"})
        result = agent.execute(intent_note, ctx)

        self.assertEqual(result.reasoning, "快速拔枪适用")
        self.assertEqual(result.structured["matched_power_tags"][0]["name"], "快速拔枪")


if __name__ == "__main__":
    unittest.main()
