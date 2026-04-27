from __future__ import annotations

from src.agents.base import BaseAgent
from src.agents.prompts import RHYTHM_SYSTEM_PROMPT
from src.models import AgentNote


class RhythmAgent(BaseAgent):
    system_prompt = RHYTHM_SYSTEM_PROMPT
    agent_name = "节奏Agent"

    def execute(self, scene_description: str) -> AgentNote:
        user_msg = f"""{scene_description}

请用生动的叙事建立场景，最后把聚光灯交给玩家。"""
        return self._call_llm(user_msg)
