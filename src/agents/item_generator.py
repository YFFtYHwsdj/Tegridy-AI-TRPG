"""物品 生成者。"""

from __future__ import annotations

from src.agents.base import BaseAgent
from src.agents.prompts.world_generators import ITEM_GENERATOR_PROMPT
from src.models import GameItem, PowerTag, WeaknessTag


class ItemGeneratorAgent(BaseAgent):
    """物品 生成者。"""

    system_prompt = ITEM_GENERATOR_PROMPT
    agent_name = "物品生成Agent"

    def execute(self, generation_prompt: str, item_id: str) -> GameItem:
        note = self._call_llm(generation_prompt)
        data = note.structured

        tags = []
        for tag_data in data.get("tags", []):
            tags.append(
                PowerTag(name=tag_data.get("name", ""), description=tag_data.get("description", ""))
            )

        weakness_tags = []
        for tag_data in data.get("weakness_tags", []):
            weakness_tags.append(
                WeaknessTag(
                    name=tag_data.get("name", ""), description=tag_data.get("description", "")
                )
            )

        return GameItem(
            item_id=item_id,
            name=data.get("name", "未命名物品"),
            description=data.get("description", ""),
            tags=tags,
            weakness_tags=weakness_tags,
        )
