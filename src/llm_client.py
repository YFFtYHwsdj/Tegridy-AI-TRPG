import time
from openai import (
    APIError,
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)


class LLMError(Exception):
    pass


class LLMClient:
    def __init__(self, api_key: str, base_url: str, model: str, max_retries: int = 3):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.max_retries = max_retries

    def chat(self, system_prompt: str, user_message: str, temperature: float = 0.3) -> str:
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
                return content
            except (RateLimitError, APIConnectionError, APITimeoutError, InternalServerError, APIError) as e:
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise LLMError(f"API 调用失败（已重试 {self.max_retries} 次）: {e}") from e
            except LLMError:
                raise
            except Exception as e:
                raise LLMError(f"API 调用发生未预期错误: {e}") from e
        raise LLMError("API 调用失败：已达最大重试次数")
