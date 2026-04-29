"""全局状态管理 —— 跨场景的叙事历史聚合。

GlobalState 是纯粹的数据聚合层，不管理运行时状态。
它存储所有已完成场景的叙事块，为 Agent 提供跨场景上下文。

上下文构建规则：
    - 紧邻上一场景：压缩摘要 + 完整叙事全文
    - 所有更早场景：仅压缩摘要

首个版本仅存储叙事历史。后续可扩展角色跨场景追踪、
重要存在数据库等。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SceneBlock:
    """GlobalState 中存储的单个场景叙事块。

    Attributes:
        scene_id: 场景唯一标识
        scene_description: 场景描述文本
        compression: CompressorAgent 产出的场景压缩摘要
        full_narrative: 完整叙事文本列表（不做任何压缩或截断）
    """

    scene_id: str
    scene_description: str = ""
    compression: str = ""
    full_narrative: list[str] = field(default_factory=list)


class GlobalState:
    """跨场景状态聚合器。

    存储所有已完成场景的叙事块，提供 build_block() 方法
    生成供 Agent 使用的跨场景上下文文本块。

    场景结束后通过 append() 追加新块，上下文构建规则在
    build_block() 中实现。
    """

    def __init__(self):
        self._blocks: list[SceneBlock] = []

    def append(
        self,
        scene_id: str,
        description: str,
        compression: str,
        narratives: list[str],
    ):
        """场景结束后追加一个叙事块。

        完整叙事文本在追加时做浅拷贝，避免外部后续修改污染存储。

        Args:
            scene_id: 场景唯一标识
            description: 场景描述文本
            compression: CompressorAgent 产出的压缩摘要
            narratives: 完整叙事文本列表（按时间顺序）
        """
        self._blocks.append(
            SceneBlock(
                scene_id=scene_id,
                scene_description=description,
                compression=compression,
                full_narrative=list(narratives),
            )
        )

    @property
    def scene_count(self) -> int:
        """已完成的场景数量（不含当前活跃场景）。"""
        return len(self._blocks)

    def build_block(self) -> str:
        """构建供 Agent 使用的跨场景上下文文本块。

        格式规则：
            - 所有更早场景（场景1 到 场景N-2）→ 只输出压缩摘要
            - 紧邻上一场景（场景N-1）→ 压缩摘要 + 完整叙事全文

        无已完成场景时返回空字符串。只有一个已完成场景时，
        该场景按"紧邻上一场景"处理（完整叙事输出）。

        Returns:
            格式化的跨场景上下文文本，供 Agent prompt 中嵌入使用
        """
        if not self._blocks:
            return ""

        lines = ["=== 故事至今 ==="]
        n = len(self._blocks)

        # 更早的场景（场景1 到 场景N-2）：只输出压缩摘要
        for i in range(0, n - 1):
            block = self._blocks[i]
            idx = i + 1
            lines.append(f"\n[场景{idx}] {block.scene_description}")
            if block.compression:
                lines.append(f"  {block.compression}")
            else:
                lines.append("  （无压缩摘要）")

        # 最后一个块（场景N-1，即紧邻上一场景）：压缩摘要 + 完整叙事全文
        last = self._blocks[-1]
        idx = n
        lines.append(f"\n[场景{idx}] {last.scene_description}")
        if last.compression:
            lines.append(f"  {last.compression}")
        else:
            lines.append("  （无压缩摘要）")

        lines.append("")
        lines.append("──────────────────── 上一场景完整叙事 ────────────────────")
        lines.append("")

        if last.full_narrative:
            for j, entry in enumerate(last.full_narrative, 1):
                lines.append(f"[T{j}] {entry}")
        else:
            lines.append("（无叙事记录）")

        lines.append("")
        lines.append("────────────────")

        return "\n".join(lines)
