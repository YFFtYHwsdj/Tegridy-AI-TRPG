"""场景路由与导演。"""

from __future__ import annotations

from src.agents.base import BaseAgent
from src.agents.prompts.world_generators import SCENE_ROUTER_PROMPT
from src.context import MessageBuilder
from src.models import AgentNote
from src.state.global_state import GlobalState


class SceneRouterAgent(BaseAgent):
    """场景路由与导演。"""

    system_prompt = SCENE_ROUTER_PROMPT
    agent_name = "场景路由Agent"

    def execute(self, player_intent: str, global_state: GlobalState) -> AgentNote:
        # 为了给 Router 最全面的视野，我们提取全部的 locations, npcs, items 的摘要
        # 当数据量大时，可以限制为与近期剧情相关的全量子集。目前全量输出。
        lines = ["=== 全局世界资产表 ==="]
        lines.append("【地点】")
        for eid, loc in global_state.places.items():
            lines.append(f"- ID: {eid} | 名称: {loc.name} | 描述: {loc.description}")
        lines.append("\n【NPC】")
        for eid, npc in global_state.npcs.items():
            lines.append(f"- ID: {eid} | 名称: {npc.name} | 描述: {npc.description}")
        lines.append("\n【物品】")
        for eid, it in global_state.items.items():
            lines.append(f"- ID: {eid} | 名称: {it.name} | 描述: {it.description}")

        world_block = "\n".join(lines)

        builder = MessageBuilder()
        builder.add_block("全局世界资产表", world_block, wrap_title=True)
        builder.add_block("玩家意图/过渡提示", player_intent, wrap_title=True)

        return self._call_llm(builder.build())
