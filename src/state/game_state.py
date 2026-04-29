"""游戏状态管理 —— 顶层状态容器，持有角色、当前场景和跨场景历史。

GameState 是系统运行时的顶层状态容器。场景切换逻辑通过
transition_to() 方法实现，将当前场景压缩并推入 GlobalState，
然后设置新场景。

跨场景叙事历史由 GlobalState 独立管理，GameState 持有其引用。
当前场景的上下文构建委托给 SceneState，全局上下文块由 GlobalState 提供。

设计理念：
    - GameState 专注于运行时协调，不持有深层嵌套历史数据
    - GlobalState 专注于跨场景数据聚合
    - SceneState 专注于单个场景内的数据管理
"""

from __future__ import annotations

import uuid

from src.context import AgentContext
from src.models import Character, SceneSummary
from src.state.global_state import GlobalState
from src.state.scene_state import SceneState


class GameState:
    """游戏运行时状态容器。

    持有当前角色、当前场景、场景切换前的存档和跨场景历史。
    make_context() 将 SceneState 的上下文与 GlobalState 的历史块拼接。
    """

    def __init__(self):
        self.character: Character | None = None
        self.scene: SceneState = SceneState()
        self.global_state = GlobalState()

    def setup(self, character: Character, scene: SceneState):
        """初始化游戏或直接设置场景（不触发归档）。

        仅用于游戏首次启动时设置初始场景。
        场景间切换请使用 transition_to()。

        Args:
            character: 玩家角色
            scene: 初始场景状态
        """
        self.character = character
        self.scene = scene

    def transition_to(self, new_scene: SceneState):
        """执行场景切换。

        执行以下步骤：
        1. 为当前场景生成唯一标识，创建 SceneSummary 存入新场景的前驱列表
        2. 将当前场景的压缩摘要和完整叙事追加到 GlobalState
        3. 将当前场景引用替换为新场景

        Args:
            new_scene: 下一个场景的 SceneState 对象
        """
        old_scene = self.scene
        scene_id = uuid.uuid4().hex[:12]

        # 将当前场景的压缩摘要作为前驱引用存入新场景
        summary = SceneSummary(
            scene_id=scene_id,
            scene_description=old_scene.scene_description,
            compression=old_scene.compression,
            narrative_count=len(old_scene.narrative_history),
        )
        new_scene.previous_scenes = [*old_scene.previous_scenes, summary]

        # 将当前场景的叙事块追加到 GlobalState
        self.global_state.append(
            scene_id=scene_id,
            description=old_scene.scene_description,
            compression=old_scene.compression,
            narratives=old_scene.narrative_history,
        )

        self.scene = new_scene

    def append_narrative(self, entry: str):
        """向当前场景追加叙事条目。

        委托给 SceneState.append_narrative()。

        Args:
            entry: 叙事文本
        """
        self.scene.append_narrative(entry)

    def make_context(self, player_input: str = "") -> AgentContext:
        """构建 Agent 上下文。

        拼接 GlobalState 的历史块和 SceneState 的当前场景上下文。
        调用方通过 ctx.global_block 获取跨场景历史，
        通过 ctx.assets_block / context_block / narrative_block 获取当前信息。

        Args:
            player_input: 玩家当前输入文本

        Returns:
            AgentContext: 包含全局历史和当前场景的完整上下文
        """
        ctx = self.scene.make_context(self.character, player_input)
        ctx.global_block = self.global_state.build_block()
        return ctx
