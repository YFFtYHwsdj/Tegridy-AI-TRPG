"""世界演化推演与图边融合引擎管线。

负责在场景结束后，阅读完整叙事历史并更新 GlobalState。
协调 WorldAnalyzerAgent (提议关系和重写笔记) 和
EdgeMergeAgent (处理图边碰撞与融合)。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.agents.world_updater import EdgeMergeAgent, WorldAnalyzerAgent
    from src.state.global_state import GlobalState
    from src.state.scene_state import SceneState


def apply_world_updates(
    analyzer: WorldAnalyzerAgent,
    merger: EdgeMergeAgent,
    scene: SceneState,
    global_state: GlobalState,
) -> dict:
    """执行完整的场景末世界更新管线。

    1. 调用 WorldAnalyzerAgent 推演更新。
    2. 应用 Notes 更新。
    3. 收集新关系，执行纯 Python 图碰撞检测。
    4. 对冲突边调用 EdgeMergeAgent 进行合并。

    Returns:
        新提及的实体字典 (new_entities_mentioned) 供 Router 备用。
    """
    from src.logger import log_system

    note = analyzer.execute(scene, global_state)
    data = note.structured

    # 1. 更新 Notes
    updates = data.get("entity_updates", [])
    for upd in updates:
        eid = upd.get("entity_id")
        etype = upd.get("entity_type")
        revised = upd.get("revised_notes", "")
        if not eid or not revised:
            continue

        _, ent = global_state.get_entity_by_id(eid)
        if ent:
            ent.notes = revised
            log_system(f"已重写 {etype} [{eid}] 的笔记")

    # 2. 图边碰撞检测准备
    # edge_candidates: (id1, id2) -> list of descriptions
    # 保证 id1 < id2 确保双向边落入同一个桶
    edge_candidates = {}

    def add_candidate(s_id, t_id, desc):
        if not s_id or not t_id or not desc:
            return
        key = tuple(sorted([s_id, t_id]))
        if key not in edge_candidates:
            edge_candidates[key] = {"s_ids": set(), "t_ids": set(), "descs": []}
        edge_candidates[key]["s_ids"].add(s_id)
        edge_candidates[key]["t_ids"].add(t_id)
        edge_candidates[key]["descs"].append(f"{s_id} -> {t_id}: {desc}")

    # 将原有图中的关系加入候选桶（仅针对本轮被提出的实体相关联的边）
    # 为简单起见，我们收集所有相关的旧边
    proposed = data.get("proposed_relationships", [])
    affected_entities = set()
    for prop in proposed:
        affected_entities.add(prop.get("source_id"))
        affected_entities.add(prop.get("target_id"))

    for eid in affected_entities:
        etype, ent = global_state.get_entity_by_id(eid)
        if ent:
            rels = ent.connections if etype == "place" else ent.relationships
            for tid, desc in list(rels.items()):
                add_candidate(eid, tid, desc)
                # 从原结构中剥离，等待合并后重新插入
                del rels[tid]

    # 将新提出的关系加入候选桶
    for prop in proposed:
        add_candidate(prop.get("source_id"), prop.get("target_id"), prop.get("description"))

    # 3. 碰撞与合并
    for (id_a, id_b), bag in edge_candidates.items():
        descs = bag["descs"]
        if not descs:
            continue

        if len(descs) == 1:
            # 无冲突，直接加回
            # 解析出原始的 source 和 target
            s_id = next(iter(bag["s_ids"]))
            t_id = next(iter(bag["t_ids"]))
            desc = descs[0].split(": ", 1)[1]
            _insert_edge(global_state, s_id, t_id, desc)
        else:
            # 多条边，需 LLM 融合
            _, ent_a = global_state.get_entity_by_id(id_a)
            _, ent_b = global_state.get_entity_by_id(id_b)
            desc_a = ent_a.description if ent_a else "未知"
            desc_b = ent_b.description if ent_b else "未知"

            merge_note = merger.execute(id_a, desc_a, id_b, desc_b, descs)
            m_data = merge_note.structured

            s_id = m_data.get("merged_source_id")
            t_id = m_data.get("merged_target_id")
            m_desc = m_data.get("merged_description")
            if s_id and t_id and m_desc:
                _insert_edge(global_state, s_id, t_id, m_desc)
                log_system(f"已融合图边: {s_id} -> {t_id}")

    return data.get("new_entities_mentioned", [])


def _insert_edge(global_state: GlobalState, source_id: str, target_id: str, desc: str):
    etype, ent = global_state.get_entity_by_id(source_id)
    if ent:
        if etype == "place":
            ent.connections[target_id] = desc
        else:
            ent.relationships[target_id] = desc
