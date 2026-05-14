"""领域驱动的管理器模块。

包含用于管理游戏状态实体（物品、线索、标签、角色、NPC）的各领域管理器。
取代原有的 EffectApplicator，实现高内聚低耦合的状态操作。
"""

from .character_manager import CharacterManager
from .clue_manager import ClueManager
from .item_manager import ItemManager
from .npc_manager import NPCManager
from .story_tag_manager import StoryTagManager

__all__ = [
    "CharacterManager",
    "ClueManager",
    "ItemManager",
    "NPCManager",
    "StoryTagManager",
]
