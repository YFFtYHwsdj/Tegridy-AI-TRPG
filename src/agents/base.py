"""Agent 基类 —— LLM Agent 的抽象基类。

所有 Agent 继承自 BaseAgent，共享统一的 LLM 调用流程：
    1. 调用 LLM API（system_prompt + user_message，JSON mode）
    2. 记录完整调用日志
    3. 解析纯 JSON 输出为 AgentNote（reasoning 字段 + 结构化数据）
    4. JSON 解析失败时自动重试一次（防御网络截断等极端情况）

子类只需定义 system_prompt（系统提示词）和 agent_name（日志标识）。
"""

from __future__ import annotations

from abc import ABC

from src.json_parser import JSONParseError, parse_json_output
from src.llm_client import LLMClient
from src.logger import log_call
from src.models import AgentNote

# JSON 解析失败时的最大重试次数
# JSON mode 下理论上不应失败，1 次重试足以覆盖偶发截断
_JSON_RETRY_LIMIT = 1


class BaseAgent(ABC):  # noqa: B024
    """LLM Agent 抽象基类。

    每个具体 Agent 的模板方法模式：
        - 子类设置 system_prompt 和 agent_name
        - (可选) 子类设置 model 和 thinking 以覆盖全局默认模型配置
        - _call_llm() 发送 user_message 并解析返回的 AgentNote
    """

    system_prompt: str = ""
    agent_name: str = "BaseAgent"
    model: str | None = None
    thinking: bool | None = None

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def _call_llm(self, user_message: str) -> AgentNote:
        """调用 LLM 并解析 JSON 输出为 AgentNote。

        封装完整的调用流程：API 请求（JSON mode）→ 日志记录 → JSON 解析。
        JSON 解析失败时自动重试（最多 _JSON_RETRY_LIMIT 次），
        重试仍失败则抛出 JSONParseError。

        Args:
            user_message: 发送给 LLM 的完整消息

        Returns:
            AgentNote: 包含推理过程和结构化数据的分析便签

        Raises:
            JSONParseError: JSON 解析在重试后仍然失败
            LLMError: LLM API 调用失败
        """
        from src.logger import get_game_logger

        _log = get_game_logger()
        _log.debug("[%s] 调用中...", self.agent_name)

        last_error: JSONParseError | None = None

        for attempt in range(_JSON_RETRY_LIMIT + 1):
            raw, usage_info = self.llm.chat(
                self.system_prompt,
                user_message,
                model=self.model,
                thinking=self.thinking,
            )
            log_call(self.agent_name, self.system_prompt, user_message, raw, usage_info)

            try:
                note = parse_json_output(raw)
                _log.debug("[%s] 完成", self.agent_name)
                return note
            except JSONParseError as e:
                last_error = e
                if attempt < _JSON_RETRY_LIMIT:
                    _log.warning(
                        "[%s] JSON 解析失败，重试 %d/%d",
                        self.agent_name,
                        attempt + 1,
                        _JSON_RETRY_LIMIT,
                    )
                    continue

        # 重试耗尽，抛出最后一次的解析错误
        raise last_error  # type: ignore[misc]
