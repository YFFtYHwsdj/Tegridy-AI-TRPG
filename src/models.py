"""数据模型定义 —— 系统中所有核心数据类。

本模块定义了 PBTA 规则系统中使用的全部数据结构。
所有模型使用 Python dataclass 实现，保持简洁和类型安全。

核心概念：
    PowerTag（力量标签）: 角色/挑战/物品的优势特征，命中行动时提供 +1 力量值
    WeaknessTag（弱点标签）: 角色/物品的劣势特征，命中行动时提供 -1 力量值
    Status（状态）: PBTA tick 系统的水位标记，tier 1-6 递进
    StoryTag（叙事标签）: 临时的情境性标记，不参与数学计算
    AgentNote（分析便签）: Agent 间的自然语言推理传递载体
"""

from dataclasses import dataclass, field


@dataclass
class PowerTag:
    """力量标签 —— 角色、挑战或物品的优势特征。

    命中行动时提供 +1 力量值。可以被燃烧（burn）以换取额外效果。
    与 WeaknessTag 在类型层面彻底分离，杜绝编译期混淆。

    角色通过 power_tags 字段持有，挑战通过 base_tags 字段持有，
    物品通过 tags 字段持有。
    """

    name: str
    description: str = ""


@dataclass
class WeaknessTag:
    """弱点标签 —— 角色或物品的劣势特征。

    命中行动时提供 -1 力量值。不可燃烧。
    与 PowerTag 在类型层面彻底分离，杜绝编译期混淆。

    角色通过 weakness_tags 字段持有，物品通过 weakness_tags 字段持有。
    """

    name: str
    description: str = ""


@dataclass
class Status:
    """PBTA 状态 —— tick 水位系统的核心载体。

    每个状态有 6 个 tier 等级槽位（1-6）。施加状态时在对应 tier "打勾"。
    如果目标 tier 已被占用，自动上溢到下一个空位。
    current_tier 取所有已勾选槽位的最大值。

    关键字段：
        ticked_boxes: 已勾选的 tier 编号集合，例如 {1, 3} 表示 tier 1 和 3 被标记
    """

    name: str
    current_tier: int = 0
    ticked_boxes: set[int] = field(default_factory=set)


@dataclass
class StoryTag:
    """叙事标签 —— 临时的情境性标记。

    与 PowerTag/WeaknessTag（力量/弱点标签）不同，StoryTag 不参与力量值计算。
    它们记录叙事中的临时状态，例如：
        - "被警方通缉"
        - "拥有博物馆地图"
        - "赢得了黑帮老大的信任"

    可配置为一次性标签（is_single_use=True），使用后自动销毁。
    is_consumable 标记表示该标签为可消耗品（如道具）。
    """

    name: str
    description: str = ""
    is_single_use: bool = False
    is_consumable: bool = False


@dataclass
class GameItem:
    """游戏物品 —— 可被角色携带或使用的道具。

    物品可以有力量标签（作为使用时的加成来源）和弱点标签（副作用）。
    location 字段追踪物品的所在位置。
    """

    item_id: str = ""
    name: str = ""
    description: str = ""
    location: str = ""
    tags: list[PowerTag] = field(default_factory=list)
    weakness_tags: list[WeaknessTag] = field(default_factory=list)

    def __post_init__(self):
        if not self.item_id:
            self.item_id = self.name


@dataclass
class Clue:
    """线索 —— 叙事推进的信息碎片。

    线索是调查型场景的核心元素。NPC 可以持有已知线索，
    角色通过互动获取线索来推动剧情。
    """

    clue_id: str = ""
    name: str = ""
    description: str = ""

    def __post_init__(self):
        if not self.clue_id:
            self.clue_id = self.name


@dataclass
class NPC:
    """非玩家角色 —— 故事中的配角。

    NPC 可持有标签（用于交互判定）、状态、线索和物品。
    物品分为可见（items_visible）和隐藏（items_hidden）两类，
    后者只在特定条件下被玩家发现。
    """

    npc_id: str = ""
    name: str = ""
    description: str = ""
    tags: list[PowerTag] = field(default_factory=list)
    statuses: dict[str, Status] = field(default_factory=dict)
    known_clue_ids: list[str] = field(default_factory=list)
    known_item_ids: list[str] = field(default_factory=list)
    items_visible: dict[str, "GameItem"] = field(default_factory=dict)
    items_hidden: dict[str, "GameItem"] = field(default_factory=dict)

    def __post_init__(self):
        if not self.npc_id:
            self.npc_id = self.name


@dataclass
class Theme:
    """主题 / 特质模块 —— 构成角色的基本单位。

    每个 Theme 代表角色的一项核心特征（如背景、职业、专长或装备）。
    它包含了相关的正面特质（力量标签）和负面特征（弱点标签）。
    同时，根据《Otherscape》规则，每个 Theme 还带有两条发展轨道：
    Attention (进度) 和 Crack (裂痕)。
    """

    name: str
    theme_type: str
    concept: str
    motivation: str
    power_tags: list[PowerTag] = field(default_factory=list)
    weakness_tags: list[WeaknessTag] = field(default_factory=list)
    attention_track: int = 0
    crack_track: int = 0


@dataclass
class RollResult:
    """掷骰结果 —— 单次行动投骰的完整数据。

    包含力量值、两颗骰子的面值、总和以及 PBTA 标准结果标签。
    outcome 取值：full_success / partial_success / failure
    """

    power: int
    dice: tuple[int, int]
    total: int
    outcome: str

    def __post_init__(self):
        if self.outcome not in ("full_success", "partial_success", "failure"):
            raise ValueError(
                f"outcome must be full_success/partial_success/failure, got '{self.outcome}'"
            )


@dataclass
class EffectEntry:
    """效果条目 —— 单个因果效果的结构化描述。

    由效果推演 Agent 生成，包含效果类型、等级、目标、
    显示标签和推理过程（reasoning）。效果推演和后果 Agent 之间
    通过 EffectEntry 列表传递因果链信息。
    """

    effect_type: str
    tier: int
    target: str
    label: str
    reasoning: str = ""


@dataclass
class ConsequenceEntry:
    """后果条目 —— 一次行动产生的完整后果。

    包含具体化的威胁（threat_manifested）、关联的效果列表
    和叙事描述。由后果 Agent 生成，传递给叙述者 Agent
    用于生成最终叙事文本。
    """

    threat_manifested: str
    effects: list[EffectEntry] = field(default_factory=list)
    narrative_description: str = ""


@dataclass
class AgentNote:
    """Agent 分析便签 —— Agent 间的推理传递载体。

    遵循项目设计原则：Agent 间传递"分析便签"而非"表单"。
    reasoning 字段承载自然语言推理过程，
    structured 字段承载 JSON 结构化数据（仅用于真正需要机器读取的场合）。
    """

    reasoning: str
    structured: dict
