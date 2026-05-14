"""角色状态模块 —— 追踪玩家角色的状态变化。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from src.formatter import format_statuses
from src.models import GameItem, PowerTag, Status, Theme, WeaknessTag


@dataclass
class CharacterState:
    """玩家角色状态 —— 玩家在游戏世界中的化身与核心状态容器。

    角色由多个 Theme（主题/特质模块）构成，包含了角色的标签和动机。

    关键机制：
        INCAPACITATING_STATUSES: 达到 tier 1 即判定为失去行动能力的状态名集合
    """

    name: str
    themes: list[Theme] = field(default_factory=list)
    statuses: dict[str, Status] = field(default_factory=dict)
    items_visible: dict[str, GameItem] = field(default_factory=dict)
    items_hidden: dict[str, GameItem] = field(default_factory=dict)
    description: str = ""

    INCAPACITATING_STATUSES: ClassVar[set[str]] = {
        "死亡",
        "失去行动能力",
        "昏迷",
        "濒死",
    }

    @property
    def power_tags(self) -> list[PowerTag]:
        return [tag for theme in self.themes for tag in theme.power_tags]

    @property
    def weakness_tags(self) -> list[WeaknessTag]:
        return [tag for theme in self.themes for tag in theme.weakness_tags]

    def is_incapacitated(self) -> bool:
        """判断角色是否已经失去行动能力。

        规则：
            1. 任何状态达到 tier 6 都会导致失去行动能力（如果未满 tier 6 则正常）。
            2. 如果状态名称属于 INCAPACITATING_STATUSES（如"昏迷"、"死亡"），
               且其等级 >= 1，则立刻失去行动能力。

        Returns:
            如果失去行动能力返回 True，否则返回 False。
        """
        for status in self.statuses.values():
            if status.current_tier >= 6:
                return True
            if status.name in self.INCAPACITATING_STATUSES and status.current_tier >= 1:
                return True
        return False

    def build_context_block(self, include_tracks: bool = True) -> str:
        """构建角色状态文本块，供 Agent 注入上下文。

        Args:
            include_tracks: 是否在输出中包含裂痕(Crack)和进度(Attention)轨道

        Returns:
            格式化的文本块，如:
            角色: Kael - 佣兵
              状态:   - 受伤: 等级2 (勾选: [2])
              主题 [前公司安保] 力量: 快速拔枪 | 弱点: 公司通缉 | 进度: 0 | 裂痕: 0
        """
        char_status = format_statuses(self.statuses)
        lines = [
            f"角色: {self.name} - {self.description}",
            f"  状态: {char_status}",
        ]

        theme_texts = []
        for theme in self.themes:
            p_tags = ", ".join(t.name for t in theme.power_tags)
            w_tags = ", ".join(t.name for t in theme.weakness_tags)

            if include_tracks:
                theme_texts.append(
                    f"  主题 [{theme.name}] 力量: {p_tags} | 弱点: {w_tags} | 进度: {theme.attention_track} | 裂痕: {theme.crack_track}"
                )
            else:
                theme_texts.append(f"  主题 [{theme.name}] 力量: {p_tags} | 弱点: {w_tags}")

        if theme_texts:
            lines.append("  特质主题:")
            lines.extend(theme_texts)

        return "\n".join(lines)

    def get_theme(self, theme_name: str) -> Theme | None:
        """根据名称获取 Theme。"""
        for theme in self.themes:
            if theme.name == theme_name:
                return theme
        return None

    def get_theme_by_weakness_tag(self, tag_name: str) -> Theme | None:
        """根据弱点标签名称查找它所属的 Theme。"""
        for theme in self.themes:
            for w_tag in theme.weakness_tags:
                if w_tag.name == tag_name:
                    return theme
        return None

    def add_attention(self, theme_name: str, amount: int = 1) -> None:
        """为指定主题增加进度 (Attention)。"""
        theme = self.get_theme(theme_name)
        if theme:
            theme.attention_track += amount

    def add_crack(self, theme_name: str, amount: int = 1) -> None:
        """为指定主题增加裂痕 (Crack)。"""
        theme = self.get_theme(theme_name)
        if theme:
            theme.crack_track += amount

    def get_evolvable_themes(self) -> list[Theme]:
        """获取可以进化的主题列表 (Attention >= 3)。"""
        return [theme for theme in self.themes if theme.attention_track >= 3]

    def get_broken_themes(self) -> list[Theme]:
        """获取已经破碎的主题列表 (Crack >= 3)。"""
        return [theme for theme in self.themes if theme.crack_track >= 3]

    def replace_theme(self, old_theme_name: str, new_theme: Theme) -> bool:
        """替换一个已经存在的主题。"""
        for i, theme in enumerate(self.themes):
            if theme.name == old_theme_name:
                self.themes[i] = new_theme
                return True
        return False
