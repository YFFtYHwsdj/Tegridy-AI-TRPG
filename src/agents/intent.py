"""意图解析 Agent —— 负责解析玩家的自然语言输入意图。"""

from __future__ import annotations

from src.agents.base import BaseAgent
from src.agents.prompts import INTENT_PROMPT
from src.context import AgentContext
from src.models import AgentNote


class IntentAgent(BaseAgent):
    """解析玩家输入的意图，判断行动类型并生成结构化动作摘要。"""

    system_prompt = INTENT_PROMPT
    agent_name = "意图解析Agent"

    def execute(self, player_input: str, ctx: AgentContext) -> AgentNote:
        """执行意图解析。

        将玩家自然语言输入转化为可供系统处理的结构化意图（Move、叙事、询问等）。

        Args:
            player_input: 玩家输入的文本
            ctx: 当前场景的上下文

        Returns:
            AgentNote: 包含推理过程和解析结果的分析便签
        """
        user_msg = f"""{ctx.assets_block}
{ctx.context_block}

叙事历史:
{ctx.narrative_block}

---
玩家输入: {player_input}

请解析玩家的意图。"""
        return self._call_llm(user_msg)
