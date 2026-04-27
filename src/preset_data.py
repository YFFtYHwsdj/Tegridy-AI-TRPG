from src.models import Tag, Limit, Challenge, Character

DEMO_SCENE_DESCRIPTION = """
赛博朋克世界《异景》。巨型都市底层的一家嘈杂酒吧"最后一杯"。
霓虹招牌在雨中闪烁，门内传来低沉的贝斯声和廉价合成酒精的气味。

Kael 追踪一个名叫 Miko 的中间人来到这里。她手上有 Kael 的雇主需要的情报。
但 Miko 从来不做亏本买卖，而且她身边总有两个魁梧的保镖。
"""

DEMO_CHARACTER = Character(
    name="Kael",
    description="前公司安保干员，现在靠街头情报网过活。身手利落，人脉广但信用破产。",
    power_tags=[
        Tag(name="前公司安保", tag_type="power", description="受过专业的安保和战斗训练"),
        Tag(name="街头线人网", tag_type="power", description="在底层有广泛的情报来源和人脉"),
        Tag(name="快速拔枪", tag_type="power", description="枪法快且准，近距离战斗专家"),
        Tag(name="读懂房间", tag_type="power", description="擅长观察气氛和他人的真实意图"),
    ],
    weakness_tags=[
        Tag(name="信用破产", tag_type="weakness", description="在圈子里名声不好，没人愿意先给好处"),
    ],
)

DEMO_CHALLENGE = Challenge(
    name="Miko 与她的保镖",
    description=(
        "Miko 是本地帮派「赤色数据」的情报中间人，在这一行摸爬滚打了十年。"
        "她穿着剪裁利落的合成皮夹克，指尖夹着细长的电子烟，蓝色的LED光在她吐字时明灭闪烁。"
        "她精明、多疑、从不先开口——让别人先亮牌是她的生存法则。\n\n"
        "两个保镖如影随形：左边那个颅骨上有散热槽，是退伍的伤痛干员，"
        "反应速度比大多数人的拔枪更快；右边那个脖颈嵌着液压管，是个沉默的巨汉，"
        "据说能用单手捏碎赛博改造过的颅骨。他们从不主动开口，但四只眼睛像扫描仪一样在Kael身上来回切割。\n\n"
        "Miko 不做亏本买卖——情报就是她的货币。她不喜欢在公共场合闹大——至少在酒吧里不会。"
        "但如果被逼急了，她也绝不会手软。她的软肋是自尊心：被当众羞辱会让她失去冷静。"
    ),
    limits=[
        Limit(name="说服或威胁", max_tier=3),
        Limit(name="伤害或制服", max_tier=4),
    ],
    base_tags=[
        Tag(name="精明的谈判者", tag_type="power", description="从不让步，除非对方亮出足够的筹码。善于在对话中设置陷阱"),
        Tag(name="两个专业保镖", tag_type="power", description="退役伤痛干员和液压巨汉，反应速度和破坏力远超普通打手"),
        Tag(name="帮派情报网", tag_type="power", description="在帮派内部消息灵通，很可能已经知道Kael的真实底细"),
        Tag(name="主场优势", tag_type="power", description="「最后一杯」是她的地盘——酒保、常客、角落的逃生门，都在她掌控之中"),
    ],
    notes=(
        "威胁→后果参考（供后果Agent使用）：\n"
        "· 保镖威慑 → 保镖介入造成物理压制（「被压制-2」或新增「安保守卫」挑战）\n"
        "· 公开施压 → 「当众出丑-2」或援引Kael的「信用破产」弱点标签\n"
        "· 掏枪 → 「被枪指-3」或直接射击「枪伤-2」\n"
        "· 呼叫增援 → 新增「帮派成员」挑战（规模1），或使场景增加混乱因素\n"
        "· 拒绝谈判 → 「被羞辱-2」或燃尽一个社交相关标签\n\n"
        "Miko 在酒吧里绝不会先动手——但如果对方先出手，保镖的反应速度会让大多数佣兵后悔。"
        "她的软肋是自尊心：被当众羞辱会让她失去冷静，这是少数能让她判断失误的方式。"
        "如果Kael能证明自己的情报价值（或制造足够大的威胁），她可能愿意交换。"
    ),
)
