from __future__ import annotations

from src.agents.base import BaseAgent
from src.agents.prompts.item_creator import ITEM_CREATOR_PROMPT
from src.models import AgentNote


class ItemCreatorAgent(BaseAgent):
    system_prompt = ITEM_CREATOR_PROMPT
    agent_name = "物品创建Agent"

    def execute(self, item_name: str, narrative_context: str) -> AgentNote:
        context_snippet = narrative_context[:800] if narrative_context else "（无上下文）"
        user_msg = f"""叙事文本中出现了以下物品，但它不在场景预设中：
物品名称: {item_name}

叙事上下文:
{context_snippet}

请根据叙事上下文和赛博朋克世界观，为这个物品创建合适的机制数据。"""
        return self._call_llm(user_msg)
