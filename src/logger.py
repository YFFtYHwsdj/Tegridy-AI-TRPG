"""日志模块 —— 统一日志系统。

基于 Python logging 模块，双 Logger + 双文件输出：
    - aitrpg.game → logs/*_session.log   — 游戏事件（叙事、掷骰、状态、调试追踪）
    - aitrpg.llm  → logs/*_llm_calls.log  — LLM 完整调用（system prompt / user / response）

控制台输出规则：
    - aitrpg.game: 调试模式下输出 DEBUG+，正常模式下仅 INFO+
    - aitrpg.llm:  仅摘要（INFO）输出到控制台，完整提示词和响应仅写入 llm_calls.log

日志等级规范：
    DEBUG:   内部追踪（标签匹配、效果逐条执行、目标解析、JSON修复过程、Agent调用状态）
    INFO:    玩家可见叙事、系统命令响应、LLM调用摘要、掷骰结果、状态变更
    WARNING: 非致命异常（目标解析失败、标签不存在、JSON回退、效果部分失败、LLM重试）
    ERROR:   致命错误（API调用失败、效果应用错误、连接失败）

向后兼容封装（内部委托到 logging 模块）：
    - log_system(msg, level="info")
    - log_call(agent_name, system_prompt, user_message, response, usage_info)
    - log_roll(power, dice, total, outcome, power_tags, weakness_tags)
    - log_status_update(entity_name, statuses)
"""

from __future__ import annotations

import logging
import os
from datetime import datetime

GAME_LOGGER_NAME = "aitrpg.game"
LLM_LOGGER_NAME = "aitrpg.llm"

_console_handler: logging.Handler | None = None


def _create_file_handler(filepath: str, level: int) -> logging.Handler | None:
    """安全创建 FileHandler，磁盘满或权限不足时返回 None 而非崩溃。

    Args:
        filepath: 日志文件路径
        level: 日志等级阈值

    Returns:
        FileHandler 实例，创建失败返回 None
    """
    try:
        handler = logging.FileHandler(filepath, encoding="utf-8")
    except OSError:
        print(f"警告: 无法创建日志文件 {filepath}，文件日志已禁用")
        return None
    handler.setLevel(level)
    return handler


def init_logging(project_root: str, debug_mode: bool = False) -> tuple[str, str]:
    """初始化统一日志系统。

    创建两个日志文件并分别配置各自的 Handler。

    Args:
        project_root: 项目根目录路径
        debug_mode: 是否启用调试模式（控制台输出 DEBUG 消息）

    Returns:
        (游戏事件日志文件路径, LLM调用日志文件路径) 元组

    副作用:
        - 创建 logs/ 目录（如不存在）
        - 初始化模块级 _console_handler 引用
    """
    global _console_handler

    logs_dir = os.path.join(project_root, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_file = os.path.join(logs_dir, f"{timestamp}_session.log")
    llm_calls_file = os.path.join(logs_dir, f"{timestamp}_llm_calls.log")

    # ── aitrpg.game — 游戏事件日志 ────────────────────────
    game_logger = logging.getLogger(GAME_LOGGER_NAME)
    game_logger.setLevel(logging.DEBUG)
    game_logger.handlers.clear()
    game_logger.propagate = False

    # 游戏事件 → 文件（全部级别）
    game_file = _create_file_handler(session_file, logging.DEBUG)
    if game_file:
        game_file.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)-7s] %(message)s",
                datefmt="%H:%M:%S",
            )
        )
        game_logger.addHandler(game_file)

    # 游戏事件 → 控制台（调试模式 DEBUG+，正常模式 INFO+）
    _console_handler = logging.StreamHandler()
    _console_handler.setLevel(logging.DEBUG if debug_mode else logging.INFO)
    _console_handler.setFormatter(logging.Formatter("%(message)s"))
    game_logger.addHandler(_console_handler)

    # ── aitrpg.llm — LLM 完整调用日志 ─────────────────────
    llm_logger = logging.getLogger(LLM_LOGGER_NAME)
    llm_logger.setLevel(logging.DEBUG)
    llm_logger.handlers.clear()
    llm_logger.propagate = False

    # LLM 调用 → 文件（全部级别，含完整提示词和响应）
    llm_file = _create_file_handler(llm_calls_file, logging.DEBUG)
    if llm_file:
        llm_file.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)-7s] %(message)s",
                datefmt="%H:%M:%S",
            )
        )
        llm_logger.addHandler(llm_file)

    # LLM 调用摘要 → 控制台（仅 INFO，完整内容不输出到终端）
    llm_console = logging.StreamHandler()
    llm_console.setLevel(logging.INFO)
    llm_console.setFormatter(logging.Formatter("%(message)s"))
    llm_logger.addHandler(llm_console)

    # 写入会话头
    game_logger.info("═" * 50)
    game_logger.info("  AI-TRPG 会话日志")
    game_logger.info("  会话: %s", timestamp)
    game_logger.info("═" * 50)

    llm_logger.info("═" * 50)
    llm_logger.info("  AI-TRPG LLM 调用日志")
    llm_logger.info("  会话: %s", timestamp)
    llm_logger.info("═" * 50)

    return session_file, llm_calls_file


def get_game_logger() -> logging.Logger:
    """获取游戏事件日志记录器（aitrpg.game）。

    Returns:
        配置好的 Logger 实例
    """
    return logging.getLogger(GAME_LOGGER_NAME)


