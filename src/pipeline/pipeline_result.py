"""流水线结果数据类 —— 一次 Action 流水线的完整产出。

PipelineResult 汇集了流水线各阶段的 Agent 分析便签和掷骰结果，
供 GameLoop 层消费（显示、效果应用、叙事追加）。
"""

from __future__ import annotations

from dataclasses import dataclass

from src.models import AgentNote, RollResult


@dataclass
class PipelineResult:
    """一次 Action 流水线的完整结果。

    Attributes:
        tag_note: Tag 匹配 Agent 的分析便签
        roll: 掷骰结果（力量值 + 骰面 + 结果标签）
        narrator_note: 叙述者 Agent 的叙事便签
        effect_note: 效果推演 Agent 的分析便签（快速流水线时为 None）
        consequence_note: 后果 Agent 的分析便签（完全成功时为 None）
    """

    tag_note: AgentNote
    roll: RollResult
    narrator_note: AgentNote | None = None
    effect_note: AgentNote | None = None
    consequence_note: AgentNote | None = None
