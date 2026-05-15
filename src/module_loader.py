import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dacite import Config, from_dict

from src.models import NPC, GameItem, Place
from src.state.character_state import CharacterState
from src.state.scene_state import SceneState


@dataclass
class GlobalStateInit:
    places: list[Place]
    items: list[GameItem]
    npcs: list[NPC]


@dataclass
class ModuleData:
    id: str
    name: str
    description: str
    worldview: str
    character: CharacterState
    global_state_init: GlobalStateInit
    initial_scene: SceneState


class ModuleLoader:
    """负责从 JSON 数据文件加载模组。"""

    def __init__(self, modules_dir: str = "data/modules"):
        self.modules_dir = Path(modules_dir)

    def load_module(self, module_id: str) -> ModuleData:
        """加载指定 ID 的模组数据。"""
        file_path = self.modules_dir / f"{module_id}.json"
        if not file_path.exists():
            raise FileNotFoundError(f"Module file not found: {file_path}")

        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        # dacite config to support type conversions if necessary (e.g. sets)
        config = Config(cast=[set, tuple])
        module_data = from_dict(data_class=ModuleData, data=data, config=config)
        return module_data

    def list_available_modules(self) -> list[dict[str, Any]]:
        """列出所有可用的模组基础信息。"""
        modules = []
        if not self.modules_dir.exists():
            return modules

        for file_path in self.modules_dir.glob("*.json"):
            try:
                with open(file_path, encoding="utf-8") as f:
                    data = json.load(f)
                    modules.append(
                        {
                            "id": data.get("id"),
                            "name": data.get("name"),
                            "description": data.get("description"),
                        }
                    )
            except Exception as e:
                print(f"Failed to load module info from {file_path}: {e}")

        return modules
