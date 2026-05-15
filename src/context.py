"""Agent 上下文数据类 —— Agent 推理时的标准信息包。

AgentContext 是传递给每个 Agent 的标准上下文数据结构。
包含四个文本块和结构化引用：
    - worldview_block: 世界观设定
    - global_block: 跨场景历史（GlobalState 产出，含上一场景完整叙事）
    - assets_block: 场景资产（NPC、线索、物品）
    - context_block: 当前状态快照（场景、角色）
    - narrative_block: 当前场景叙事历史
    - character: 直接对象引用（供代码层使用）
    - player_input: 玩家当前输入
    - extra: 扩展字段（如 scene_state）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from src.state.character_state import CharacterState

if TYPE_CHECKING:
    pass


@dataclass
class AgentContext:
    """Agent 推理上下文 —— 标准化信息包。

    Attributes:
        worldview_block: 世界观设定文本
        global_block: 跨场景历史文本（GlobalState.build_block() 产出）
        assets_block: 场景资产文本（NPC、线索、物品）
        context_block: 当前状态快照文本（供 LLM 阅读）
        narrative_block: 当前场景叙事历史文本（供 LLM 阅读）
        character: 玩家角色引用（代码层使用）
        player_input: 玩家当前输入文本
        extra: 扩展数据（如 scene_state 引用）
    """

    worldview_block: str = ""
    global_block: str = ""
    assets_block: str = ""
    context_block: str = ""
    narrative_block: str = ""
    character: CharacterState | None = None
    player_input: str = ""
    extra: dict = field(default_factory=dict)

    def format_standard_blocks(self, include_global: bool = True) -> str:
        """格式化标准的上下文块组合。

        按照严格的优先级顺序自顶向下排列上下文。
        供各个 Agent 在构建 user_msg 时统一调用。

        Args:
            include_global: 是否包含 global_block（2跳网络图与跨场景历史）

        Returns:
            组装好的多行文本字符串
        """
        blocks = []
        if self.worldview_block:
            blocks.append(f"=== 世界观设定 ===\n{self.worldview_block}")

        if include_global and self.global_block:
            blocks.append(f"=== 跨场景历史与世界网络 (Global) ===\n{self.global_block}")

        if self.assets_block:
            blocks.append(f"=== 当前场景资产 (Assets) ===\n{self.assets_block}")

        if self.context_block:
            blocks.append(f"=== 当前场景环境 (Context) ===\n{self.context_block}")

        if self.narrative_block:
            blocks.append(f"=== 本场景局部叙事 (Narrative) ===\n{self.narrative_block}")

        return "\n\n".join(blocks)
