from src.models import Tag, Limit, Challenge, Character, GameItem, Clue, NPC
from src.state.scene_state import SceneState

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

MIKO_CHALLENGE = Challenge(
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
        Tag(name="精明的谈判者", tag_type="power", description="从不让步，除非对方亮出足够的筹码"),
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

DEMO_CHALLENGE = MIKO_CHALLENGE


def build_demo_scene() -> SceneState:
    scene = SceneState(scene_description=DEMO_SCENE_DESCRIPTION)

    scene.add_challenge(MIKO_CHALLENGE)

    scene.scene_items_visible["datapad_bar"] = GameItem(
        item_id="datapad_bar",
        name="Miko的数据板",
        description="纤薄的全息数据板，屏幕上是密文滚动的情报摘要。搁在吧台上，微微发光。",
        location="吧台台面上",
        tags=[Tag("情报来源", "power", "可能包含Miko正在浏览的交易信息")],
    )

    scene.scene_items_visible["weapon_locker"] = GameItem(
        item_id="weapon_locker",
        name="应急武器柜",
        description="酒吧后墙的金属柜，生物识别锁。传闻老板在里面存了应对麻烦的'最终方案'。",
        location="酒吧后墙",
        tags=[Tag("应急武器", "power", "内含一把霰弹枪——如果能打开的话")],
    )

    scene.scene_items_hidden["medkit_bar"] = GameItem(
        item_id="medkit_bar",
        name="军规急救包",
        description="军规级自凝血注射器和创伤敷料，装在防水尼龙袋里。可能是某个退伍佣兵遗忘的。",
        location="吧台下方暗格深处",
        tags=[Tag("急救包", "power", "一次性的紧急治疗用具")],
    )

    scene.clues_hidden["comm_log"] = Clue(
        clue_id="comm_log",
        name="保镖通讯记录",
        description="退役伤痛干员腕部终端上的未加密短讯——后巷有一辆装甲车待命，预计15分钟后到达。这是交易失败的后备方案。",
    )

    scene.clues_hidden["miko_motive"] = Clue(
        clue_id="miko_motive",
        name="Miko的真正动机",
        description="Miko其实在找机会背叛赤色数据。Kael的出现对她来说是一个完美的掩护——她需要一个外部力量来分散帮派的注意力。芯片里的情报只是诱饵。",
    )

    miko_npc = NPC(
        npc_id="miko",
        name="Miko",
        description="赤色数据的资深情报中间人。合成皮夹克，细长电子烟，从不先亮牌。",
        tags=[
            Tag("精明的谈判者", "power", "从不让步，善于在对话中设置陷阱"),
            Tag("帮派情报网", "power", "在帮派内部消息灵通"),
        ],
        known_clue_ids=["comm_log", "miko_motive"],
        known_item_ids=["chip_encrypted", "miko_communicator"],
        items_visible={
            "miko_communicator": GameItem(
                item_id="miko_communicator",
                name="加密通讯器",
                description="系在腰带上的军用级加密通讯器。红色指示灯有节奏地闪烁——随时在线。",
                location="Miko腰带上的皮套内",
                tags=[Tag("加密通讯", "power", "可联系帮派内线")],
            ),
        },
        items_hidden={
            "chip_encrypted": GameItem(
                item_id="chip_encrypted",
                name="加密数据芯片",
                description="一枚微型芯片，刻有赤色数据的密级标记。藏在Miko合成皮夹克内侧的暗袋里。",
                location="Miko合成皮夹克内侧暗袋",
                tags=[Tag("关键情报", "power", "包含赤色数据对Kael雇主的追踪记录——有人在出卖他")],
            ),
        },
    )
    scene.npcs["miko"] = miko_npc

    guard_left = NPC(
        npc_id="bodyguard_left",
        name="退役伤痛干员",
        description="颅骨上有散热槽的退伍干员。反应速度比大多数人拔枪更快。沉默而专注，眼神像扫描仪一样来回切割。",
        tags=[
            Tag("赛博反射", "power", "神经加速植入物赋予超人的反应速度"),
        ],
        known_clue_ids=["comm_log"],
        known_item_ids=["guard_sidearm"],
        items_visible={
            "guard_sidearm": GameItem(
                item_id="guard_sidearm",
                name="伤痛干员的配枪",
                description="定制的重型手枪，枪口补偿器暗示着使用者的射击习惯。快拔枪套固定在右腿外侧。",
                location="右侧大腿快拔枪套",
                tags=[Tag("重火力", "power", "高制止力的定制弹药")],
            ),
        },
    )
    scene.npcs["bodyguard_left"] = guard_left

    guard_right = NPC(
        npc_id="bodyguard_right",
        name="液压巨汉",
        description="脖颈嵌着液压管的沉默巨人。据说能用单手捏碎赛博改造过的颅骨。从不主动开口。",
        tags=[
            Tag("超人类力量", "power", "液压增强肌肉纤维提供惊人的物理破坏力"),
        ],
        known_item_ids=["weapon_locker"],
    )
    scene.npcs["bodyguard_right"] = guard_right

    return scene
