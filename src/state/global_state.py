"""全局状态管理 —— 跨场景的叙事历史聚合与全局实体图结构。

GlobalState 不仅存储已完成场景的叙事块，更重要的是它维护了整个游戏世界的全局图结构。
包含三大实体（Place, NPC, GameItem）库。

提供了基于 2跳视野 (2-Hop Context) 的图节点爬取功能，
为 Agent 提供深度的场景关联上下文。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.models import NPC, GameItem, Place


@dataclass
class SceneBlock:
    """GlobalState 中存储的单个场景叙事块。

    用于保留长线叙事记忆。
    """

    scene_id: str
    scene_description: str = ""
    compression: str = ""
    full_narrative: list[str] = field(default_factory=list)


class GlobalState:
    """跨场景状态聚合与图结构管理器。

    持有 places, npcs, items 三大全局字典。
    提供基于关系边 (connections/relationships) 的 BFS 爬取。
    """

    def __init__(self, worldview: str = ""):
        self.worldview = worldview
        self._blocks: list[SceneBlock] = []

        self.places: dict[str, Place] = {}
        self.npcs: dict[str, NPC] = {}
        self.items: dict[str, GameItem] = {}

    def get_entity_by_id(self, entity_id: str) -> tuple[str, Place | NPC | GameItem | None]:
        """根据 ID 查找实体对象及其类型。"""
        if entity_id in self.places:
            return "place", self.places[entity_id]
        if entity_id in self.npcs:
            return "npc", self.npcs[entity_id]
        if entity_id in self.items:
            return "item", self.items[entity_id]
        return "unknown", None

    def append_narrative_block(
        self,
        scene_id: str,
        description: str,
        compression: str,
        narratives: list[str],
    ):
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
        return len(self._blocks)

    def build_narrative_context(self) -> str:
        """构建叙事历史摘要块（向后兼容原 build_block 逻辑）。"""
        lines = []

        if not self._blocks:
            return "\n".join(lines).strip()

        lines.append("=== 故事至今 ===")
        n = len(self._blocks)

        for i in range(0, n - 1):
            block = self._blocks[i]
            idx = i + 1
            lines.append(f"\n[场景{idx}] {block.scene_description}")
            if block.compression:
                lines.append(f"  {block.compression}")
            else:
                lines.append("  （无压缩摘要）")

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

    def build_graph_context(
        self, start_place_id: str, start_npc_ids: list[str], start_item_ids: list[str]
    ) -> str:
        """基于 2跳视野构建图结构上下文。

        以传入的起点 ID 为 0跳，通过 connections 和 relationships 扩展出 1跳和 2跳的实体。
        提取它们的完整 description 和 notes。
        """
        visited = set()
        nodes_by_depth = {0: [], 1: [], 2: []}
        queue = []

        def enqueue(eid, depth):
            if not eid or eid in visited or depth > 2:
                return
            visited.add(eid)
            etype, ent = self.get_entity_by_id(eid)
            if ent:
                queue.append((eid, ent, etype, depth))
                nodes_by_depth[depth].append((eid, ent, etype))

        # 0跳：起始实体
        enqueue(start_place_id, 0)
        for nid in start_npc_ids:
            enqueue(nid, 0)
        for iid in start_item_ids:
            enqueue(iid, 0)

        # BFS 扩展
        head = 0
        while head < len(queue):
            eid, ent, etype, depth = queue[head]
            head += 1
            if depth < 2:
                rels = {}
                if etype == "place":
                    rels = ent.connections
                elif etype in ("npc", "item"):
                    rels = ent.relationships

                for target_id in rels:
                    enqueue(target_id, depth + 1)

        # 格式化输出
        lines = []
        lines.append("=== 世界实体网络 (2-Hop Context) ===")
        for depth in range(3):
            nodes = nodes_by_depth[depth]
            if not nodes:
                continue
            lines.append(f"\n--- {depth}跳 扩展实体 ---")
            for eid, ent, etype in nodes:
                if etype == "place":
                    lines.append(f"[地点] {ent.name} (ID: {eid})")
                    lines.append(f"  描述: {ent.description}")
                    if ent.notes:
                        lines.append(f"  附加笔记: {ent.notes}")
                    if ent.connections:
                        lines.append("  连接通路:")
                        for tid, desc in ent.connections.items():
                            lines.append(f"    -> {tid}: {desc}")
                elif etype == "npc":
                    lines.append(f"[NPC] {ent.name} (ID: {eid})")
                    lines.append(f"  描述: {ent.description}")
                    if ent.notes:
                        lines.append(f"  附加笔记: {ent.notes}")
                    if ent.relationships:
                        lines.append("  关系网络:")
                        for tid, desc in ent.relationships.items():
                            lines.append(f"    -> {tid}: {desc}")
                elif etype == "item":
                    lines.append(f"[物品] {ent.name} (ID: {eid})")
                    lines.append(f"  描述: {ent.description}")
                    if ent.notes:
                        lines.append(f"  附加笔记: {ent.notes}")
                    if ent.relationships:
                        lines.append("  关系网络:")
                        for tid, desc in ent.relationships.items():
                            lines.append(f"    -> {tid}: {desc}")

        return "\n".join(lines)
