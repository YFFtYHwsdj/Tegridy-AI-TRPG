from src.models import Challenge, Limit, Status

challenge = Challenge(
    name="Miko 与她的保镖",
    description="",
    limits=[
        Limit(name="说服或威胁", max_tier=3),
        Limit(name="伤害或制服", max_tier=4),
    ],
    statuses={
        "愿意交易": Status(
            name="愿意交易", current_tier=3, limit_category="说服", ticked_boxes={2, 3}
        ),
        "被误导": Status(name="被误导", current_tier=2, limit_category="说服", ticked_boxes={2}),
    },
)

triggered = challenge.check_limits()
print("Triggered:", triggered)
print("Progress:", challenge.get_limit_progress())
