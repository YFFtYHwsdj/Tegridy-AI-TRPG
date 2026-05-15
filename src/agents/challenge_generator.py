"""挑战 生成者。"""

from __future__ import annotations

from src.agents.base import BaseAgent
from src.agents.prompts.world_generators import CHALLENGE_GENERATOR_PROMPT
from src.models import Challenge, PowerTag


class ChallengeGeneratorAgent(BaseAgent):
    """挑战 生成者。"""

    system_prompt = CHALLENGE_GENERATOR_PROMPT
    agent_name = "挑战生成Agent"

    def execute(self, generation_prompt: str, challenge_id: str) -> Challenge:
        note = self._call_llm(generation_prompt)
        data = note.structured

        base_tags = []
        for tag_data in data.get("base_tags", []):
            base_tags.append(
                PowerTag(name=tag_data.get("name", ""), description=tag_data.get("description", ""))
            )

        return Challenge(
            challenge_id=challenge_id,
            name=data.get("name", "未命名挑战"),
            description=data.get("description", ""),
            limits=data.get("limits", {}),
            base_tags=base_tags,
            threats=data.get("threats", []),
            consequences=data.get("consequences", []),
        )
