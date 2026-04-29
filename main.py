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
from src.preset_data import (
    DEMO_CHARACTER,
    build_demo_scene,
)

load_dotenv()

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    """主入口函数。

    1. 从 .env 加载 DeepSeek API 配置
    2. 初始化日志和 LLM 客户端
    3. 创建 GameLoop 并加载 Demo 场景
    4. 进入交互式输入循环（/quit 退出）
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

    _log.info("正在连接到 DeepSeek...")
    try:
        llm = LLMClient(api_key=api_key, base_url=base_url, model=model, thinking=False)
    except Exception as e:
        _log.error("连接失败: %s", e)
        sys.exit(1)

    game = GameLoop(llm, debug_mode=True)
    game.setup(
        character=DEMO_CHARACTER,
        scene=build_demo_scene(),
    )

    _log.info("")
    _log.info("输入你的行动（输入 /quit 退出，/help 查看命令）")

    while True:
        try:
            player_input = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            _log.info("")
            _log.info("游戏结束。")
            break

        if not player_input:
            continue

        result = game.process_action(player_input)
        if result == "QUIT":
            _log.info("游戏结束。")
            break


if __name__ == "__main__":
    main()
