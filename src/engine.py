"""核心规则引擎 —— 所有可判定逻辑的确定性计算模块。

本模块是 PBTA 规则系统的"数学层"，负责力量值计算、掷骰解析、状态叠加/溢出、
极限达成检测等纯计算任务。按照项目设计原则，这里全部用纯 Python 实现，
零 LLM token 消耗，结果完全确定性。

主要概念：
    power（力量值）: 行动投骰时的加值，由匹配标签、状态等因素综合决定
    ticked_boxes（打勾槽位）: PBTA 状态系统的水位标记，Tier 1-6
    nudge（轻推）: 状态自然恶化一级，来自 Otherscape 机制
"""

from __future__ import annotations

import logging
import random

from src.models import Challenge, Character, PowerTag, RollResult, Status, StoryTag, WeaknessTag

logger = logging.getLogger("aitrpg.game")


def resolve_matched_tags(
    character: Character,
    challenge: Challenge | None,
    matched_power_names: list[str],
    matched_weakness_names: list[str],
) -> tuple[list[PowerTag], list[WeaknessTag]]:
    """将 TagMatcher 输出的标签名解析为强类型 Tag 对象。

    从角色和挑战的标签列表中查找匹配项。同时起到验证作用——
    LLM 返回的不存在的标签名会被静默过滤。

    Args:
        character: 当前角色
        challenge: 当前挑战（可为 None）
        matched_power_names: TagMatcher 匹配的力量标签名
        matched_weakness_names: TagMatcher 匹配的弱点标签名

    Returns:
        (resolved_power_tags, resolved_weakness_tags) 元组
    """
    all_power: list[PowerTag] = list(character.power_tags)
    all_weakness: list[WeaknessTag] = list(character.weakness_tags)
    if challenge:
        all_power.extend(challenge.base_tags)

    name_set_power = set(matched_power_names)
    name_set_weakness = set(matched_weakness_names)

    resolved_power = [t for t in all_power if t.name in name_set_power]
    resolved_weakness = [t for t in all_weakness if t.name in name_set_weakness]

    unknown_power = name_set_power - {t.name for t in all_power}
    unknown_weakness = name_set_weakness - {t.name for t in all_weakness}
    if unknown_power:
        logger.warning("丢弃 LLM 返回的未知力量标签: %s", unknown_power)
    if unknown_weakness:
        logger.warning("丢弃 LLM 返回的未知弱点标签: %s", unknown_weakness)

    return resolved_power, resolved_weakness


def calculate_power(
    power_tags: list[PowerTag],
    weakness_tags: list[WeaknessTag],
    best_status_tier: int = 0,
    worst_status_tier: int = 0,
) -> int:
    """计算一次行动的力量值（power）。

    力量值是掷骰的固定加值，决定行动的成功概率。
    计算公式：max(力量标签数 - 弱点标签数 + 最佳状态Tier - 最差状态Tier, 1)
    底线为 1，确保即使在最不利的情况下也有基本的行动可能。

    Args:
        power_tags: 本行动命中的 PowerTag 对象列表
        weakness_tags: 本行动命中的 WeaknessTag 对象列表
        best_status_tier: 施加影响的最高正面状态 Tier（默认 0）
        worst_status_tier: 施加影响的最高负面状态 Tier（默认 0）

    Returns:
        int: 力量值，最小为 1
    """
    tag_power = len(power_tags) - len(weakness_tags)
    return max(tag_power + best_status_tier - worst_status_tier, 1)


def roll_dice(power: int) -> RollResult:
    """执行 PBTA 标准 2d6 + power 掷骰。

    结果判定：
        total >= 10 → full_success（完全成功）
        total >= 7  → partial_success（部分成功）
        total < 7   → failure（失败）

    Args:
        power: 力量值，由 calculate_power() 计算得出

    Returns:
        RollResult: 包含力量值、两颗骰子的面值、总和及结果标签
    """
    d1 = random.randint(1, 6)
    d2 = random.randint(1, 6)
    total = d1 + d2 + power

    # 蛇眼（双 1）总是失败，即使总值超过 6
    if d1 == 1 and d2 == 1:
        outcome = "failure"
    elif total >= 10:
        outcome = "full_success"
    elif total >= 7:
        outcome = "partial_success"
    # 箱车（双 6）总是完全成功，即使总值低于 10
    elif d1 == 6 and d2 == 6:
        outcome = "full_success"
    else:
        outcome = "failure"

    return RollResult(power=power, dice=(d1, d2), total=total, outcome=outcome)


