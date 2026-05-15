"""预置数据 —— Demo 场景的角色、挑战和场景构建。

提供多套演示模组数据：
    - ALLEY_PRESET: 赛博朋克风格死胡同（Kael）
    - CYBER_SHRINE_PRESET: 赛博龛寺虚拟网域（Rin）
"""

from collections.abc import Callable
from dataclasses import dataclass

from src.models import NPC, GameItem, Place, PowerTag, StoryTag, Theme, WeaknessTag
from src.state.character_state import CharacterState
from src.state.global_state import GlobalState
from src.state.scene_state import SceneState


@dataclass
class DemoPreset:
    id: str
    name: str
    description: str
    worldview: str
    character: CharacterState
    build_scene: Callable[[GlobalState], SceneState]


# -----------------------------------------------------------------------------
# ALLEY PRESET
# -----------------------------------------------------------------------------

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


def build_alley_scene(global_state: GlobalState) -> SceneState:
    """构建赛博死胡同场景并注册全局实体。"""
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

    # 4. 创建 SceneState
    scene = SceneState(
        place_id="alley_01",
        situation="Kael 刚刚完成了一单看似简单的“跑腿”任务，手里提着手提箱。但接头人没有出现，反而是三个带着廉价义体武器的底层帮派混混堵住了胡同口。对方显然是提前收到了风声，专门来抢箱子的。",
        active_npc_ids=["thug_leader", "thug_shooter", "thug_brute"],
        active_item_ids=["briefcase", "noodle_pot", "sewer_grate"],
    )
    scene.story_tags["酸雨"] = StoryTag(name="酸雨", description="持续伤害，降低能见度")
    scene.story_tags["狭窄地形"] = StoryTag(name="狭窄地形", description="限制了大型武器和闪避空间")

    return scene


ALLEY_PRESET = DemoPreset(
    id="alley",
    name="赛博死胡同 (Cyberpunk Alley)",
    description="扮演前公司干员Kael，在阴暗的酸雨小巷里面对底层帮派的抢劫。",
    worldview=DEMO_WORLDVIEW,
    character=DEMO_CHARACTER,
    build_scene=build_alley_scene,
)

# -----------------------------------------------------------------------------
# CYBER SHRINE PRESET
# -----------------------------------------------------------------------------

SHRINE_WORLDVIEW = "这是一个被骇客、企业与神话生物共治的世界。赛博空间不再仅仅是数据的集合，而是神明与妖怪栖居的虚拟维度。在这个被称为“异景”的网络世界中，黑客通过特制的挽具技术，以心智化身与防火墙和恶意程序进行实质性的战斗。"

RIN_CHARACTER = CharacterState(
    name="Rin",
    description="第7区特约网络干员。通过特殊的赛博挽具技术接入赛博空间，专门处理虚拟现实中的危机与异常网域。",
    themes=[
        Theme(
            name="网络黑客",
            theme_type="背景/职业",
            concept="精通赛博空间渗透与数据解析",
            motivation="揭露隐藏在代码中的真相",
            power_tags=[
                PowerTag(name="代码解析", description="能够看穿虚拟伪装，阅读并解密底层代码流"),
                PowerTag(
                    name="赛博挽具", description="使用特殊技术连接赛博空间，化身更为敏捷和强大"
                ),
                PowerTag(name="虚拟伪装", description="能暂时修改自己的身份标识以欺骗基础安保程序"),
            ],
            weakness_tags=[
                WeaknessTag(
                    name="肉体脆弱",
                    description="物理肉体正躺在安全屋中，一旦在虚拟世界遭受致命伤害，可能导致脑部神经反馈损伤",
                ),
            ],
        ),
        Theme(
            name="第7区特派员",
            theme_type="身份/特权",
            concept="为神秘的第7区工作，拥有某些隐秘资源",
            motivation="完成指派的任务",
            power_tags=[
                PowerTag(
                    name="后门算法", description="携带了第七区研发的渗透算法，能够强制开启连接路径"
                ),
                PowerTag(name="隐秘频段", description="能通过加密频段呼叫外部的战术支持或信息核查"),
            ],
            weakness_tags=[
                WeaknessTag(
                    name="服从命令",
                    description="必须优先完成第七区指派的任务指标，违背命令将切断资源支持",
                ),
            ],
        ),
        Theme(
            name="神经接口改装",
            theme_type="装备/义体",
            concept="大脑后庭植入了军用级神经直连接口",
            motivation="追求更快的处理速度",
            power_tags=[
                PowerTag(
                    name="超频计算",
                    description="短时间内极速提升思维速度，甚至能放慢虚拟现实中的相对时间",
                ),
                PowerTag(name="电子直觉", description="凭直觉感知到附近的数据流向和隐藏的逻辑陷阱"),
            ],
            weakness_tags=[
                WeaknessTag(
                    name="过载发热",
                    description="超频过久会导致接口物理发热，引发剧烈偏头痛并降低灵敏度",
                ),
            ],
        ),
    ],
)


