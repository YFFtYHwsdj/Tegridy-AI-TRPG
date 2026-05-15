"""场景过渡流水线。

负责在场景结束时，统筹压缩、世界演化、裂痕评估、路由和资产生成。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.agents import CompressorAgent, CrackEvaluatorAgent, SceneRouterAgent
from src.agents.challenge_generator import ChallengeGeneratorAgent
from src.agents.item_generator import ItemGeneratorAgent
from src.agents.npc_generator import NPCGeneratorAgent
from src.agents.place_generator import PlaceGeneratorAgent
from src.agents.world_updater import EdgeMergeAgent, WorldAnalyzerAgent
from src.llm_client import LLMClient
from src.logger import log_system
from src.pipeline.world_update_pipeline import apply_world_updates
from src.state.game_state import GameState
from src.state.scene_state import SceneState

if TYPE_CHECKING:
    pass


class SceneTransitionPipeline:
    """场景过渡控制器。"""

    def __init__(self, llm: LLMClient, state: GameState):
        self.llm = llm
        self.state = state

        # 初始化所有相关的 Agent
        self.compressor = CompressorAgent(llm)
        self.world_analyzer = WorldAnalyzerAgent(llm)
        self.edge_merge = EdgeMergeAgent(llm)
        self.crack_evaluator = CrackEvaluatorAgent(llm)
        self.scene_router = SceneRouterAgent(llm)
        self.place_gen = PlaceGeneratorAgent(llm)
        self.npc_gen = NPCGeneratorAgent(llm)
        self.item_gen = ItemGeneratorAgent(llm)
        self.challenge_gen = ChallengeGeneratorAgent(llm)

    def execute(self, transition_hint: str):
        """执行场景过渡流水线。

        1. 压缩当前场景。
        2. 世界推演与图边融合。
        3. 裂痕评估。
        4. 路由：决定去向。
        5. 生成：补全缺失资产。
        6. 切换场景状态。
        """
        old_scene = self.state.scene

        # 1. 压缩当前场景
        compressor_note = self.compressor.execute(old_scene, self.state.global_state)
        compression = compressor_note.structured.get("scene_summary", "")
        old_scene.compression = compression

        # 2. 世界推演与图边融合
        apply_world_updates(
            self.world_analyzer, self.edge_merge, old_scene, self.state.global_state
        )

        # 3. 裂痕评估 (仅在有角色时)
        if self.state.character:
            ctx = self.state.make_context()
            crack_note = self.crack_evaluator.execute(compression, ctx)
            cracked_themes = crack_note.structured.get("cracked_themes", [])
            for c_theme in cracked_themes:
                t_name = c_theme.get("theme_name")
                reason = c_theme.get("reason", "")
                if t_name and self.state.character.get_theme(t_name):
                    self.state.character.add_crack(t_name, 1)
                    log_system(
                        f"场景裂痕结算: 主题 [{t_name}] Crack +1 (原因: {reason})", level="warning"
                    )

        # 4. 路由：决定下个场景位置与演员
        router_note = self.scene_router.execute(transition_hint, self.state.global_state)
        r_data = router_note.structured

        # 5. 生成缺失资产
        loc_data = r_data.get("target_place", {})
        place_id = loc_data.get("id")
        if loc_data.get("is_new") and place_id:
            loc = self.place_gen.execute(loc_data.get("generation_prompt", ""), place_id)
            self.state.global_state.places[place_id] = loc

        active_npcs = []
        for npc_req in r_data.get("target_npcs", []):
            nid = npc_req.get("id")
            if not nid:
                continue
            if npc_req.get("is_new"):
                npc = self.npc_gen.execute(npc_req.get("generation_prompt", ""), nid)
                self.state.global_state.npcs[nid] = npc
            active_npcs.append(nid)

        active_items = []
        for item_req in r_data.get("target_items", []):
            iid = item_req.get("id")
            if not iid:
                continue
            if item_req.get("is_new"):
                it = self.item_gen.execute(item_req.get("generation_prompt", ""), iid)
                self.state.global_state.items[iid] = it
            active_items.append(iid)

        active_challenges = []
        for c_req in r_data.get("target_challenges", []):
            cid = c_req.get("id")
            if not cid:
                continue
            if c_req.get("is_new"):
                c_obj = self.challenge_gen.execute(c_req.get("generation_prompt", ""), cid)
                self.state.global_state.challenges[cid] = c_obj
            active_challenges.append(cid)

        # 6. 构建并切换 SceneState
        new_scene = SceneState(
            place_id=place_id,
            situation=r_data.get("situation_prompt", "无特定状况"),
            active_npc_ids=active_npcs,
            active_item_ids=active_items,
            active_challenge_ids=active_challenges,
        )

        self.state.transition_to(new_scene)
