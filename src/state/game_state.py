"""游戏状态管理 —— 单层聚合模型，持有角色和当前场景的引用。

GameState 是系统运行时的顶层状态容器。它不直接管理嵌套数据，
而是持有角色、场景和场景历史的引用。场景切换时，当前场景被推入
scene_history 堆栈，新场景接管 active 位置。

设计理念：
    - 状态管理采用扁平结构，避免深层嵌套
    - 场景作为上下文单元切换，scene_history 支持回溯
"""

from __future__ import annotations

from src.context import AgentContext
from src.models import Character
from src.state.scene_state import SceneState


class GameState:
    """游戏运行时状态容器。

    持有当前角色、当前场景和场景历史。
    make_context() 是 Agent 上下文的工厂方法，委托给 SceneState。
    """

    def __init__(self):
        self.character: Character | None = None
        self.scene: SceneState = SceneState()
        self.scene_history: list[SceneState] = []

    def setup(self, character: Character, scene: SceneState):
        """初始化或切换场景。

        如果当前场景已有内容（描述或活跃挑战），
        先将其推入 scene_history 再设置新场景。

        Args:
            character: 玩家角色
            scene: 新场景状态
        """
        self.character = character
        if self.scene.scene_description or self.scene.active_challenges:
            self.scene_history.append(self.scene)
        self.scene = scene

    def append_narrative(self, entry: str):
        """向当前场景追加叙事条目。

        委托给 SceneState.append_narrative()，
        场景内部管理叙事历史的长度限制。

        Args:
            entry: 叙事文本
        """
        self.scene.append_narrative(entry)

    def make_context(self, player_input: str = "") -> AgentContext:
        """构建 Agent 上下文。

        工厂方法，委托给 SceneState.make_context()。

        Args:
            player_input: 玩家当前输入文本

        Returns:
            AgentContext: 包含场景、角色、历史叙事的完整上下文
        """
        return self.scene.make_context(self.character, player_input)
