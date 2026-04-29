"""物品管理与叙事生效 —— 游戏状态变更的执行引擎。

本模块从 MovePipeline 中提取出来的"非流水线编排"职责，
负责执行叙述者 Agent 产出的揭示决策和物品转移指令。
这些操作直接修改 GameState（线索/物品的 hidden ↔ visible 切换、物品跨位置移动），
与 Agent 调用顺序无关，属于独立的游戏状态变更层。

设计原则：
    - 所有修改 GameState 的方法显式接收 state 参数，避免隐式耦合
    - 物品位置编码（"scene"、"character"、"npc.<id>"）在本模块内统一解析
    - emergent 物品的 LLM 创建逻辑封装在 create_emergent_item 中
"""

from __future__ import annotations

from src.llm_client import LLMClient
from src.logger import log_system


class ItemManager:
    """游戏状态中的物品管理与叙事生效引擎。

    负责：
        - 揭示决策执行（线索/物品从 hidden 变为 visible）
        - 物品转移（场景 ↔ 角色 ↔ NPC 之间的物品