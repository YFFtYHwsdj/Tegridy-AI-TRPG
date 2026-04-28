from __future__ import annotations

from src.agents.base import BaseAgent
from src.agents.prompts.item_creator import ITEM_CREATOR_PROMPT
from src.context import AgentContext
from src.models import AgentNote


class ItemCreatorAgent(BaseAgent):
    system_prompt = ITEM_CREATOR_PROMPT
    agent_name = "物品创建Agent"

    def execute(self, item_name: str, ctx: AgentContext) -> AgentNote:
        user_msg = f"""{ctx.assets_block}
{ctx.context_block}

叙事历史:
{ctx.narrative_block}

---
叙事文本中出现了以下物品，但它不在场景预设中：
物品名称: {item_name}

请根据上下文和赛博朋克世界观，为这个物品创建合适的机制数据。"""
        return self._call_llm(user_msg)