def build_shrine_scene(global_state: GlobalState) -> SceneState:
    """构建赛博龛寺（初始池塘）场景并注册全局实体。"""
    # 1. 注册 Place
    pond = Place(
        place_id="shrine_pond_01",
        name="赛博龛寺 - 池塘端口",
        description="网域的外围访问点。由闪耀的代码与数据之线组成的瀑布汇聚成池，水面上漂浮着虚拟的莲花。",
    )
    global_state.places[pond.place_id] = pond

    # 2. 注册 Items
    data_waterfall = GameItem(
        item_id="data_waterfall",
        name="数据瀑布",
        description="从赛博空间汇入池塘的巨大下行链路。它代表着外界进入这里的数据流。",
        location="池塘边缘",
        tags=[PowerTag("席卷数据流", "水流湍急，如果不慎卷入，可能会被直接冲刷出网域。")],
    )
    firewall_gate = GameItem(
        item_id="firewall_gate",
        name="门界塔入口",
        description="通往龛寺庭院内部的主要防火墙。由数道变幻莫测的力场屏障构成，时间流在表面流转。",
        location="瀑布后方石阶上",
        tags=[PowerTag("时间流屏障", "唯有掌握正确规律或携带特定授权才能安全穿透。")],
        notes="隐藏线索：屏障看似毫无规律，但如果用特定节奏（如音乐或诗歌）可能可以引起其内在逻辑的共鸣。",
    )
    for it in [data_waterfall, firewall_gate]:
        global_state.items[it.item_id] = it

    # 3. 注册 NPCs
    kappa = NPC(
        npc_id="kappa_guardian",
        name="河童守护程序",
        description="一种形似丑陋河童的入侵对策应用程序。背着龟壳的暗绿色两栖生物，四处巡视搜寻入侵者。",
        tags=[
            PowerTag("水下伏击", "能够潜入数据水流中隐蔽身形并发动突袭。"),
            PowerTag("强制断开", "它的攻击能够直接撕裂入侵者的化身代码，造成断线伤害。"),
            PowerTag("保护甲壳", "背部的虚拟龟壳拥有极高的抗打击防御权限。"),
        ],
        notes="隐藏线索：如果它失去与池塘水流（数据流）的接触，运行速度就会大幅度减慢（慢速运算）。",
    )
    kirinaga = NPC(
        npc_id="hacker_kirinaga",
        name="桐永阳菜",
        description="归来的相马氏族网络团队队长。霓虹发色的朋克造型，周身环绕着漂浮的加密卷轴，手持长柄薙刀。",
        tags=[
            PowerTag("致命薙刀", "刀刃带着分形图案代码，能够斩断化身并造成持续流血故障。"),
            PowerTag("卷轴防火墙", "漂浮的卷轴能自动拦截即将到来的攻击或异常状态。"),
            PowerTag("专业黑客", "极其严谨细致，几乎没有逻辑漏洞可以利用。"),
        ],
    )
    for npc in [kappa, kirinaga]:
        global_state.npcs[npc.npc_id] = npc

    # 4. 创建 SceneState
    scene = SceneState(
        place_id="shrine_pond_01",
        situation="Rin 的化身刚刚通过第七区的后门算法降落在闪耀着代码光芒的池塘边缘。不远处是高耸的门界塔防火墙。正当 Rin 准备寻找进入途径时，水面突然泛起一阵不祥的漩涡，一个背着龟壳、双眼闪烁红光的河童守护程序从数据流中跃出，准备发起攻击！",
        active_npc_ids=["kappa_guardian"],
        active_item_ids=["data_waterfall", "firewall_gate"],
    )
    scene.story_tags["数据湍流"] = StoryTag(
        name="数据湍流", description="池塘环境中的数据流非常不稳定，容易影响精细操作。"
    )

    return scene


CYBER_SHRINE_PRESET = DemoPreset(
    id="cyber_shrine",
    name="赛博龛寺 (Cyber Shrine)",
    description="扮演第7区特约网络干员Rin，潜入被“大虾蟆”恐怖组织控制的神话虚拟网域。",
    worldview=SHRINE_WORLDVIEW,
    character=RIN_CHARACTER,
    build_scene=build_shrine_scene,
)

# -----------------------------------------------------------------------------
# EXPORT
# -----------------------------------------------------------------------------

AVAILABLE_PRESETS: dict[str, DemoPreset] = {
    ALLEY_PRESET.id: ALLEY_PRESET,
    CYBER_SHRINE_PRESET.id: CYBER_SHRINE_PRESET,
}

# 保留默认导出用于向后兼容
DEMO_CHARACTER = ALLEY_PRESET.character
DEMO_WORLDVIEW = ALLEY_PRESET.worldview
build_demo_scene = ALLEY_PRESET.build_scene
