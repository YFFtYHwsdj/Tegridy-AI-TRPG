"""信息补充 Agent —— 处理玩家向 MC 询问细节的请求。

当玩家不是在采取行动，而是在提问、回忆、确认细节时，
IntentAgent 将输入路由到 InquiryAgent。

InquiryAgent 在已有信息范围内回答问题，严格遵守信息安全规则：
    - 只转述已有信息，不自行创作剧情
    - 不泄露隐藏线索/物品
    - 当信息需要行动获取时，引导玩家采取行动
"""

from __future__ import annotations

from src.agents.base import BaseAgent
from src.agents.prompts import INQUIRY_PROMPT
from src.context import AgentContext
from src.models import AgentNote

_HIDDEN_NOTICE = """注意：标记为(隐藏)的线索、物品及其详情尚未被玩家角色发现。
回复中绝不提及这些信息的存在或内容。"""


class InquiryAgent(BaseAgent):
    """信息补充 Agent —— 回答玩家的提问和回忆请求。

    不推进叙事，不触发掷骰，不揭示隐藏信息。
    仅在已有信息范围内回答问题或引导玩家采取行动获取信息。
    """

    system_prompt = INQUIRY_PROMPT
    agent_name = "信息补充Agent"

    def execute(self, player_input: str, ctx: AgentContext) -> AgentNote:
        """回答玩家的信息询问。

        将场景资产、当前状态、叙事历史和玩家问题拼接为 user message，
        交给 LLM 在已有信息范围内回答。

        Args:
            player_input: 玩家的提问文本
            ctx: Agent 上下文（包含场景资产、状态、叙事历史）

        Returns:
            AgentNote: 包含回复文本和信息来源分类
        """
        user_msg = f"""{ctx.assets_block}
{ctx.context_block}

叙事历史:
{ctx.narrative_block}

{_HIDDEN_NOTICE}
玩家提问: {player_input}

请在已有信息范围内回答玩家的问题。不要创作新的剧情内容。"""
        return self._call_llm(user_msg)
