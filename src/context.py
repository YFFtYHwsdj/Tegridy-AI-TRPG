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

if TYPE_CHECKING:
    from src.state.character_state import CharacterState


class MessageBuilder:
    """动态组装 Agent Prompt 的上下文构建器。

    采用组合模式，避免使用庞大且脆弱的 f-string 模板。
    只在内容非空时才添加相应的 block，避免产生多余的空行或无意义标题。
    """

    def __init__(self):
        self.blocks: list[str] = []

    def add_block(self, title: str, content: str, wrap_title: bool = False) -> MessageBuilder:
        """添加一个带标题的文本块。

        Args:
            title: 标题文本
            content: 内容文本
            wrap_title: 如果为 True，标题格式为 "=== {title} ===\\n"，否则为 "{title}: "

        Returns:
            自身实例，支持链式调用
        """
        if content and content.strip():
            if wrap_title:
                self.blocks.append(f"=== {title} ===\n{content.strip()}")
            else:
                self.blocks.append(f"{title}: {content.strip()}")
        return self

    def add_text(self, text: str) -> MessageBuilder:
        """直接添加一段纯文本。

        Args:
            text: 要添加的文本

        Returns:
            自身实例，支持链式调用
        """
        if text and text.strip():
            self.blocks.append(text.strip())
        return self

    def build(self) -> str:
        """构建最终的上下文字符串，各个 block 之间用双换行符分隔。"""
        return "\n\n".join(self.blocks)


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

    def build_message(self, include_global: bool = True) -> MessageBuilder:
        """构建包含标准上下文块的 MessageBuilder。

        按照严格的优先级顺序自顶向下排列上下文。
        供各个 Agent 在构建 user_msg 时统一调用，随后可以继续链式添加特定上下文。

        Args:
            include_global: 是否包含 global_block（2跳网络图与跨场景历史）

        Returns:
            初始化了标准块的 MessageBuilder 实例
        """
        builder = MessageBuilder()

        builder.add_block("世界观设定", self.worldview_block, wrap_title=True)

        if include_global:
            builder.add_block("跨场景历史与世界网络 (Global)", self.global_block, wrap_title=True)

        builder.add_block("当前场景资产 (Assets)", self.assets_block, wrap_title=True)
        builder.add_block("当前场景环境 (Context)", self.context_block, wrap_title=True)
        builder.add_block("本场景局部叙事 (Narrative)", self.narrative_block, wrap_title=True)

        return builder
