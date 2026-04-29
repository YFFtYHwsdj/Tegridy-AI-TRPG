"""流水线模块入口。"""

from __future__ import annotations

from src.pipeline._item_manager import ItemManager
from src.pipeline.pipeline_result import PipelineResult

__all__ = ["ItemManager", "PipelineResult"]
