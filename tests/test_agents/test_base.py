"""BaseAgent 测试 —— Agent 基类的 LLM 调用和输出解析。

验证所有 Agent 共享的 _call_llm 方法：
    - 正确调用 LLMClient.chat
    - 使用子类定义的 system_prompt 和 agent_name
    - 正确解析返回文本为 AgentNote
    - 调用被记录到日志
"""

from __future__ import annotations

import unittest
from unittest.mock import patch

from src.agents.base import BaseAgent
from src.models import AgentNote
from tests.helpers import MockLLMClient


class DummyAgent(BaseAgent):
    """测试用的具体 Agent 子类。"""

    system_prompt = "你是测试Agent"
    agent_name = "DummyAgent"


class TestBaseAgentCallLLM(unittest.TestCase):
    """测试 BaseAgent._call_llm 的核心行为。"""

    def test_uses_subclass_system_prompt(self):
        """验证调用时使用子类定义的 system_prompt。"""
        mock_llm = MockLLMClient(
            responses=[("=====REASONING=====\n测试\n=====STRUCTURED=====\n{}", {})]
        )
        agent = DummyAgent(mock_llm)
        agent._call_llm("用户消息")

        self.assertEqual(len(mock_llm.call_history), 1)
        self.assertEqual(mock_llm.call_history[0]["system_prompt"], "你是测试Agent")

    def test_passes_user_message(self):
        """验证 user_message 被正确传递给 LLM。"""
        mock_llm = MockLLMClient(
            responses=[("=====REASONING=====\n测试\n=====STRUCTURED=====\n{}", {})]
        )
        agent = DummyAgent(mock_llm)
        agent._call_llm("这是测试输入")

        self.assertIn("这是测试输入", mock_llm.call_history[0]["user_message"])

    def test_returns_parsed_agent_note(self):
        """验证返回正确解析的 AgentNote。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '=====REASONING=====\n分析过程\n=====STRUCTURED=====\n{"key": "value"}',
                    {},
                )
            ]
        )
        agent = DummyAgent(mock_llm)
        result = agent._call_llm("输入")

        self.assertIsInstance(result, AgentNote)
        self.assertEqual(result.reasoning, "分析过程")
        self.assertEqual(result.structured["key"], "value")

    def test_uses_default_temperature(self):
        """验证默认 temperature 为 0.3。"""
        mock_llm = MockLLMClient(
            responses=[("=====REASONING=====\n测试\n=====STRUCTURED=====\n{}", {})]
        )
        agent = DummyAgent(mock_llm)
        agent._call_llm("输入")

        self.assertEqual(mock_llm.call_history[0]["temperature"], 0.3)

    @patch("src.agents.base.print")
    def test_prints_agent_name(self, mock_print):
        """验证调用时打印 Agent 名称。"""
        mock_llm = MockLLMClient(
            responses=[("=====REASONING=====\n测试\n=====STRUCTURED=====\n{}", {})]
        )
        agent = DummyAgent(mock_llm)
        agent._call_llm("输入")

        printed = " ".join(str(call) for call in mock_print.call_args_list)
        self.assertIn("DummyAgent", printed)

    @patch("src.agents.base.log_call")
    def test_logs_call(self, mock_log_call):
        """验证调用被记录到日志系统。"""
        mock_llm = MockLLMClient(
            responses=[("=====REASONING=====\n测试\n=====STRUCTURED=====\n{}", {})]
        )
        agent = DummyAgent(mock_llm)
        agent._call_llm("用户输入")

        mock_log_call.assert_called_once()
        args = mock_log_call.call_args[0]
        self.assertEqual(args[0], "DummyAgent")
        self.assertEqual(args[1], "你是测试Agent")
        self.assertEqual(args[2], "用户输入")


if __name__ == "__main__":
    unittest.main()
