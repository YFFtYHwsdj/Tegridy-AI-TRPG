"""Tegridy-AI-TRPG 入口脚本。

加载环境变量，初始化 LLM 客户端和日志系统，
创建 GameLoop 实例并加载 Demo 场景，进入交互式主循环。
"""

import os
import sys

from dotenv import load_dotenv

from src.game_loop import GameLoop
from src.llm_client import LLMClient
from src.logger import get_logger, init_logging
from src.module_loader import ModuleLoader

load_dotenv()

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    """主入口函数。

    1. 从 .env 加载 DeepSeek API 配置
    2. 初始化日志和 LLM 客户端
    3. 创建 GameLoop 并启动完整游戏循环
    """
    api_key = os.getenv("DEEPSEEK_API_KEY")
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")

    if not api_key:
        # init_logging 之前还没有 logger，保留 print
        print("错误: 请在 .env 文件中设置 DEEPSEEK_API_KEY")
        sys.exit(1)

    session_file, llm_file = init_logging(PROJECT_ROOT, debug_mode=True)
    _log = get_logger()
    _log.info("游戏日志: %s", session_file)
    _log.info("LLM调用日志: %s", llm_file)

    loader = ModuleLoader()
    presets = loader.list_available_modules()
    if not presets:
        print("错误: 未找到任何可用模组 (data/modules/)")
        sys.exit(1)

    print("\n==================================================")
    print("  欢迎来到 Tegridy AI TRPG  ")
    print("==================================================")
    print("请选择要加载的演示模组：")
    for i, p in enumerate(presets):
        print(f" {i + 1}. {p['name']}")
        print(f"    - {p['description']}")

    choice_str = input(f"\n请选择 [1-{len(presets)}] (默认: 1): ")
    choice_idx = 0
    if choice_str.strip().isdigit():
        idx = int(choice_str.strip()) - 1
        if 0 <= idx < len(presets):
            choice_idx = idx

    selected_preset_info = presets[choice_idx]
    print(f"\n>> 已选择模组: {selected_preset_info['name']} <<\n")

    selected_preset = loader.load_module(selected_preset_info["id"])

    _log.info("正在连接到 DeepSeek...")
    try:
        llm = LLMClient(api_key=api_key, base_url=base_url, model=model, thinking=False)
    except Exception as e:
        _log.error("连接失败: %s", e)
        sys.exit(1)

    game = GameLoop(llm, debug_mode=True)
    game.state.global_state.worldview = selected_preset.worldview
    for place in selected_preset.global_state_init.places:
        game.state.global_state.places[place.place_id] = place
    for item in selected_preset.global_state_init.items:
        game.state.global_state.items[item.item_id] = item
    for npc in selected_preset.global_state_init.npcs:
        game.state.global_state.npcs[npc.npc_id] = npc

    game.run(
        character=selected_preset.character,
        first_scene=selected_preset.initial_scene,
    )


if __name__ == "__main__":
    main()
