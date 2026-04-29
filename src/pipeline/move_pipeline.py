"""Action 流程编排 —— 多 Agent 接力执行的 Pipe-and-Filter 流水线。

本模块是系统的核心控制器。MovePipeline 协调 Tag 匹配、掷骰、效果推演、
后果生成、叙事渲染和校验应用的全流程。每条流水线对应一次玩家行动，
按照 PBTA 规则完成"意图 → 判定 → 效果 → 后果 → 叙事"的完整序列。

流水线模式：
    - run_single_move_pipeline: 标准完整流水线（单步 action）
    - run_quick_pipeline: 快速流水线（跳过效果推演 Agent）
    - process_split_actions: 复合 action 拆分流水线（多步子 action 接力）
"""

from __future__ import annotations

from typing import Any

from src.agents import (
    ConsequenceAgent,
    ContinuationCheckAgent,
    EffectActualizationAgent,
    NarratorAgent,
    QuickConsequenceAgent,
    QuickNarratorAgent,
    TagMatcherAgent,
)
from src.display.console import ConsoleDisplay
from src.engine import calculate_power, roll_dice
from src.llm_client import LLMClient
from src.logger import log_roll, log_system
from src.pipeline._tag_utils import extract_status_tiers, extract_tag_names
from src.pipeline.pipeline_result import PipelineResult
from src.state.game_state import GameState


def _summarize_last_sub(roll, effects, cons) -> str:
    """生成上一步子 action 的摘要文本，用于继续性检查。

    Args:
        roll: 上一步的 RollResult
        effects: 上一步的效果列表
        cons: 上一步的后果列表

    Returns:
        格式化的摘要字符串
    """
    if roll is None:
        return "（上一步无有效掷骰）"
    parts = [f"掷骰结果: {roll.outcome}"]
    if effects:
        parts.append("效果: " + ", ".join(e.get("label", e.get("operation", "?")) for e in effects))
    if cons:
        parts.append("后果: " + ", ".join(c.get("threat_manifested", "?") for c in cons))
    return "; ".join(parts) if parts else "（无效果信息）"


