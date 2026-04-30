"""E2E 自动化测试命令行入口。

使用方式：
    python -m e2e_test                    # 默认 150 轮
    python -m e2e_test --max-rounds 10    # 跑 10 轮
    python -m e2e_test --max-scenes 2     # 最多 2 次场景切换
    python -m e2e_test --no-debug         # 关闭调试输出

加载 .env 环境变量，初始化 LLM 和日志系统，
使用 preset_data 的 Demo 场景数据运行自动化测试。
"""

import argparse
import json
import os
import sys

from dotenv import load_dotenv

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from e2e_test.auto_runner import AutoRunner  # noqa: E402
from src.llm_client import LLMClient  # noqa: E402
from src.logger import get_logger, init_logging  # noqa: E402
from src.preset_data import DEMO_CHARACTER, build_demo_scene  # noqa: E402


def parse_args() -> argparse.Namespace:
    """解析命令行参数。

    Returns:
        解析后的参数命名空间
    """
    parser = argparse.ArgumentParser(
        description="AI 玩家自动化 E2E 测试",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--max-rounds",
        type=int,
        default=150,
        help="最大回合数，即玩家输入次数 (默认: 150)",
    )
    parser.add_argument(
        "--max-scenes",
        type=int,
        default=15,
        help="最大场景切换次数 (默认: 15)",
    )
    parser.add_argument(
        "--player-history",
        type=int,
        default=50,
        help="AI 玩家叙事历史窗口大小 (默认: 50)",
    )
    parser.add_argument(
        "--no-debug",
        action="store_true",
        help="关闭调试输出（仅显示叙事）",
    )
    return parser.parse_args()


def main():
    """E2E 自动化测试主入口。

    1. 加载 .env 环境变量
    2. 初始化日志和 LLM 客户端
    3. 运行 AutoRunner
    4. 将测试摘要保存到 logs/ 目录
    """
    load_dotenv()
    args = parse_args()

    api_key = os.getenv("DEEPSEEK_API_KEY")
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")

    if not api_key:
        print("错误: 请在 .env 文件中设置 DEEPSEEK_API_KEY")
        sys.exit(1)

    debug_mode = not args.no_debug
    session_file, llm_file = init_logging(PROJECT_ROOT, debug_mode=debug_mode)
    log = get_logger()
    log.info("E2E 测试日志: %s", session_file)
    log.info("LLM 调用日志: %s", llm_file)

    log.info("正在连接到 DeepSeek...")
    try:
        llm = LLMClient(api_key=api_key, base_url=base_url, model=model, thinking=False)
    except Exception as e:
        log.error("连接失败: %s", e)
        sys.exit(1)

    # 运行自动化测试
    runner = AutoRunner(
        llm=llm,
        max_rounds=args.max_rounds,
        max_scenes=args.max_scenes,
        player_history_window=args.player_history,
        debug_mode=debug_mode,
    )

    summary = runner.run(
        character=DEMO_CHARACTER,
        first_scene=build_demo_scene(),
    )

    # 保存摘要到 logs/ 目录
    logs_dir = os.path.join(PROJECT_ROOT, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    summary_file = os.path.join(logs_dir, "e2e_last_summary.json")
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    log.info("测试摘要已保存到: %s", summary_file)


if __name__ == "__main__":
    main()
