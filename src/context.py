"""Agent 上下文数据类 —— Agent 推理时的标准信息包。

AgentContext 是传递给每个 Agent 的标准上下文数据结构。
包含两个文本块和结构化引用：
    - context_block: 当前状态快照（场景、角色、挑战、极限进度）
    - narrative_block: 最近叙事历史
    - character/challenge: 直接对象引用（供代码层使用）
    - player_input: 玩家当前输入
    - extra: 扩展字段（如 scene_state）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models import Challenge, Character


@dataclass
class AgentContext:
    """Agent 推理上下文 —— 标准化信息包。

    Attributes:
        context_block: 当前状态快照文本（供 LLM 阅读）
        narrative_block: 最近叙事历史文本（供 LLM 阅读）
        character: 玩家角色引用（代码层使用）
        challenge: 当前挑战引用（代码层使用）
        player_input: 玩家当前输入文本
        extra: 扩展数据（如 scene_state 引用）
    """

    context_block: str
    narrative_block: str
    character: Character | None = None
    challenge: Challenge | None = None
    player_input: str = ""
    extra: dict = field(default_factory=dict)
