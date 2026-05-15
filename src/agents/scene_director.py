"""场景导演 Agent —— 判断场景是否应该结束。

SceneDirectorAgent 在每轮玩家行动完成后被调用。
它从叙事和戏剧节奏角度判断当前场景的张力是否已释放，
是否应该结束并过渡到下一个场景。

输入是完整的 AgentContext（含跨场景历史）和本轮行动的叙事结果，
输出是判定结果（是否结束 + 原因 + 过渡提示）。
"""

from __future__ import annotations

from src.agents.base import BaseAgent
from src.agents.prompts import SCENE_DIRECTOR_PROMPT
from src.context import AgentContext
from src.models import AgentNote


class SceneDirectorAgent(BaseAgent):
    """场景导演 —— 每轮行动后判断场景结束条件。

    execute() 接收 AgentContext 和本轮叙事结果，返回
    包含 scene_should_end / reason / transition_hint 的 AgentNote。
    """

    system_prompt = SCENE_DIRECTOR_PROMPT
    agent_name = "场景导演Agent"

    def execute(self, ctx: AgentContext, last_narrative: str = "") -> AgentNote:
        """判断当前场景是否应该结束。

        Args:
            ctx: 完整的 Agent 上下文（含 global_block 跨场景历史）
            last_narrative: 本轮行动产出的叙事文本

        Returns:
            AgentNote，structured 包含：
                - scene_should_end (bool): 是否结束场景
                - reason (str): 一句话理由
                - transition_hint (str): 过渡建议（结束时有值，否则空字符串）
        """

        narrative_section = ""
        if last_narrative:
            narrative_section = f"\n本轮行动叙事:\n{last_narrative}"

        base_context = ctx.format_standard_blocks(include_global=True)

        user_msg = f"""{base_context}
{narrative_section}

---
请判断当前场景是否应该结束。"""
        return self._call_llm(user_msg)
