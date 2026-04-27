import random
from src.models import Character, Challenge, Status, RollResult


def calculate_power(
    matched_power_tags: list[str],
    matched_weakness_tags: list[str],
    best_status_tier: int = 0,
    worst_status_tier: int = 0,
) -> int:
    tag_power = len(matched_power_tags) - len(matched_weakness_tags)
    return max(tag_power + best_status_tier - worst_status_tier, 1)


def roll_dice(power: int) -> RollResult:
    d1 = random.randint(1, 6)
    d2 = random.randint(1, 6)
    total = d1 + d2 + power

    if total >= 10:
        outcome = "full_success"
    elif total >= 7:
        outcome = "partial_success"
    else:
        outcome = "failure"

    return RollResult(power=power, dice=(d1, d2), total=total, outcome=outcome)


def apply_status(
    entity: Character | Challenge,
    status_name: str,
    tier: int,
    limit_category: str = "",
) -> Status:
    if not isinstance(entity, (Character, Challenge)):
        raise TypeError(f"entity must be Character or Challenge, got {type(entity).__name__}")
    if tier < 1 or tier > 6:
        raise ValueError(f"tier must be between 1 and 6, got {tier}")

    if status_name not in entity.statuses:
        entity.statuses[status_name] = Status(name=status_name, limit_category=limit_category)
    elif limit_category and not entity.statuses[status_name].limit_category:
        entity.statuses[status_name].limit_category = limit_category

    status = entity.statuses[status_name]
    target_box = tier

    while target_box <= 6 and target_box in status.ticked_boxes:
        target_box += 1

    if target_box <= 6:
        status.ticked_boxes.add(target_box)

    status.current_tier = max(status.ticked_boxes) if status.ticked_boxes else 0
    return status


def remove_status(
    entity: Character | Challenge,
    status_name: str,
    tier: int,
) -> Status | None:
    if status_name not in entity.statuses:
        return None

    status = entity.statuses[status_name]

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
    return challenge.check_limits()
