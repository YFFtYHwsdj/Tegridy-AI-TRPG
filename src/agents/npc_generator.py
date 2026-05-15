"""NPC 生成者。"""

from __future__ import annotations

from src.agents.base import BaseAgent
from src.agents.prompts.world_generators import NPC_GENERATOR_PROMPT
from src.models import NPC, PowerTag


class NPCGeneratorAgent(BaseAgent):
    """NPC 生成者。"""

    system_prompt = NPC_GENERATOR_PROMPT
    agent_name = "NPC生成Agent"

    def execute(self, generation_prompt: str, npc_id: str) -> NPC:
        note = self._call_llm(generation_prompt)
        data = note.structured

        tags = []
        for tag_data in data.get("tags", []):
            tags.append(
                PowerTag(name=tag_data.get("name", ""), description=tag_data.get("description", ""))
            )

        return NPC(
            npc_id=npc_id,
            name=data.get("name", "未命名人物"),
            description=data.get("description", ""),
            tags=tags,
        )
