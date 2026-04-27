import os
import sys
import readline
from dotenv import load_dotenv

from src.llm_client import LLMClient
from src.game_loop import GameLoop
from src.logger import init_log
from src.preset_data import (
    DEMO_SCENE_DESCRIPTION,
    DEMO_CHARACTER,
    DEMO_CHALLENGE,
)

load_dotenv()

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    api_key = os.getenv("DEEPSEEK_API_KEY")
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")

    if not api_key:
        print("错误: 请在 .env 文件中设置 DEEPSEEK_API_KEY")
        sys.exit(1)

    log_file = init_log(PROJECT_ROOT)
    print(f"日志文件: {log_file}")

    print("正在连接到 DeepSeek...")
    try:
        llm = LLMClient(api_key=api_key, base_url=base_url, model=model)
    except Exception as e:
        print(f"连接失败: {e}")
        sys.exit(1)

    game = GameLoop(llm)
    game.setup(
        character=DEMO_CHARACTER,
        challenge=DEMO_CHALLENGE,
        scene_desc=DEMO_SCENE_DESCRIPTION,
    )

    print("\n输入你的行动（输入 quit 退出）")

    while True:
        try:
            player_input = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n游戏结束。")
            break

        if not player_input:
            continue

        result = game.process_action(player_input)
        if result == "QUIT":
            print("游戏结束。")
            break


if __name__ == "__main__":
    main()
