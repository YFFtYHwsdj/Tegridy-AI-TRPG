"""测试各机制判定 Agent。"""

from __future__ import annotations

import unittest

from src.agents.crack_evaluator import CrackEvaluatorAgent
from src.agents.crisis import CrisisAgent
from src.agents.evolution import EvolutionAgent
from tests.helpers import MockLLMClient, make_test_context


class TestEvolutionAgent(unittest.TestCase):
    def test_execute(self):
        mock_llm = MockLLMClient(
            responses=[
                (
                    '{"reasoning": "主题进化", "state": "finished", '
                    '"new_theme": {"name": "老兵", "type": "背景", "concept": "战斗专家"}}',
                    {},
                )
            ]
        )
        agent = EvolutionAgent(mock_llm)
        ctx = make_test_context()

        result = agent.execute("我选第一个选项", ctx, active_theme_name="测试")

        # 验证 context 和 active_theme 被带入
        user_msg = mock_llm.call_history[0]["user_message"]
        sys_msg = mock_llm.call_history[0]["system_prompt"]
        self.assertIn("我选第一个选项", user_msg)
        self.assertIn("测试", sys_msg)

        self.assertEqual(result.structured.get("state"), "finished")
        self.assertEqual(result.structured.get("new_theme", {}).get("name"), "老兵")


class TestCrisisAgent(unittest.TestCase):
    def test_execute(self):
        mock_llm = MockLLMClient(
            responses=[
                (
                    '{"reasoning": "处理危机", "state": "finished", '
                    '"replaced_theme": {"name": "重生", "type": "状态", "concept": "刚从死神手里逃脱"}}',
                    {},
                )
            ]
        )
        agent = CrisisAgent(mock_llm)
        ctx = make_test_context()

        result = agent.execute("", ctx, active_theme_name="测试")

        # 验证默认的系统提示被带入 (因为 player_input 为空)
        user_msg = mock_llm.call_history[0]["user_message"]
        self.assertIn("玩家的该主题已经满足彻底毁灭的条件", user_msg)

        self.assertEqual(result.structured.get("state"), "finished")
        self.assertEqual(result.structured.get("replaced_theme", {}).get("name"), "重生")


class TestCrackEvaluatorAgent(unittest.TestCase):
    def test_execute(self):
        mock_llm = MockLLMClient(
            responses=[
                (
                    '{"reasoning": "评估裂痕", '
                    '"cracked_themes": [{"theme_name": "测试", "reason": "做出了违背信念的选择"}]}',
                    {},
                )
            ]
        )
        agent = CrackEvaluatorAgent(mock_llm)
        ctx = make_test_context()

        result = agent.execute("在这个场景中，Kael 抛弃了队友。", ctx)

        user_msg = mock_llm.call_history[0]["user_message"]
        self.assertIn("Kael 抛弃了队友", user_msg)
        self.assertIn("测试", user_msg)  # ctx.character 里的主题会被提取并拼接进去

        themes = result.structured.get("cracked_themes", [])
        self.assertEqual(len(themes), 1)
        self.assertEqual(themes[0]["theme_name"], "测试")


if __name__ == "__main__":
    unittest.main()
