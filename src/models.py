"""数据模型定义 —— 系统中所有核心数据类。

本模块定义了 PBTA 规则系统中使用的全部数据结构。
所有模型使用 Python dataclass 实现，保持简洁和类型安全。

核心概念：
    Tag（标签）: 角色/挑战的力量来源或弱点，参与力量值计算
    Status（状态）: PBTA tick 系统的水位标记，tier 1-6 递进
    StoryTag（叙事标签）: 临时的情境性标记，不参与数学计算
    Limit（极限）: 挑战的关键突破条件，与关联状态的控制阈值挂钩
    Challenge（挑战）: NPC、障碍物、环境危险等叙事阻力的抽象
    AgentNote（分析便签）: Agent 间的自然语言推理传递载体
"""

from dataclasses import dataclass, field
from typing import ClassVar


@dataclass
class Tag:
    """PBTA 标签 —— 角色或挑战的核心特征标识。

    标签分为两种类型：
        power（力量）: 行动时可利用的优势，增加力量值
        weakness（弱点）: 行动时的劣势，减少力量值

    注意：Tag 与 StoryTag 不同。Tag 参与力量值计算，
    StoryTag 是纯叙事标记，由 Agent 在效果推演中引用。
    """

    name: str
    tag_type: str
    description: str = ""

    def __post_init__(self):
        if self.tag_type not in ("power", "weakness"):
            raise ValueError(f"tag_type must be 'power' or 'weakness', got '{self.tag_type}'")


@dataclass
class Status:
    """PBTA 状态 —— tick 水位系统的核心载体。

    每个状态有 6 个 tier 等级槽位（1-6）。施加状态时在对应 tier "打勾"。
    如果目标 tier 已被占用，自动上溢到下一个空位。
    current_tier 取所有已勾选槽位的最大值。

    关键字段：
        ticked_boxes: 已勾选的 tier 编号集合，例如 {1, 3} 表示 tier 1 和 3 被标记
        limit_category: 关联的极限类别名，用于 Challenge 的状态追踪
    """

    name: str
    current_tier: int = 0
    ticked_boxes: set[int] = field(default_factory=set)
    limit_category: str = ""


@dataclass
class StoryTag:
    """叙事标签 —— 临时的情境性标记。

    与 Tag（力量/弱点标签）不同，StoryTag 不参与力量值计算。
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
class Limit:
    """极限条件 —— 挑战的关键突破阈值。

    每个 Limit 关联一个 limit_category，与状态的 limit_category 字段匹配。
    当匹配的状态 current_tier 达到 max_tier 时，极限被触发。
    is_progress 标记是否以进度条方式追踪（如倒计时、积累型目标）。
    """

    name: str
    max_tier: int
    is_progress: bool = False

    def __post_init__(self):
        if self.max_tier < 1 or self.max_tier > 6:
            raise ValueError(f"max_tier must be between 1 and 6, got {self.max_tier}")


@dataclass
class Challenge:
    """挑战 —— 叙事阻力的抽象表示。

    Challenge 可以代表 NPC、障碍物、环境危险、谜题等任何
    玩家需要通过行动克服的叙事元素。

    关键机制：
        - limits: 突破条件列表，当关联状态达到阈值时触发
        - broken_limits: 已被突破的极限集合
        - transformation: 极限被完全突破后的形态变化描述
    """

    name: str
    description: str
    limits: list[Limit] = field(default_factory=list)
    base_tags: list[Tag] = field(default_factory=list)
    statuses: dict[str, Status] = field(default_factory=dict)
    story_tags: dict[str, StoryTag] = field(default_factory=dict)
    notes: str = ""
    broken_limits: set[str] = field(default_factory=set)
    transformation: str = ""

    def get_matching_statuses(self, limit_name: str) -> list[Status]:
        """获取与指定极限名匹配的所有状态。

        匹配规则：状态的 limit_category 字段包含 limit_name。
        例如 limit_name="时间" 会匹配 limit_category="时间压力" 的状态。

        Args:
            limit_name: 极限名称

        Returns:
            匹配的 Status 列表
        """
        results = []
        for status in self.statuses.values():
            if status.limit_category and status.limit_category in limit_name:
                results.append(status)
        return results

    def get_limit_progress(self) -> dict[str, int]:
        """获取每个极限的当前进度。

        对每个 Limit，取其关联状态中的最高 current_tier 作为进度值。

        Returns:
            {limit_name: progress_tier} 的映射字典
        """
        return {
            limit.name: max(
                (s.current_tier for s in self.get_matching_statuses(limit.name)),
                default=0,
            )
            for limit in self.limits
        }

    def check_limits(self) -> list[Limit]:
        """检查是否有极限条件被触发。

        遍历所有极限，检查关联状态是否达到 max_tier 阈值。
        已被标记为 broken 的极限不再重复触发。

        Returns:
            被触发的 Limit 对象列表
        """
        triggered = []
        for limit in self.limits:
            if limit.name in self.broken_limits:
                continue
            matching = self.get_matching_statuses(limit.name)
            for s in matching:
                if s.current_tier >= limit.max_tier:
                    triggered.append(limit)
                    break
        return triggered

    def mark_limits_broken(self, limit_names: list[str]):
        """将指定极限标记为已突破。

        Args:
            limit_names: 要标记的极限名称列表
        """
        for name in limit_names:
            self.broken_limits.add(name)


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
    tags: list[Tag] = field(default_factory=list)
    weakness: Tag | None = None

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
    tags: list[Tag] = field(default_factory=list)
    statuses: dict[str, Status] = field(default_factory=dict)
    known_clue_ids: list[str] = field(default_factory=list)
    known_item_ids: list[str] = field(default_factory=list)
    items_visible: dict[str, "GameItem"] = field(default_factory=dict)
    items_hidden: dict[str, "GameItem"] = field(default_factory=dict)

    def __post_init__(self):
        if not self.npc_id:
            self.npc_id = self.name


@dataclass
class Character:
    """玩家角色 —— 玩家在游戏世界中的化身。

    角色拥有力量标签和弱点标签（用于力量值计算）、
    状态（track 系统）、叙事标签（临时标记）和物品。

    关键机制：
        burned_tags: 已燃尽的标签集合，标签燃烧后不再参与计算
        INCAPACITATING_STATUSES: 达到 tier 1 即判定为失去行动能力的状态名集合
    """

    name: str
    power_tags: list[Tag] = field(default_factory=list)
    weakness_tags: list[Tag] = field(default_factory=list)
    statuses: dict[str, Status] = field(default_factory=dict)
    story_tags: dict[str, StoryTag] = field(default_factory=dict)
    burned_tags: set[str] = field(default_factory=set)
    items_visible: dict[str, "GameItem"] = field(default_factory=dict)
    items_hidden: dict[str, "GameItem"] = field(default_factory=dict)
    description: str = ""

    INCAPACITATING_STATUSES: ClassVar[set[str]] = {
        "死亡",
        "失去行动能力",
        "被打晕",
        "被制服",
        "被束缚",
        "dead",
        "unconscious",
        "incapacitated",
    }

    def is_incapacitated(self) -> bool:
        """判断角色是否失去行动能力。

        两种判定条件（满足其一即判定为 incapacitated）：
        1. 任意状态达到 tier 6（极度严重）
        2. 特定"失去行动能力"类状态达到 tier 1 及以上

        Returns:
            True 表示角色无法行动
        """
        for status in self.statuses.values():
            if status.current_tier >= 6:
                return True
            if status.name in self.INCAPACITATING_STATUSES and status.current_tier >= 1:
                return True
        return False


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
