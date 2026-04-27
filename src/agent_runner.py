from __future__ import annotations

from src.llm_client import LLMClient
from src.models import AgentNote
from src.json_parser import parse_agent_output
from src.logger import log_call


class AgentRunner:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def run_agent(self, system_prompt: str, user_message: str, agent_name: str) -> AgentNote:
        print(f"\n  [{agent_name}] 调用中...", end=" ", flush=True)
        raw, usage_info = self.llm.chat(system_prompt, user_message)
        log_call(agent_name, system_prompt, user_message, raw, usage_info)
        print("完成")
        return parse_agent_output(raw)
