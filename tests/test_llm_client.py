"""LLMClient 测试 —— API 调用、重试机制、错误处理。

验证 LLMClient 的 chat 方法在各种场景下的行为：
    - 正常调用返回内容和用量
    - 可恢复错误（限流、连接超时、服务端错误）的自动重试
    - 超过最大重试次数后的异常抛出
    - 空内容返回的异常处理
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    InternalServerError,
    RateLimitError,
)

from src.llm_client import LLMClient, LLMError


class TestLLMClientChat(unittest.TestCase):
    """测试 LLMClient.chat 的正常和异常路径。"""

    def _make_client(self, max_retries: int = 3, thinking: bool = False) -> LLMClient:
        """创建测试用的 LLMClient 实例。"""
        return LLMClient(
            api_key="test-key",
            base_url="https://test.example.com",
            model="test-model",
            max_retries=max_retries,
            thinking=thinking,
        )

    def _make_mock_response(self, content: str | None = "hello") -> MagicMock:
        """创建模拟的 API 响应对象。"""
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = content

        usage = MagicMock()
        usage.prompt_tokens = 10
        usage.completion_tokens = 5
        usage.total_tokens = 15
        usage.prompt_tokens_details = None
        response.usage = usage

        return response

    @patch("src.llm_client.OpenAI")
    def test_chat_returns_content_and_usage(self, mock_openai_class: MagicMock):
        """正常调用应返回内容文本和用量信息。"""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = self._make_mock_response("测试响应")

        client = self._make_client()
        content, usage = client.chat("system", "user")

        self.assertEqual(content, "测试响应")
        self.assertEqual(usage["prompt_tokens"], 10)
        self.assertEqual(usage["completion_tokens"], 5)
        self.assertEqual(usage["total_tokens"], 15)

    @patch("src.llm_client.OpenAI")
    def test_chat_passes_correct_parameters(self, mock_openai_class: MagicMock):
        """验证调用参数正确传递，且默认关闭 thinking。"""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = self._make_mock_response()

        client = self._make_client()
        client.chat("system prompt", "user message", temperature=0.7)

        call_args = mock_client.chat.completions.create.call_args
        self.assertEqual(call_args.kwargs["model"], "test-model")
        self.assertEqual(call_args.kwargs["temperature"], 0.7)
        messages = call_args.kwargs["messages"]
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[0]["content"], "system prompt")
        self.assertEqual(messages[1]["role"], "user")
        self.assertEqual(messages[1]["content"], "user message")
        self.assertEqual(call_args.kwargs["extra_body"], {"thinking": {"type": "disabled"}})

    @patch("src.llm_client.OpenAI")
    def test_chat_thinking_enabled_no_extra_body(self, mock_openai_class: MagicMock):
        """thinking=True 时不应传入 extra_body。"""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = self._make_mock_response()

        client = self._make_client(thinking=True)
        client.chat("system prompt", "user message")

        call_args = mock_client.chat.completions.create.call_args
        self.assertNotIn("extra_body", call_args.kwargs)

    @patch("src.llm_client.OpenAI")
    @patch("src.llm_client.time.sleep")
    def test_chat_retries_on_rate_limit(self, mock_sleep: MagicMock, mock_openai_class: MagicMock):
        """RateLimitError 时应重试并最终成功。"""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.side_effect = [
            RateLimitError("rate limited", response=MagicMock(), body=None),
            self._make_mock_response("success after retry"),
        ]

        client = self._make_client(max_retries=3)
        content, _ = client.chat("system", "user")

        self.assertEqual(content, "success after retry")
        self.assertEqual(mock_client.chat.completions.create.call_count, 2)
        mock_sleep.assert_called_once()

    @patch("src.llm_client.OpenAI")
    @patch("src.llm_client.time.sleep")
    def test_chat_retries_on_connection_error(
        self, mock_sleep: MagicMock, mock_openai_class: MagicMock
    ):
        """APIConnectionError 时应重试。"""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.side_effect = [
            APIConnectionError(request=MagicMock()),
            self._make_mock_response("success"),
        ]

        client = self._make_client()
        content, _ = client.chat("system", "user")

        self.assertEqual(content, "success")
        self.assertEqual(mock_client.chat.completions.create.call_count, 2)

    @patch("src.llm_client.OpenAI")
    @patch("src.llm_client.time.sleep")
    def test_chat_retries_on_timeout(self, mock_sleep: MagicMock, mock_openai_class: MagicMock):
        """APITimeoutError 时应重试。"""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.side_effect = [
            APITimeoutError(request=MagicMock()),
            self._make_mock_response("success"),
        ]

        client = self._make_client()
        content, _ = client.chat("system", "user")

        self.assertEqual(content, "success")

    @patch("src.llm_client.OpenAI")
    @patch("src.llm_client.time.sleep")
    def test_chat_retries_on_server_error(
        self, mock_sleep: MagicMock, mock_openai_class: MagicMock
    ):
        """InternalServerError 时应重试。"""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.side_effect = [
            InternalServerError("server error", response=MagicMock(), body=None),
            self._make_mock_response("success"),
        ]

        client = self._make_client()
        content, _ = client.chat("system", "user")

        self.assertEqual(content, "success")

    @patch("src.llm_client.OpenAI")
    @patch("src.llm_client.time.sleep")
    def test_chat_retries_on_api_error(self, mock_sleep: MagicMock, mock_openai_class: MagicMock):
        """通用 APIError 时应重试。"""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.side_effect = [
            APIError("api error", request=MagicMock(), body=None),
            self._make_mock_response("success"),
        ]

        client = self._make_client()
        content, _ = client.chat("system", "user")

        self.assertEqual(content, "success")

    @patch("src.llm_client.OpenAI")
    @patch("src.llm_client.time.sleep")
    def test_chat_raises_after_max_retries(
        self, mock_sleep: MagicMock, mock_openai_class: MagicMock
    ):
        """超过最大重试次数后应抛出 LLMError。"""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.side_effect = RateLimitError(
            "rate limited", response=MagicMock(), body=None
        )

        client = self._make_client(max_retries=2)
        with self.assertRaises(LLMError) as ctx:
            client.chat("system", "user")

        self.assertIn("已重试", str(ctx.exception))
        self.assertEqual(mock_client.chat.completions.create.call_count, 2)

    @patch("src.llm_client.OpenAI")
    def test_chat_raises_on_empty_content(self, mock_openai_class: MagicMock):
        """API 返回空内容时应抛出 LLMError。"""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = self._make_mock_response(None)

        client = self._make_client()
        with self.assertRaises(LLMError) as ctx:
            client.chat("system", "user")

        self.assertIn("空内容", str(ctx.exception))

    @patch("src.llm_client.OpenAI")
    @patch("src.llm_client.time.sleep")
    def test_exponential_backoff(self, mock_sleep: MagicMock, mock_openai_class: MagicMock):
        """验证重试间隔按指数退避增长。"""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.side_effect = [
            RateLimitError("1", response=MagicMock(), body=None),
            RateLimitError("2", response=MagicMock(), body=None),
            self._make_mock_response("success"),
        ]

        client = self._make_client(max_retries=3)
        client.chat("system", "user")

        self.assertEqual(mock_sleep.call_count, 2)
        # 第一次重试等待 2^0 = 1 秒，第二次等待 2^1 = 2 秒
        mock_sleep.assert_any_call(1)
        mock_sleep.assert_any_call(2)

    @patch("src.llm_client.OpenAI")
    def test_chat_records_cached_tokens(self, mock_openai_class: MagicMock):
        """DeepSeek prompt caching 信息被正确记录。"""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        response = self._make_mock_response("test")
        details = MagicMock()
        details.cached_tokens = 100
        response.usage.prompt_tokens_details = details
        mock_client.chat.completions.create.return_value = response

        client = self._make_client()
        _, usage = client.chat("system", "user")

        self.assertEqual(usage.get("cached_tokens"), 100)

    @patch("src.llm_client.OpenAI")
    def test_chat_handles_none_usage(self, mock_openai_class: MagicMock):
        """usage 为 None 时不报错，用量记为 0。"""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        response = self._make_mock_response("test")
        response.usage = None
        mock_client.chat.completions.create.return_value = response

        client = self._make_client()
        content, usage = client.chat("system", "user")

        self.assertEqual(content, "test")
        self.assertEqual(usage["prompt_tokens"], 0)
        self.assertEqual(usage["completion_tokens"], 0)
        self.assertEqual(usage["total_tokens"], 0)


if __name__ == "__main__":
    unittest.main()
