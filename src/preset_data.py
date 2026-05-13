"""预置数据 —— Demo 场景的角色、挑战和场景构建。

提供赛博朋克风格的单场景 Demo 数据，包含：
    - DEMO_CHARACTER: 玩家角色 Kael（前公司安保干员）
    - DEMO_CHALLENGE: 主挑战 Miko（情报中间人 + 两个保镖）
    - build_demo_scene(): 构建包含 NPC、物品、线索的完整场景
"""

from src.models import NPC, Character, Clue, GameItem, PowerTag, WeaknessTag
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
        PowerTag(name="前公司安保", description="受过专业的安保和战斗训练"),
        PowerTag(name="街头线人网", description="在底层有广泛的情报来源和人脉"),
        PowerTag(name="快速拔枪", description="枪法快且准，近距离战斗专家"),
        PowerTag(name="读懂房间", description="擅长观察气氛和他人的真实意图"),
    ],
    weakness_tags=[
        WeaknessTag(name="信用破产", description="在圈子里名声不好，没人愿意先给好处"),
    ],
)


def build_demo_scene() -> SceneState:
    """构建 Demo 场景。

    创建包含 Miko 挑战、NPC（Miko + 两个保镖）、
    可见/隐藏物品和隐藏线索的完整 SceneState。

    Returns:
        完整的 SceneState 对象
    """
    scene = SceneState(scene_description=DEMO_SCENE_DESCRIPTION)

    scene.scene_items_visible["datapad_bar"] = GameItem(
        item_id="datapad_bar",
        name="Miko的数据板",
        description="纤薄的全息数据板，屏幕上是密文滚动的情报摘要。搁在吧台上，微微发光。",
        location="吧台台面上",
        tags=[PowerTag("情报来源", "可能包含Miko正在浏览的交易信息")],
    )

    scene.scene_items_visible["weapon_locker"] = GameItem(
        item_id="weapon_locker",
        name="应急武器柜",
        description="酒吧后墙的金属柜，生物识别锁。传闻老板在里面存了应对麻烦的'最终方案'。",
        location="酒吧后墙",
        tags=[PowerTag("应急武器", "内含一把霰弹枪——如果能打开的话")],
    )

    scene.scene_items_hidden["medkit_bar"] = GameItem(
        item_id="medkit_bar",
        name="军规急救包",
        description="军规级自凝血注射器和创伤敷料，装在防水尼龙袋里。可能是某个退伍佣兵遗忘的。",
        location="吧台下方暗格深处",
        tags=[PowerTag("急救包", "一次性的紧急治疗用具")],
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
            PowerTag("精明的谈判者", "从不让步，善于在对话中设置陷阱"),
            PowerTag("帮派情报网", "在帮派内部消息灵通"),
        ],
        known_clue_ids=["comm_log", "miko_motive"],
        known_item_ids=["chip_encrypted", "miko_communicator"],
        items_visible={
            "miko_communicator": GameItem(
                item_id="miko_communicator",
                name="加密通讯器",
                description="系在腰带上的军用级加密通讯器。红色指示灯有节奏地闪烁——随时在线。",
                location="Miko腰带上的皮套内",
                tags=[PowerTag("加密通讯", "可联系帮派内线")],
            ),
        },
        items_hidden={
            "chip_encrypted": GameItem(
                item_id="chip_encrypted",
                name="加密数据芯片",
                description="一枚微型芯片，刻有赤色数据的密级标记。藏在Miko合成皮夹克内侧的暗袋里。",
                location="Miko合成皮夹克内侧暗袋",
                tags=[PowerTag("关键情报", "包含赤色数据对Kael雇主的追踪记录——有人在出卖他")],
            ),
        },
    )
    scene.npcs["miko"] = miko_npc

    guard_left = NPC(
        npc_id="bodyguard_left",
        name="退役伤痛干员",
        description="颅骨上有散热槽的退伍干员。反应速度比大多数人拔枪更快。沉默而专注，眼神像扫描仪一样来回切割。",
        tags=[
            PowerTag("赛博反射", "神经加速植入物赋予超人的反应速度"),
        ],
        known_clue_ids=["comm_log"],
        known_item_ids=["guard_sidearm"],
        items_visible={
            "guard_sidearm": GameItem(
                item_id="guard_sidearm",
                name="伤痛干员的配枪",
                description="定制的重型手枪，枪口补偿器暗示着使用者的射击习惯。快拔枪套固定在右腿外侧。",
                location="右侧大腿快拔枪套",
                tags=[PowerTag("重火力", "高制止力的定制弹药")],
            ),
        },
    )
    scene.npcs["bodyguard_left"] = guard_left

    guard_right = NPC(
        npc_id="bodyguard_right",
        name="液压巨汉",
        description="脖颈嵌着液压管的沉默巨人。据说能用单手捏碎赛博改造过的颅骨。从不主动开口。",
        tags=[
            PowerTag("超人类力量", "液压增强肌肉纤维提供惊人的物理破坏力"),
        ],
        known_item_ids=["weapon_locker"],
    )
    scene.npcs["bodyguard_right"] = guard_right

    return scene
