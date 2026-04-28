"""LLM 客户端封装 —— OpenAI-compatible API 调用的统一入口。

封装了 OpenAI Python SDK，提供带自动重试的 chat 调用。
支持 DeepSeek 等 OpenAI-compatible 格式的 API。
错误处理涵盖限流、连接超时、服务端错误等常见场景。
"""

import time

from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)


class LLMError(Exception):
    """LLM API 调用相关的所有错误的统一异常类型。"""

    pass


class LLMClient:
    """LLM API 客户端。

    封装 OpenAI-compatible 的 chat completion 调用，
    内置指数退避重试机制，自动记录 token 用量。
    """

    def __init__(self, api_key: str, base_url: str, model: str, max_retries: int = 3):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.max_retries = max_retries

    def chat(
        self, system_prompt: str, user_message: str, temperature: float = 0.3
    ) -> tuple[str, dict]:
        """发起一次 chat completion 调用。

        自动重试（指数退避 2^attempt 秒），处理限流、连接超时、
        服务端错误等可恢复异常。不可恢复的异常直接抛出 LLMError。

        Args:
            system_prompt: 系统提示词
            user_message: 用户消息（给 LLM 的完整输入）
            temperature: 生成温度，默认 0.3（偏确定性输出）

        Returns:
            (响应文本, token用量信息) 元组

        Raises:
            LLMError: API 调用失败或返回空内容
        """
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    temperature=temperature,
                )
                content = response.choices[0].message.content
                if content is None:
                    raise LLMError("API 返回了空内容")

                usage = response.usage
                usage_info = {
                    "prompt_tokens": usage.prompt_tokens if usage else 0,
                    "completion_tokens": usage.completion_tokens if usage else 0,
                    "total_tokens": usage.total_tokens if usage else 0,
                }

                # DeepSeek 支持 prompt caching，记录缓存命中情况
                if (
                    usage
                    and hasattr(usage, "prompt_tokens_details")
                    and usage.prompt_tokens_details
                ):
                    cached = getattr(usage.prompt_tokens_details, "cached_tokens", None)
                    if cached is not None:
                        usage_info["cached_tokens"] = cached

                return content, usage_info
            except (
                RateLimitError,
                APIConnectionError,
                APITimeoutError,
                InternalServerError,
                APIError,
            ) as e:
                if attempt < self.max_retries - 1:
                    time.sleep(2**attempt)
                    continue
                raise LLMError(f"API 调用失败（已重试 {self.max_retries} 次）: {e}") from e
            except LLMError:
                raise
            except Exception as e:
                raise LLMError(f"API 调用发生未预期错误: {e}") from e
        raise LLMError("API 调用失败：已达最大重试次数")
