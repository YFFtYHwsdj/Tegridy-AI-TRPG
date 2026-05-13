"""JSON 解析器测试 —— parse_json_output 的行为验证。

验证 JSON mode 下 LLM 输出的解析：
    - 纯 JSON 输入的正常解析
    - reasoning 字段提取为 AgentNote.reasoning
    - 无 reasoning 字段时 reasoning 为空字符串
    - JSON 解析失败的 fallback 行为
"""

import unittest

from src.json_parser import parse_json_output
from src.models import AgentNote


class TestParseJsonOutput(unittest.TestCase):
    """测试 parse_json_output 的解析行为。"""

    def test_simple_json(self):
        """纯 JSON 输入应正确解析。"""
        result = parse_json_output('{"key": "value"}')
        self.assertIsInstance(result, AgentNote)
        self.assertEqual(result.structured["key"], "value")

    def test_reasoning_extracted(self):
        """reasoning 字段应提取为 AgentNote.reasoning，不出现在 structured 中。"""
        result = parse_json_output('{"reasoning": "思考过程", "action_type": "combat"}')
        self.assertEqual(result.reasoning, "思考过程")
        self.assertEqual(result.structured["action_type"], "combat")
        self.assertNotIn("reasoning", result.structured)

    def test_no_reasoning_field(self):
        """无 reasoning 字段时 reasoning 应为空字符串。"""
        result = parse_json_output('{"action_type": "social"}')
        self.assertEqual(result.reasoning, "")
        self.assertEqual(result.structured["action_type"], "social")

    def test_empty_reasoning(self):
        """reasoning 为空字符串时应正确处理。"""
        result = parse_json_output('{"reasoning": "", "data": 1}')
        self.assertEqual(result.reasoning, "")
        self.assertEqual(result.structured["data"], 1)

    def test_nested_json(self):
        """嵌套 JSON 结构应正确解析。"""
        raw = '{"reasoning": "推理", "effects": [{"type": "attack", "tier": 2}]}'
        result = parse_json_output(raw)
        self.assertEqual(result.reasoning, "推理")
        self.assertEqual(result.structured["effects"][0]["type"], "attack")

    def test_json_parse_failure_raises(self):
        """JSON 解析失败时应抛出 JSONParseError。"""
        from src.json_parser import JSONParseError

        with self.assertRaises(JSONParseError):
            parse_json_output("这不是JSON")

    def test_empty_string_raises(self):
        """空字符串应抛出 JSONParseError。"""
        from src.json_parser import JSONParseError

        with self.assertRaises(JSONParseError):
            parse_json_output("")

    def test_boolean_and_null_values(self):
        """布尔值和 null 应正确解析。"""
        result = parse_json_output('{"reasoning": "测试", "flag": true, "empty": null}')
        self.assertEqual(result.reasoning, "测试")
        self.assertTrue(result.structured["flag"])
        self.assertIsNone(result.structured["empty"])

    def test_chinese_content(self):
        """中文内容应正确解析。"""
        result = parse_json_output('{"reasoning": "这是中文推理", "narrative": "赛博朋克酒吧"}')
        self.assertEqual(result.reasoning, "这是中文推理")
        self.assertEqual(result.structured["narrative"], "赛博朋克酒吧")


if __name__ == "__main__":
    unittest.main()