def apply_status(
    entity: Character | Challenge,
    status_name: str,
    tier: int,
    limit_category: str = "",
) -> Status:
    """向实体施加或叠加一个状态，支持 tick 溢出机制。

    PBTA 状态系统的核心操作。每个状态有 6 个 tier 槽位（等级 1-6）。
    施加时在对应 tier 上"打勾"。如果该 tier 已被占用，
    则自动上溢到下一个空位（tick overflow）。

    例如：已有 tier 2 被勾选，再次施加 tier 2 → 自动填充到 tier 3（如果空着）。

    Args:
        entity: 目标角色或挑战
        status_name: 状态名称（如"受伤"、"恐惧"）
        tier: 要施加的状态等级 (1-6)
        limit_category: 关联的极限类别名（用于挑战的状态追踪），可选

    Returns:
        Status: 施加后的状态对象（原地修改）

    Raises:
        TypeError: entity 不是 Character 或 Challenge
        ValueError: tier 不在 1-6 范围内
    """
    if not isinstance(entity, (Character, Challenge)):
        raise TypeError(f"entity must be Character or Challenge, got {type(entity).__name__}")
    if tier < 1 or tier > 6:
        raise ValueError(f"tier must be between 1 and 6, got {tier}")

    if status_name not in entity.statuses:
        entity.statuses[status_name] = Status(name=status_name, limit_category=limit_category)
    elif limit_category and not entity.statuses[status_name].limit_category:
        entity.statuses[status_name].limit_category = limit_category

    status = entity.statuses[status_name]

    # tick 溢出：从目标 tier 开始找第一个未被勾选的槽位
    target_box = tier
    while target_box <= 6 and target_box in status.ticked_boxes:
        target_box += 1

    if target_box <= 6:
        status.ticked_boxes.add(target_box)

    # 当前 Tier 取所有已勾选槽位的最大值
    status.current_tier = max(status.ticked_boxes) if status.ticked_boxes else 0
    return status


def remove_status(
    entity: Character | Challenge,
    status_name: str,
    tier: int,
) -> Status | None:
    """移除状态的指定一级勾选。

    从指定 tier 向下查找第一个已勾选的槽位并移除（优先移除高层级）。
    如果状态所有 tier 都被移除，则从实体上删除该状态。

    Args:
        entity: 目标角色或挑战
        status_name: 状态名称
        tier: 要移除的起始等级（从此 tier 向下搜索已勾选的 box）

    Returns:
        移除后的 Status 对象；如果状态被完全清空则返回 None
    """
    if status_name not in entity.statuses:
        return None

    status = entity.statuses[status_name]

    # 从指定 tier 向下遍历，移除第一个找到的已勾选槽位
    # 优先移除高层级：因为减益通常是从最严重的状态开始恢复
    for box in range(tier, 0, -1):
        if box in status.ticked_boxes:
            status.ticked_boxes.discard(box)
            break

    status.current_tier = max(status.ticked_boxes) if status.ticked_boxes else 0

    if status.current_tier == 0:
        del entity.statuses[status_name]
        return None

    return status


def check_limits(challenge: Challenge) -> list:
    """检查挑战是否触发了任何极限条件。

    便利封装，直接委托给 Challenge.check_limits()。

    Args:
        challenge: 要检查的挑战对象

    Returns:
        list: 被触发的 Limit 对象列表
    """
    return challenge.check_limits()


