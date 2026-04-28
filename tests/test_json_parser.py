import unittest

from src.json_parser import _extract_json_object, _recover_json, parse_agent_output
from src.models import AgentNote


class TestExtractJsonObject(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(_extract_json_object('{"a": 1}'), '{"a": 1}')

    def test_text_before(self):
        self.assertEqual(_extract_json_object('前缀文字 {"a": 1}'), '{"a": 1}')

    def test_text_after(self):
        self.assertEqual(_extract_json_object('{"a": 1} 后缀文字'), '{"a": 1}')

    def test_nested(self):
        result = _extract_json_object('{"a": {"b": 2}}')
        self.assertEqual(result, '{"a": {"b": 2}}')

    def test_multiple_objects_extracts_first(self):
        result = _extract_json_object('{"first": 1} {"second": 2}')
        self.assertEqual(result, '{"first": 1}')

    def test_no_brace(self):
        self.assertIsNone(_extract_json_object("纯文本没有花括号"))

    def test_string_with_brace_inside(self):
        result = _extract_json_object('{"key": "value with } inside"}')
        self.assertEqual(result, '{"key": "value with } inside"}')

    def test_escaped_quote_in_string(self):
        result = _extract_json_object('{"key": "value with \\" quote"}')
        self.assertEqual(result, '{"key": "value with \\" quote"}')


class TestRecoverJson(unittest.TestCase):
    def test_direct_parse(self):
        self.assertEqual(_recover_json('{"a": 1}'), {"a": 1})

    def test_trailing_comma(self):
        self.assertEqual(_recover_json('{"a": 1,}'), {"a": 1})

    def test_trailing_comma_in_array(self):
        self.assertEqual(_recover_json('{"a": [1, 2,]}'), {"a": [1, 2]})

    def test_balanced_extraction(self):
        self.assertEqual(_recover_json('前缀文本 {"a": 1} 后缀文本'), {"a": 1})

    def test_balanced_extraction_with_trailing_comma(self):
        self.assertEqual(_recover_json('前缀 {"a": 1,} 后缀'), {"a": 1})

    def test_single_quotes(self):
        self.assertEqual(_recover_json("{'a': 'hello'}"), {"a": "hello"})

    def test_unquoted_keys(self):
        self.assertEqual(_recover_json('{a: 1, b: "test"}'), {"a": 1, "b": "test"})

    def test_empty_string(self):
        self.assertIsNone(_recover_json(""))

    def test_unrecoverable(self):
        self.assertIsNone(_recover_json("这不是JSON甚至不是近似JSON的文本"))


class TestParseAgentOutput(unittest.TestCase):
    def test_both_sections(self):
        raw = '=====REASONING=====\n这是一段分析推理\n=====STRUCTURED=====\n{"a": 1}'
        result = parse_agent_output(raw)
        self.assertIsInstance(result, AgentNote)
        self.assertEqual(result.reasoning, "这是一段分析推理")
        self.assertEqual(result.structured, {"a": 1})

    def test_no_reasoning_section(self):
        raw = '=====STRUCTURED=====\n{"a": 1}'
        result = parse_agent_output(raw)
        self.assertEqual(result.reasoning, "")
        self.assertEqual(result.structured, {"a": 1})

    def test_no_structured_section(self):
        raw = "=====REASONING=====\n分析内容"
        result = parse_agent_output(raw)
        self.assertEqual(result.reasoning, "")
        self.assertEqual(result.structured, {})

    def test_unparseable_structured_falls_back_to_raw(self):
        raw = "=====STRUCTURED=====\n这不是JSON"
        result = parse_agent_output(raw)
        self.assertEqual(result.structured, {"raw": "这不是JSON"})

    def test_reasoning_multiline(self):
        raw = '=====REASONING=====\n第一行分析\n第二行分析\n=====STRUCTURED=====\n{"x": true}'
        result = parse_agent_output(raw)
        self.assertEqual(result.reasoning, "第一行分析\n第二行分析")
        self.assertEqual(result.structured, {"x": True})

    def test_structured_with_trailing_comma(self):
        raw = '=====REASONING=====\n分析\n=====STRUCTURED=====\n{"a": 1,}'
        result = parse_agent_output(raw)
        self.assertEqual(result.structured, {"a": 1})


if __name__ == "__main__":
    unittest.main()
