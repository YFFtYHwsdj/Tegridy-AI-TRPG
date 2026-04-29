"""场景压缩 Agent —— 将完整叙事历史压缩为结构化摘要。

CompressorAgent 在场景结束时被调用（SceneDirector 判定结束后）。
它接收当前 SceneState 的完整信息，产出结构化压缩摘要，
存入 scene.compression 字段。

压缩摘要随后被 GlobalState 和 SceneSummary 使用，
在后续场景中作为"前情提要"注入 Agent 上下文。
"""

from __future__ import annotations

from src.agents.base import BaseAgent
from src.agents.prompts import COMPRESSOR_PROMPT
from src.models import AgentNote
from src.state.scene_state import SceneState


class CompressorAgent(BaseAgent):
    """场景压缩器 —— 将完整叙事压缩为结构化摘要。

    execute() 接收 SceneState 对象，抽取场景描述、叙事历史和
    挑战/NPC 概览信息，发送给 LLM 生成压缩摘要。
    """

    system_prompt = COMPRESSOR_PROMPT
    agent_name = "场景压缩Agent"

    def execute(self, scene: SceneState) -> AgentNote:
        """压缩当前场景的叙事历史。

        Args:
            scene: 需要压缩的 SceneState 对象

        Returns:
            AgentNote，structured 包含：
                - scene_summary (str): 场景摘要
                - key_events (list[str]): 关键事件列表
                - character_changes (str): 角色变化描述
                - unresolved_threads (str): 未解决的线索
        """
        narrative_text = scene._build_narrative_block()

        # 简洁的场景资产概览——不需要完整 assets block，只需要名称列表
        npc_names = [npc.name for npc in scene.npcs.values()]
        challenge_names = list(scene.active_challenges.keys())

        user_msg = f"""场景描述:
{scene.scene_description}

场景中的NPC: {", ".join(npc_names) if npc_names else "（无）"}
场景中的挑战: {", ".join(challenge_names) if challenge_names else "（无）"}

完整叙事历史:
{narrative_text}

---
请将以上场景压缩为结构化摘要。"""
        return self._call_llm(user_msg)
