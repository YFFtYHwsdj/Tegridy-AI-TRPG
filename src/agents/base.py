from __future__ import annotations

from abc import ABC
from src.llm_client import LLMClient
from src.models import AgentNote
from src.json_parser import parse_agent_output
from src.logger import log_call


class BaseAgent(ABC):
    system_prompt: str = ""
    agent_name: str = "BaseAgent"

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def _call_llm(self, user_message: str) -> AgentNote:
        print(f"\n  [{self.agent_name}] 调用中...", end=" ", flush=True)
        raw, usage_info = self.llm.chat(self.system_prompt, user_message)
        log_call(self.agent_name, self.system_prompt, user_message, raw, usage_info)
        print("完成")
        return parse_agent_output(raw)