class MovePipeline:
    """Action 流水线 —— 多 Agent 接力执行的核心控制器。

    初始化时创建所有所需的 Agent 实例（Tag 匹配、效果推演、后果、
    叙述者、继续性检查、校验），每条流水线调用时按固定顺序执行它们。

    关键方法：
        run_single_move_pipeline: 完整流水线，适用于一般 action
        run_quick_pipeline: 快速流水线，跳过效果推演，适用于简单 action
        process_split_actions: 复合 action 拆分执行
        validate_and_apply: 校验叙事输出并将其中的线索/物品揭示应用到游戏状态
    """

    def __init__(self, llm: LLMClient, state: GameState, display: ConsoleDisplay):
        self.llm = llm
        self.state = state
        self.display = display

        # 创建所有 Agent 实例
        self.tag_agent = TagMatcherAgent(llm)
        self.effect_agent = EffectActualizationAgent(llm)
        self.consequence_agent = ConsequenceAgent(llm)
        self.quick_consequence_agent = QuickConsequenceAgent(llm)
        self.narrator = NarratorAgent(llm)
        self.quick_narrator = QuickNarratorAgent(llm)
        self.continuation_check = ContinuationCheckAgent(llm)

    def _run_tag_and_roll(self, intent_note, ctx, sub_action=None):
        """流水线阶段1: 标签匹配 + 掷骰。

        执行 Tag 匹配 Agent 获取命中的力量/弱点标签，
        提取标签名和状态 tier，计算力量值并掷骰。

        Args:
            intent_note: 意图解析 Agent 的分析便签
            ctx: 当前场景上下文
            sub_action: 子 action 数据（复合 action 场景），可选

        Returns:
            (tag_note, roll) 元组
        """
        tag_note = self.tag_agent.execute(intent_note, ctx, sub_action=sub_action)

        matched_power = tag_note.structured.get("matched_power_tags", [])
        matched_weakness = tag_note.structured.get("matched_weakness_tags", [])
        power_tag_names = extract_tag_names(matched_power)
        weakness_tag_names = extract_tag_names(matched_weakness)

        best_status_tier, worst_status_tier = extract_status_tiers(tag_note)

        power = calculate_power(
            power_tag_names,
            weakness_tag_names,
            best_status_tier=best_status_tier,
            worst_status_tier=worst_status_tier,
        )
        roll = roll_dice(power)

        log_roll(power, roll.dice, roll.total, roll.outcome, power_tag_names, weakness_tag_names)

        return tag_note, roll

    def run_single_move_pipeline(self, intent_note, ctx, sub_action=None) -> PipelineResult:
        """执行标准完整流水线。

        阶段顺序：
            1. 标签匹配 + 掷骰 (_run_tag_and_roll)
            2. 效果推演 (EffectActualizationAgent)
            3. 后果生成 (ConsequenceAgent) — 仅在 partial_success 或 failure 时
            4. 叙事渲染 (NarratorAgent)
            5. 校验与生效 (validate_and_apply)

        Args:
            intent_note: 意图解析 Agent 的分析便签
            ctx: 当前场景上下文
            sub_action: 子 action 数据（复合 action 场景），可选

        Returns:
            PipelineResult: 包含各阶段 AgentNote 和掷骰结果的完整数据
        """
        tag_note, roll = self._run_tag_and_roll(intent_note, ctx, sub_action)

        effect_note = self.effect_agent.execute(
            intent_note, tag_note, roll, ctx, sub_action=sub_action
        )

        # 仅在未完全成功时生成后果（部分成功和失败都有代价）
        consequence_note = None
        if roll.outcome in ("partial_success", "failure"):
            consequence_note = self.consequence_agent.execute(intent_note, effect_note, roll, ctx)

        narrator_note = self.narrator.execute(
            intent_note,
            effect_note,
            roll,
            ctx,
            consequence_note=consequence_note,
        )

        self.validate_and_apply(narrator_note, ctx)

        return PipelineResult(
            tag_note=tag_note,
            roll=roll,
            effect_note=effect_note,
            consequence_note=consequence_note,
            narrator_note=narrator_note,
        )

    def run_quick_pipeline(self, intent_note, ctx) -> PipelineResult:
        """执行快速流水线（跳过效果推演 Agent）。

        适用于效果由系统直接裁定、不需要 LLM 推演的简单 action。
        阶段顺序：标签匹配+掷骰 → 快速后果 → 快速叙事 → 校验生效。

        Args:
            intent_note: 意图解析 Agent 的分析便签
            ctx: 当前场景上下文

        Returns:
            PipelineResult（effect_note 为 None）
        """
        tag_note, roll = self._run_tag_and_roll(intent_note, ctx)

        consequence_note = None
        if roll.outcome in ("partial_success", "failure"):
            consequence_note = self.quick_consequence_agent.execute(intent_note, roll, ctx)

        narrator_note = self.quick_narrator.execute(
            intent_note,
            roll,
            ctx,
            consequence_note=consequence_note,
        )

        self.validate_and_apply(narrator_note, ctx)

        return PipelineResult(
            tag_note=tag_note,
            roll=roll,
            effect_note=None,
            consequence_note=consequence_note,
            narrator_note=narrator_note,
        )

    def validate_and_apply(self, narrator_note, ctx=None):
        """应用叙事输出中的揭示和物品转移。

        直接信任叙述者的 revelation_decisions 和 item_transfers，
        不经过 LLM 校验。

        设计决策——为何不在此处引入独立的验证器 Agent：

        1. **叙述者的可靠性保障**：叙述者 Agent 的 system prompt 中注入了
           _HIDDEN_NOTICE 约束，明确要求"标记为(隐藏)的线索、物品及其详情
           尚未被玩家角色发现，叙事中不要直接提及。如果玩家的行动在逻辑上
           自然应该触达它们，通过 revelation_decisions 标记揭示"。这意味着
           叙述者在生成叙事时已经在同一推理上下文中完成了"是否应该揭示"
           的判断，其 revelation_decisions 与该叙事之间保持内在一致性。

        2. **风险场景**：
           - 叙述者可能因为 LLM 幻觉而在叙事中**间接**透露隐藏信息（如
             不通过 revelation_decisions 却在叙事文本中暗示密道存在）。
             但这种泄露发生在前端的叙事文本中（玩家可直接读取），后端
             的 revelation_decisions 只是将线索从 hidden→visible，属于
             信息可见性变更而非信息泄露源头。
           - 叙述者可能错误标记不相关的线索为已揭示。这会导致额外线索
             意外暴露给玩家——但这类错误在直接信任模式下和经 LLM 验证
             模式下出现的概率相似（验证器同样可能产生幻觉）。

        3. **监控机制**：
           - revelation_decisions 和 item_transfers 只执行纯数据操作
             （字典 key 移动），不涉及 LLM 调用或随机性。
           - 所有被揭示的线索/物品 ID 在 _apply_revelations 中会与游戏
             状态中的实际 hidden 字典做交叉校验：若 ID 不存在于 hidden
             字典中，操作静默跳过（不会导致崩溃或状态污染）。
           - 对于未找到的物品 ID，_apply_item_transfers 会通过 log_system
             记录 warning 级别日志，便于事后排查异常场景。

        Args:
            narrator_note: 叙述者 Agent 的分析便签
            ctx: 当前场景上下文（用于 emergent 物品创建）
        """
        self._apply_revelations(narrator_note.structured)
        self._apply_item_transfers(narrator_note.structured, ctx)

    def _apply_revelations(self, structured: dict):
        """执行最终决策中的揭示操作。

        从 structured dict 的 revelation_decisions 中提取揭示指令，
        将隐藏的线索/物品从隐藏字典转移到可见字典。

        Args:
            structured: 包含 revelation_decisions 的 dict
        """
        scene = self.state.scene
        decisions = structured.get("revelation_decisions", {})

        for clue_id in decisions.get("reveal_clue_ids", []):
            if clue_id in scene.clues_hidden:
                clue = scene.clues_hidden.pop(clue_id)
                scene.clues_visible[clue_id] = clue

        for item_id in decisions.get("reveal_item_ids", []):
            found = False
            if item_id in scene.scene_items_hidden:
                item = scene.scene_items_hidden.pop(item_id)
                scene.scene_items_visible[item_id] = item
                found = True
            else:
                for npc in scene.npcs.values():
                    if item_id in npc.items_hidden:
                        item = npc.items_hidden.pop(item_id)
                        npc.items_visible[item_id] = item
                        found = True
                        break
            if not found:
                log_system(f"未找到物品 '{item_id}'", level="warning")

    def _apply_item_transfers(self, structured: dict, ctx=None):
        """执行最终决策中的物品转移。

        处理物品在不同位置之间的移动（场景 ↔ 角色 ↔ NPC），
        支持自动创建 emergent 物品（叙述者即兴引入的新物品）。

        Args:
            structured: 包含 item_transfers 的 dict
            ctx: 当前场景上下文（用于 emergent 物品创建）
        """
        _scene = self.state.scene
        transfers = structured.get("item_transfers", [])
        location_updates = structured.get("location_text_updates", [])

        # 构建物品位置更新映射
        loc_map = {u["item_id"]: u["new_location"] for u in location_updates if isinstance(u, dict)}

        for t in transfers:
            if not isinstance(t, dict):
                continue
            item_id = t.get("item_id") or t.get("item", "")
            from_loc = t.get("from", "")
            to_loc = t.get("to", "")
            if not item_id or not from_loc or not to_loc:
                continue

            # 从源位置取出物品
            item = self._pop_item(item_id, from_loc)
            if item is None:
                # 物品不存在 → 尝试自动创建 emergent 物品
                created = self._create_emergent_item(item_id, ctx)
                if not created:
                    log_system(f"未找到且无法创建 '{item_id}' (from={from_loc})", level="warning")
                    continue
                item = created
                log_system(f"转移时自动创建 '{item_id}'", level="debug")

            # 更新物品的 location 文本
            if item_id in loc_map:
                item.location = loc_map[item_id]

            # 插入到目标位置
            self._insert_item(item_id, item, to_loc)

    def _create_emergent_item(self, item_name: str, ctx=None):
        """创建 emergent 物品 —— 叙述者即兴引入的新物品。

        LLM 叙述者可能在叙事中引入原数据中不存在的物品。
        此时调用 ItemCreator Agent 根据上下文自动生成物品数据。

        Args:
            item_name: 物品名称
            ctx: 当前场景上下文（用于 ItemCreatorAgent）

        Returns:
            新创建的 GameItem 对象，创建失败返回 None
        """
        from src.agents.item_creator import ItemCreatorAgent

        if not hasattr(self, "item_creator"):
            self.item_creator = ItemCreatorAgent(self.llm)

        creator_note = self.item_creator.execute(item_name, ctx)
        item_data = creator_note.structured
        if not item_data:
            return None

        from src.models import GameItem, Tag

        # 解析物品标签（支持 dict 和 str 两种格式）
        tags = []
        for t in item_data.get("tags", []):
            if isinstance(t, dict):
                tags.append(
                    Tag(
                        name=t.get("name", ""),
                        tag_type=t.get("tag_type", "power"),
                        description=t.get("description", ""),
                    )
                )
            elif isinstance(t, str):
                tags.append(Tag(name=t, tag_type="power"))

        weakness = None
        w = item_data.get("weakness")
        if w and isinstance(w, dict):
            weakness = Tag(
                name=w.get("name", ""),
                tag_type="weakness",
                description=w.get("description", ""),
            )

        item_id = item_data.get("item_id") or item_name
        return GameItem(
            item_id=item_id,
            name=item_name,
            description=item_data.get("description", ""),
            tags=tags,
            weakness=weakness,
            location=item_data.get("location", ""),
        )

    def _pop_item(self, item_id: str, location: str):
        """从指定位置取出物品（从可见或隐藏字典中移除）。

        支持的位置格式：
            - "scene": 场景物品
            - "character": 角色物品
            - "npc.<npc_id>": 指定 NPC 的物品

        Args:
            item_id: 物品 ID
            location: 位置标识符

        Returns:
            取出的物品对象，未找到返回 None
        """
        scene = self.state.scene
        if location == "scene":
            for d in (scene.scene_items_visible, scene.scene_items_hidden):
                if item_id in d:
                    return d.pop(item_id)
        elif location == "character":
            char = self.state.character
            if char:
                for d in (char.items_visible, char.items_hidden):
                    if item_id in d:
                        return d.pop(item_id)
        elif location.startswith("npc."):
            npc_id = location[4:]
            npc = scene.npcs.get(npc_id)
            if npc:
                for d in (npc.items_visible, npc.items_hidden):
                    if item_id in d:
                        return d.pop(item_id)
        return None

    def _insert_item(self, item_id: str, item, location: str):
        """将物品插入到指定位置的可见字典。

        支持的位置格式同 _pop_item。

        Args:
            item_id: 物品 ID
            item: 物品对象
            location: 目标位置标识符
        """
        scene = self.state.scene
        if location == "scene":
            scene.scene_items_visible[item_id] = item
        elif location == "character":
            if self.state.character:
                self.state.character.items_visible[item_id] = item
        elif location.startswith("npc."):
            npc_id = location[4:]
            npc = scene.npcs.get(npc_id)
            if npc:
                npc.items_visible[item_id] = item

    def process_split_actions(self, intent_note, split_actions) -> list:
        """执行复合 action 的拆分流水线。

        当一个意图被意图解析 Agent 拆分为多个子 action（split_actions）时，
        按顺序逐个执行，每步之前检查是否可以继续（continuation_check）。

        流程：
            1. 对每个子 action 运行完整流水线
            2. 执行前检查上一步结果是否阻止继续
            3. 将上一步的掷骰/效果/后果作为上下文传递给下一步

        Args:
            intent_note: 意图解析 Agent 的分析便签
            split_actions: 子 action 列表

        Returns:
            PipelineResult 列表（可能因 blocked 而提前终止）
        """
        self.display.print_split_action_header(len(split_actions))

        prev_roll = None
        prev_effects = []
        prev_cons = []
        results = []

        for i, sub in enumerate(split_actions):
            if sub is None:
                continue
            if not isinstance(sub, dict):
                sub = {"action_summary": str(sub)}
            sub: dict[str, Any] = dict(sub, _index=i)

            self.display.print_split_sub_header(
                i + 1, len(split_actions), sub.get("action_summary", "?")
            )

            # 非首步：检查上一步结果是否允许继续
            if i > 0:
                ctx = self.state.make_context()
                check_note = self.continuation_check.execute(
                    sub,
                    ctx,
                    _summarize_last_sub(prev_roll, prev_effects, prev_cons),
                )
                can_continue = check_note.structured.get("can_continue", True)
                if not can_continue:
                    reason = check_note.structured.get("reason", "")
                    self.display.print_split_blocked(sub.get("action_summary", "?"), reason)
                    return results

            ctx = self.state.make_context(sub.get("fragment", ""))
            result = self.run_single_move_pipeline(intent_note, ctx, sub_action=sub)
            results.append(result)

            # 保存当前步的结果供下一步的继续性检查使用
            prev_roll = result.roll
            prev_effects = (
                result.effect_note.structured.get("effects", []) if result.effect_note else []
            )
            prev_cons = (
                result.consequence_note.structured.get("consequences", [])
                if result.consequence_note
                else []
            )

        return results
