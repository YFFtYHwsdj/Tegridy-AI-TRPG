from __future__ import annotations

from src.agents.base import BaseAgent
from src.agents.prompts.crack_evaluator import CRACK_EVALUATOR_PROMPT
from src.context import AgentContext, MessageBuilder
from src.models import AgentNote


class CrackEvaluatorAgent(BaseAgent):
    system_prompt = CRACK_EVALUATOR_PROMPT
    agent_name = "裂痕评估Agent"
    json_mode = True

    def execute(
        self,
        scene_compression: str,
        ctx: AgentContext,
    ) -> AgentNote:
        """执行场景结束时的 Crack 评估。"""
        # 构建当前角色的主题列表
        char = ctx.character
        themes_list = []
        if char:
            for t in char.themes:
                themes_list.append(
                    f"- {t.name} (类型: {t.theme_type}, 概念: {t.concept}, 动机: {t.motivation})"
                )

        character_themes_text = "\n".join(themes_list) if themes_list else "无"

        builder = MessageBuilder()
        builder.add_block("玩家当前主题", character_themes_text, wrap_title=True)
        builder.add_block("本场景压缩", scene_compression, wrap_title=True)
        builder.add_text("请评估并输出结果。")

        return self._call_llm(builder.build())
