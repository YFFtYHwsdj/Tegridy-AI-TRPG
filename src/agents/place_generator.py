"""地点生成者。"""

from __future__ import annotations

import uuid

from src.agents.base import BaseAgent
from src.agents.prompts.world_generators import PLACE_GENERATOR_PROMPT
from src.models import GameItem, Place


class PlaceGeneratorAgent(BaseAgent):
    """地点生成者。"""

    system_prompt = PLACE_GENERATOR_PROMPT
    agent_name = "地点生成Agent"

    def execute(self, generation_prompt: str, place_id: str) -> Place:
        note = self._call_llm(generation_prompt)
        data = note.structured

        loc = Place(
            place_id=place_id,
            name=data.get("name", "未命名地点"),
            description=data.get("description", ""),
        )
        for item_data in data.get("items", []):
            iid = item_data.get("item_id") or uuid.uuid4().hex[:8]
            loc.items[iid] = GameItem(
                item_id=iid,
                name=item_data.get("name", ""),
                description=item_data.get("description", ""),
                location=item_data.get("location", ""),
            )
        return loc
