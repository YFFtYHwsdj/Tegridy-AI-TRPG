import unittest

from src.module_loader import ModuleLoader


class TestModuleLoader(unittest.TestCase):
    def setUp(self):
        self.loader = ModuleLoader()

    def test_list_available_modules(self):
        """测试模块列表。"""
        modules = self.loader.list_available_modules()
        self.assertTrue(len(modules) >= 2)

        ids = [m["id"] for m in modules]
        self.assertIn("alley", ids)
        self.assertIn("cyber_shrine", ids)

    def test_load_alley_module(self):
        """测试加载 alley 模组。"""
        module = self.loader.load_module("alley")

        self.assertEqual(module.id, "alley")
        self.assertEqual(module.character.name, "Kael")
        self.assertTrue(len(module.worldview) > 0)

        # 验证实体
        places = module.global_state_init.places
        self.assertTrue(any(p.place_id == "alley_01" for p in places))

        # 验证场景内的活动实体
        scene = module.initial_scene
        self.assertEqual(scene.place_id, "alley_01")
        self.assertIn("thug_leader", scene.active_npc_ids)

    def test_load_cyber_shrine_module(self):
        """测试加载 cyber_shrine 模组。"""
        module = self.loader.load_module("cyber_shrine")

        self.assertEqual(module.id, "cyber_shrine")
        self.assertEqual(module.character.name, "Rin")
        self.assertTrue(len(module.worldview) > 0)

        # 验证实体
        places = module.global_state_init.places
        npcs = module.global_state_init.npcs
        items = module.global_state_init.items

        self.assertTrue(any(p.place_id == "shrine_pond_01" for p in places))
        self.assertTrue(any(n.npc_id == "kappa_guardian" for n in npcs))
        self.assertTrue(any(i.item_id == "data_waterfall" for i in items))

        # 验证场景内的活动实体
        scene = module.initial_scene
        self.assertEqual(scene.place_id, "shrine_pond_01")
        self.assertIn("kappa_guardian", scene.active_npc_ids)
        self.assertIn("data_waterfall", scene.active_item_ids)
        self.assertIn("数据湍流", scene.story_tags)
    def test_load_module_not_found(self):
        """测试加载不存在的模组时抛出 FileNotFoundError。"""
        with self.assertRaises(FileNotFoundError):
            self.loader.load_module("non_existent_module_id")

    def test_list_modules_directory_not_exists(self):
        """测试模组目录不存在时返回空列表。"""
        loader = ModuleLoader(modules_dir="non_existent_dir")
        modules = loader.list_available_modules()
        self.assertEqual(modules, [])

    def test_list_modules_invalid_json(self):
        """测试目录中存在无效 JSON 文件时会被跳过。"""
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            loader = ModuleLoader(modules_dir=temp_dir)
            
            # 创建一个有效的 JSON 文件
            valid_file = os.path.join(temp_dir, "valid.json")
            with open(valid_file, "w", encoding="utf-8") as f:
                f.write('{"id": "valid", "name": "Valid Module", "description": "Desc"}')
                
            # 创建一个无效的 JSON 文件
            invalid_file = os.path.join(temp_dir, "invalid.json")
            with open(invalid_file, "w", encoding="utf-8") as f:
                f.write('{"id": "invalid", "name": "Invalid Module", "description": "Desc"') # 缺少右括号
                
            modules = loader.list_available_modules()
            self.assertEqual(len(modules), 1)
            self.assertEqual(modules[0]["id"], "valid")


if __name__ == "__main__":
    unittest.main()
