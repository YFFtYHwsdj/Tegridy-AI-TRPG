"""预置数据 —— Demo 场景的角色、挑战和场景构建。

提供赛博朋克风格的单场景 Demo 数据，包含：
    - DEMO_CHARACTER: 玩家角色 Kael（前公司安保干员）
    - build_demo_scene(): 构建包含 NPC、物品、线索的完整场景，并注册到 GlobalState
"""

from src.models import NPC, GameItem, Place, PowerTag, StoryTag, Theme, WeaknessTag
from src.state.character_state import CharacterState
from src.state.global_state import GlobalState
from src.state.scene_state import SceneState

DEMO_WORLDVIEW = "这是一个赛博朋克世界。科技、黑客、枪战、街头谈判、超自然神话力量都可能是行动的一部分。风格：硬朗、有质感、氛围浓厚。挑战常常包含道德困境或艰难选择。"

DEMO_CHARACTER = CharacterState(
    name="Kael",
    description="前公司安保干员，现在靠街头情报网过活。身手利落，人脉广但信用破产。",
    themes=[
        Theme(
            name="前公司安保",
            theme_type="背景/职业",
            concept="受过专业的安保和战斗训练",
            motivation="找回失去的荣誉",
            power_tags=[
                PowerTag(
                    name="前公司安保", description="受过专业的安保和战斗训练，深谙战术小队协作"
                ),
                PowerTag(name="快速拔枪", description="枪法快且准，近距离火拼专家"),
                PowerTag(name="战术格斗", description="精通夺枪和近身CQC制服技术"),
            ],
            weakness_tags=[
                WeaknessTag(
                    name="公司通缉", description="被前雇主列入黑名单，随时可能遭遇赏金猎人"
                ),
            ],
        ),
        Theme(
            name="街头线人网",
            theme_type="资源/专长",
            concept="在底层有广泛的情报来源和人脉",
            motivation="在街头活下去",
            power_tags=[
                PowerTag(name="街头线人网", description="在底层酒吧、黑市有熟人和情报来源"),
                PowerTag(name="读懂房间", description="擅长观察气氛，一眼看穿他人的真实意图和谎言"),
                PowerTag(name="黑市渠道", description="知道去哪里搞到未注册的装备或禁药"),
            ],
            weakness_tags=[
                WeaknessTag(
                    name="信用破产", description="在圈子里名声不好，办事必须先交钱或给抵押"
                ),
            ],
        ),
        Theme(
            name="神经强化义体",
            theme_type="装备/义体",
            concept="植入了廉价但实用的神经反射和感知增强义体",
            motivation="保持对危险的极度敏锐",
            power_tags=[
                PowerTag(
                    name="突触加速器", description="危机时刻可以短暂加速神经反应，如同时间变慢"
                ),
                PowerTag(name="视觉增强", description="在黑暗和烟雾中能看清热源或夜视"),
                PowerTag(name="疼痛抑制", description="强行切断痛觉神经，无视伤痛继续战斗"),
            ],
            weakness_tags=[
                WeaknessTag(
                    name="排异反应", description="使用过度会导致神经抽搐或短暂失明，需要长期服药"
                ),
            ],
        ),
    ],
)


def build_demo_scene(global_state: GlobalState) -> SceneState:
    """构建 Demo 场景并注册全局实体。

    创建地点、NPC 和 物品，注册到 GlobalState，
    并返回一个封装好引用的 SceneState 对象。

    Args:
        global_state: 全局状态，用于注册实体

    Returns:
        初始的 SceneState 对象
    """

    # 1. 注册 Place
    alley = Place(
        place_id="alley_01",
        name="阴暗死胡同",
        description="下着酸雨的阴暗死胡同，旁边是散发着馊味的合成面条摊，霓虹招牌在雨中闪烁短路。",
    )
    global_state.places[alley.place_id] = alley

    # 2. 注册 Items
    briefcase = GameItem(
        item_id="briefcase",
        name="生物锁手提箱",
        description="Kael 护送的任务物品。带有未知的生物识别锁，材质极其坚固。",
        location="Kael 手中",
        tags=[PowerTag("坚固防弹", "关键时刻或许可以用来挡子弹")],
        notes="隐藏线索：微弱的追踪频段。信号源就在手提箱的夹层里——被雇主（或者接头人）定位并出卖了。",
    )
    noodle_pot = GameItem(
        item_id="noodle_pot",
        name="翻滚的合成面条汤锅",
        description="旁边面条摊上正在沸腾的汤锅，散发着劣质香精和高温蒸汽。",
        location="巷口面条摊",
        tags=[PowerTag("高温烫伤", "如果泼在人身上会造成严重的痛苦")],
    )
    sewer_grate = GameItem(
        item_id="sewer_grate",
        name="松动的下水道格栅",
        description="被垃圾掩盖的下水道入口，格栅已经生锈松动。可以作为紧急逃生路线。",
        location="垃圾箱后面",
        tags=[PowerTag("隐蔽逃生路线", "通向错综复杂的地下管网")],
    )
    for it in [briefcase, noodle_pot, sewer_grate]:
        global_state.items[it.item_id] = it

    # 3. 注册 NPCs
    leader = NPC(
        npc_id="thug_leader",
        name="剃刀帮众",
        description="带头的混混，双臂改造了便宜但致命的螳螂刀。态度极其嚣张。",
        tags=[PowerTag("螳螂刀", "近战极具杀伤力，能切开防弹衣")],
        notes="隐藏线索：脖子后方有微小的'铁锈犬'电子纹身。这是一个活跃在几个街区外的暴力帮派，绝不会无缘无故跑到这里来抢劫。有人雇了他们。",
    )
    shooter = NPC(
        npc_id="thug_shooter",
        name="持枪混混",
        description="紧张兮兮的年轻混混，手里拿着一把自制的动能手枪，枪口指着 Kael 晃来晃去。",
        tags=[PowerTag("自制火器", "威力不俗，但有卡壳甚至炸膛的风险")],
    )
    brute = NPC(
        npc_id="thug_brute",
        name="义体肌肉男",
        description="赤裸上身的壮汉，植入了劣质的皮下装甲和液压肌肉。动作迟缓但力量惊人。",
        tags=[
            PowerTag("皮下装甲", "能抵挡小口径子弹和轻微利器切割"),
            PowerTag("液压巨力", "被他抓到会被碾碎骨头"),
        ],
    )
    for npc in [leader, shooter, brute]:
        global_state.npcs[npc.npc_id] = npc

    # 4. 创建 SceneState (运行时切片)
    scene = SceneState(
        place_id="alley_01",
        situation="Kael 刚刚完成了一单看似简单的“跑腿”任务，手里提着手提箱。但接头人没有出现，反而是三个带着廉价义体武器的底层帮派混混堵住了胡同口。对方显然是提前收到了风声，专门来抢箱子的。",
        active_npc_ids=["thug_leader", "thug_shooter", "thug_brute"],
        active_item_ids=["briefcase", "noodle_pot", "sewer_grate"],
    )
    scene.story_tags["acid_rain"] = StoryTag(name="酸雨", description="持续伤害，降低能见度")
    scene.story_tags["narrow_alley"] = StoryTag(
        name="狭窄地形", description="限制了大型武器和闪避空间"
    )

    return scene
