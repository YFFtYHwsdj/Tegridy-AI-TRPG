"""预置数据 —— Demo 场景的角色、挑战和场景构建。

提供赛博朋克风格的单场景 Demo 数据，包含：
    - DEMO_CHARACTER: 玩家角色 Kael（前公司安保干员）
    - build_demo_scene(): 构建包含 NPC、物品、线索的完整场景
"""

from src.models import NPC, Character, Clue, GameItem, PowerTag, StoryTag, WeaknessTag
from src.state.scene_state import SceneState

DEMO_WORLDVIEW = "这是一个赛博朋克世界。科技、黑客、枪战、街头谈判、超自然神话力量都可能是行动的一部分。风格：硬朗、有质感、氛围浓厚。挑战常常包含道德困境或艰难选择。"

DEMO_SCENE_DESCRIPTION = """
赛博朋克世界《异景》。下着酸雨的阴暗死胡同，旁边是散发着馊味的合成面条摊，霓虹招牌在雨中闪烁短路。

Kael 刚刚完成了一单看似简单的“跑腿”任务，手里提着一个生物锁死的手提箱。但接头人没有出现，反而是三个带着廉价义体武器的底层帮派混混堵住了胡同口。对方显然是提前收到了风声，专门来抢箱子的。
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

    创建包含三个帮派混混 NPC、可见/隐藏物品和隐藏线索的完整 SceneState。

    Returns:
        完整的 SceneState 对象
    """
    scene = SceneState(scene_description=DEMO_SCENE_DESCRIPTION)

    # 场景全局故事标签
    scene.story_tags["acid_rain"] = StoryTag(name="酸雨", description="持续伤害，降低能见度")
    scene.story_tags["narrow_alley"] = StoryTag(
        name="狭窄地形", description="限制了大型武器和闪避空间"
    )

    scene.scene_items_visible["briefcase"] = GameItem(
        item_id="briefcase",
        name="生物锁手提箱",
        description="Kael 护送的任务物品。带有未知的生物识别锁，材质极其坚固。",
        location="Kael 手中",
        tags=[PowerTag("坚固防弹", "关键时刻或许可以用来挡子弹")],
    )

    scene.scene_items_visible["noodle_pot"] = GameItem(
        item_id="noodle_pot",
        name="翻滚的合成面条汤锅",
        description="旁边面条摊上正在沸腾的汤锅，散发着劣质香精和高温蒸汽。",
        location="巷口面条摊",
        tags=[PowerTag("高温烫伤", "如果泼在人身上会造成严重的痛苦")],
    )

    scene.scene_items_hidden["sewer_grate"] = GameItem(
        item_id="sewer_grate",
        name="松动的下水道格栅",
        description="被垃圾掩盖的下水道入口，格栅已经生锈松动。可以作为紧急逃生路线。",
        location="垃圾箱后面",
        tags=[PowerTag("隐蔽逃生路线", "通向错综复杂的地下管网")],
    )

    scene.clues_hidden["gang_tattoo"] = Clue(
        clue_id="gang_tattoo",
        name="铁锈犬帮派纹身",
        description="这几个混混脖子后方有微小的'铁锈犬'电子纹身。这是一个活跃在几个街区外的暴力帮派，绝不会无缘无故跑到这里来抢劫。有人雇了他们。",
    )

    scene.clues_hidden["tracker_signal"] = Clue(
        clue_id="tracker_signal",
        name="微弱的追踪频段",
        description="Kael 的终端捕捉到了附近有一个微弱的未注册追踪信号。信号源就在手提箱的夹层里——他被雇主（或者接头人）定位并出卖了。",
    )

    leader = NPC(
        npc_id="thug_leader",
        name="剃刀帮众",
        description="带头的混混，双臂改造了便宜但致命的螳螂刀。态度极其嚣张。",
        tags=[
            PowerTag("螳螂刀", "近战极具杀伤力，能切开防弹衣"),
        ],
        known_clue_ids=["gang_tattoo"],
    )
    scene.npcs["thug_leader"] = leader

    shooter = NPC(
        npc_id="thug_shooter",
        name="持枪混混",
        description="紧张兮兮的年轻混混，手里拿着一把自制的动能手枪，枪口指着 Kael 晃来晃去。",
        tags=[
            PowerTag("自制火器", "威力不俗，但有卡壳甚至炸膛的风险"),
        ],
    )
    scene.npcs["thug_shooter"] = shooter

    brute = NPC(
        npc_id="thug_brute",
        name="义体肌肉男",
        description="赤裸上身的壮汉，植入了劣质的皮下装甲和液压肌肉。动作迟缓但力量惊人。",
        tags=[
            PowerTag("皮下装甲", "能抵挡小口径子弹和轻微利器切割"),
            PowerTag("液压巨力", "被他抓到会被碾碎骨头"),
        ],
    )
    scene.npcs["thug_brute"] = brute

    return scene
