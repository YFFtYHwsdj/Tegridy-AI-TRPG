"""Agent 基类 —— LLM Agent 的抽象基类。

所有 Agent 继承自 BaseAgent，共享统一的 LLM 调用流程：
    1. 调用 LLM API（system_prompt + user_message）
    2. 记录完整调用日志
    3. 解析 REASONING / NARRATIVE / STRUCTURED 三段式输出为 AgentNote

子类只需定义 system_prompt（系统提示词）和 agent_name（日志标识）。
"""

from __future__ import annotations

from abc import ABC

from src.json_parser import parse_agent_output
from src.llm_client import LLMClient
from src.logger import log_call
from src.models import AgentNote


class BaseAgent(ABC):  # noqa: B024
    """LLM Agent 抽象基类。

    每个具体 Agent 的模板方法模式：
        - 子类设置 system_prompt 和 agent_name
        - _call_llm() 发送 user_message 并解析返回的 AgentNote
    """

    system_prompt: str = ""
    agent_name: str = "BaseAgent"

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def _call_llm(self, user_message: str) -> AgentNote:
        """调用 LLM 并解析输出为 AgentNote。

        封装完整的调用流程：API 请求 → 日志记录 → JSON 解析。

        Args:
            user_message: 发送给 LLM 的完整消息

        Returns:
            AgentNote: 包含推理过程和结构化数据的分析便签
        """
        print(f"\n  [{self.agent_name}] 调用中...", end=" ", flush=True)
        raw, usage_info = self.llm.chat(self.system_prompt, user_message)
        log_call(self.agent_name, self.system_prompt, user_message, raw, usage_info)
        print("完成")
        return parse_agent_output(raw)