def get_llm_logger() -> logging.Logger:
    """获取 LLM 调用日志记录器（aitrpg.llm）。

    通常不直接使用——由 log_call() 内部调用。
    仅当需要手动记录 LLM 相关事件时使用。

    Returns:
        配置好的 Logger 实例
    """
    return logging.getLogger(LLM_LOGGER_NAME)


def get_logger() -> logging.Logger:
    """获取游戏事件日志记录器（向后兼容别名，等同于 get_game_logger()）。

    Returns:
        aitrpg.game Logger 实例
    """
    return logging.getLogger(GAME_LOGGER_NAME)


def set_debug_mode(enabled: bool):
    """动态切换控制台的调试模式。

    仅影响 aitrpg.game 的控制台输出等级。
    aitrpg.llm 的控制台输出始终为 INFO（不输出完整提示词）。

    Args:
        enabled: 是否启用调试模式
    """
    global _console_handler
    if _console_handler:
        _console_handler.setLevel(logging.DEBUG if enabled else logging.INFO)


def log_system(msg: str, level: str = "info"):
    """记录一条系统事件到游戏日志。

    向后兼容封装。新代码可直接使用 get_game_logger().debug/info/warning/error()。

    Args:
        msg: 日志消息文本
        level: 日志等级，支持 "debug" / "info" / "warning" / "error"
    """
    game = get_game_logger()
    level_methods = {
        "debug": game.debug,
        "info": game.info,
        "warning": game.warning,
        "error": game.error,
    }
    log_fn = level_methods.get(level.lower(), game.info)
    log_fn("[系统] %s", msg)


def log_call(
    agent_name: str,
    system_prompt: str,
    user_message: str,
    response: str,
    usage_info: dict | None = None,
):
    """记录一次完整的 LLM API 调用。

    双通道分发：
    - aitrpg.game（INFO）: 仅调用摘要（Agent名 + token用量）—— 出现在终端和 session.log
    - aitrpg.llm（INFO）:  同上摘要 —— 出现在终端和 llm_calls.log
    - aitrpg.llm（DEBUG）: 完整 system prompt / user message / response —— 仅 llm_calls.log

    对 DeepSeek 缓存命中场景，细分缓存命中量和未缓存量。

    Args:
        agent_name: Agent 名称标识
        system_prompt: 系统提示词完整文本
        user_message: 用户消息完整文本
        response: LLM 返回完整文本
        usage_info: Token 用量信息（prompt_tokens/completion_tokens/
                    total_tokens/cached_tokens）
    """
    game = get_game_logger()
    llm = get_llm_logger()

    if usage_info:
        prompt = usage_info.get("prompt_tokens", 0)
        completion = usage_info.get("completion_tokens", 0)
        total = usage_info.get("total_tokens", 0)
        cached = usage_info.get("cached_tokens")
        if cached is not None:
            uncached = prompt - cached
            token_str = (
                f"提示{prompt}(缓存{cached}+未缓存{uncached}) | 生成{completion} | 合计{total}"
            )
        else:
            token_str = f"提示{prompt}(无缓存) | 生成{completion} | 合计{total}"
    else:
        token_str = "token 用量未知"

    summary = f"LLM调用 · {agent_name} | {token_str}"
    game.info(summary)
    llm.info(summary)

    # 完整提示词和响应仅写入 LLM 调用日志文件（DEBUG），终端不可见
    sep = "═" * 70
    llm.debug(sep)
    llm.debug("SYSTEM PROMPT (%s):", agent_name)
    llm.debug(sep)
    for line in system_prompt.split("\n"):
        llm.debug("│ %s", line)

    llm.debug(sep)
    llm.debug("USER MESSAGE (%s):", agent_name)
    llm.debug(sep)
    for line in user_message.split("\n"):
        llm.debug("│ %s", line)

    llm.debug(sep)
    llm.debug("RESPONSE (%s):", agent_name)
    llm.debug(sep)
    for line in response.split("\n"):
        llm.debug("│ %s", line)

    llm.debug(sep)
    llm.debug("")


def log_roll(
    power: int,
    dice: tuple,
    total: int,
    outcome: str,
    power_tags: list,
    weakness_tags: list,
):
    """记录一次掷骰结果到游戏日志。

    记录力量计算因子（匹配标签）和掷骰详情，INFO 级别，
    便于追踪 PBTA 规则执行是否符合预期。

    Args:
        power: 力量值
        dice: (d1, d2) 骰面元组
        total: 骰面之和 + 力量修正 = 总结果
        outcome: full_success / partial_success / failure
        power_tags: 命中的力量标签名列表
        weakness_tags: 命中的弱点标签名列表
    """
    game = get_game_logger()
    game.info("─" * 60)
    game.info(
        "掷骰 | 力量标签:%s | 弱点标签:%s | 力量:%d | 掷骰:%d+%d=%d → %s",
        power_tags,
        weakness_tags,
        power,
        dice[0],
        dice[1],
        total,
        outcome,
    )
    game.info("─" * 60)


def log_status_update(entity_name: str, statuses: dict):
    """记录实体状态变更到游戏日志。

    对角色或挑战的完整状态快照进行记录，INFO 级别。
    无状态时输出占位信息。

    Args:
        entity_name: 实体名称（角色名或挑战名）
        statuses: {状态名: Status对象} 字典
    """
    game = get_game_logger()
    if not statuses:
        game.info("[状态] %s → (无状态)", entity_name)
        return
    game.info("[状态] %s:", entity_name)
    for name, s in statuses.items():
        game.info("  %s: 等级%d (格子: %s)", name, s.current_tier, sorted(s.ticked_boxes))