def reduce_status(
    entity: Character | Challenge,
    status_name: str,
    reduce_by: int,
) -> Status | None:
    """批量减少状态的勾选次数。

    用于治疗、恢复等需要降低多级状态的操作。
    每次循环移除一个最高级已勾选槽位，重复 reduce_by 次。
    如果在此过程中状态被完全清空，立即返回 None。

    Args:
        entity: 目标角色或挑战
        status_name: 状态名称
        reduce_by: 要减少的等级数（≥1）

    Returns:
        减少后的 Status 对象；如果状态被清空则返回 None

    Raises:
        TypeError: entity 不是 Character 或 Challenge
    """
    if not isinstance(entity, (Character, Challenge)):
        raise TypeError(f"entity must be Character or Challenge, got {type(entity).__name__}")
    if reduce_by < 1:
        return None

    for _ in range(reduce_by):
        if status_name not in entity.statuses:
            return None
        status = entity.statuses[status_name]

        # 找到当前最高已勾选的 tier
        max_tier = max(status.ticked_boxes) if status.ticked_boxes else 0
        if max_tier == 0:
            break

        # 从最高级向下找第一个已勾选槽位并移除
        for box in range(max_tier, 0, -1):
            if box in status.ticked_boxes:
                status.ticked_boxes.discard(box)
                break

        # 更新当前 tier
        status.current_tier = max(status.ticked_boxes) if status.ticked_boxes else 0

        # 所有槽位清空 → 删除状态
        if status.current_tier == 0:
            del entity.statuses[status_name]
            return None

    if status_name in entity.statuses:
        return entity.statuses[status_name]
    return None


def add_story_tag(
    entity: Character | Challenge,
    name: str,
    description: str = "",
    is_single_use: bool = False,
) -> StoryTag:
    """为实体添加一个叙事标签（Story Tag）。

    叙事标签是临时或情境性的标记，例如"被警方通缉"、"拥有地图"等。
    与力量/弱点标签不同，叙事标签不参与力量值计算，
    但可能被 Agent 在效果推演中引用。

    Args:
        entity: 目标角色或挑战
        name: 标签名称
        description: 标签描述，可选
        is_single_use: 是否为一次性标签（用完即销毁）

    Returns:
        StoryTag: 新创建的标签对象

    Raises:
        TypeError: entity 不是 Character 或 Challenge
    """
    if not isinstance(entity, (Character, Challenge)):
        raise TypeError(f"entity must be Character or Challenge, got {type(entity).__name__}")
    tag = StoryTag(name=name, description=description, is_single_use=is_single_use)
    entity.story_tags[name] = tag
    return tag


def remove_story_tag(
    entity: Character | Challenge,
    name: str,
) -> StoryTag | None:
    """从实体移除一个叙事标签。

    Args:
        entity: 目标角色或挑战
        name: 要移除的标签名称

    Returns:
        被移除的 StoryTag 对象；如果标签不存在则返回 None

    Raises:
        TypeError: entity 不是 Character 或 Challenge
    """
    if not isinstance(entity, (Character, Challenge)):
        raise TypeError(f"entity must be Character or Challenge, got {type(entity).__name__}")
    return entity.story_tags.pop(name, None)


def nudge_status(
    entity: Character | Challenge,
    status_name: str,
) -> Status:
    """将状态恶化一级（nudge）。

    "Nudge" 是来自 Otherscape 的机制：状态随时间或剧情自然恶化，
    而非由特定行动造成。如果目标 tier 已被占用则上溢。

    如果状态尚不存在，会自动创建并设为 tier 1。
    如果状态已达 tier 6（最高级），不做任何操作。

    Args:
        entity: 目标角色或挑战
        status_name: 状态名称

    Returns:
        Status: 恶化后的状态对象

    Raises:
        TypeError: entity 不是 Character 或 Challenge
    """
    if not isinstance(entity, (Character, Challenge)):
        raise TypeError(f"entity must be Character or Challenge, got {type(entity).__name__}")

    if status_name not in entity.statuses:
        entity.statuses[status_name] = Status(name=status_name, current_tier=1, ticked_boxes={1})
        return entity.statuses[status_name]

    status = entity.statuses[status_name]
    if status.current_tier >= 6:
        return status

    # 向下一级恶化，如果该级已被占用则上溢
    target_box = status.current_tier + 1
    while target_box <= 6 and target_box in status.ticked_boxes:
        target_box += 1

    if target_box <= 6:
        status.ticked_boxes.add(target_box)

    status.current_tier = max(status.ticked_boxes) if status.ticked_boxes else 0
    return status
