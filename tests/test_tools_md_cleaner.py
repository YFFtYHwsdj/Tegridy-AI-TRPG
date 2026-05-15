import unittest
from unittest.mock import patch, mock_open, MagicMock, call
import os
import json

from src.tools.md_cleaner import (
    RawNode, CleanedNode,
    parse_markdown_from_string,
    clean_markdown_nodes,
    save_nodes_to_file,
    get_raw_markdown,
    main
)

class TestMDCleaner(unittest.TestCase):
    
    def test_parse_markdown_from_string(self):
        md_text = "# Header 1\nContent 1\n## Header 2\nContent 2"
        nodes = parse_markdown_from_string(md_text)
        self.assertEqual(len(nodes), 2)
        self.assertEqual(nodes[0].level, 1)
        self.assertEqual(nodes[0].title, "Header 1")
        self.assertEqual(nodes[0].raw_content, "Content 1\n")
        self.assertEqual(nodes[1].level, 2)
        self.assertEqual(nodes[1].title, "Header 2")
        self.assertEqual(nodes[1].raw_content, "Content 2")
        
        # Test no headers
        nodes_no_header = parse_markdown_from_string("Just some text")
        self.assertEqual(len(nodes_no_header), 1)
        self.assertEqual(nodes_no_header[0].level, 0)
        self.assertEqual(nodes_no_header[0].title, "Document Root")
        self.assertEqual(nodes_no_header[0].raw_content, "Just some text")

    def test_get_raw_markdown_md(self):
        mock_file_content = "# Test"
        with patch("builtins.open", mock_open(read_data=mock_file_content)):
            content = get_raw_markdown("test.md")
            self.assertEqual(content, mock_file_content)

    @patch.dict('sys.modules', {'pymupdf4llm': MagicMock()})
    def test_get_raw_markdown_pdf(self):
        import pymupdf4llm
        pymupdf4llm.to_markdown.return_value = "# Extracted PDF"
        content = get_raw_markdown("test.pdf")
        self.assertEqual(content, "# Extracted PDF")
        pymupdf4llm.to_markdown.assert_called_once_with("test.pdf")
        
    def test_get_raw_markdown_invalid_ext(self):
        with self.assertRaises(ValueError):
            get_raw_markdown("test.txt")

    @patch("src.tools.md_cleaner.os.makedirs")
    def test_save_nodes_to_file(self, mock_makedirs):
        nodes = [
            CleanedNode(level=1, title="Chapter 1", content="Content 1"),
            CleanedNode(level=1, title="Chapter 1", content="Content 1 continuation"), # duplicate title
            CleanedNode(level=0, title="", content="Just text"), # no title
            CleanedNode(level=2, title="Section 1", content="") # no content
        ]
        
        m_open = mock_open()
        with patch("builtins.open", m_open):
            save_nodes_to_file(nodes, "output/test.md")
            
        mock_makedirs.assert_called_once_with(os.path.dirname(os.path.abspath("output/test.md")), exist_ok=True)
        handle = m_open()
        
        # Check written calls
        expected_calls = [
            call("# Chapter 1\n\n"),
            call("Content 1\n\n"),
            call("Content 1 continuation\n\n"),
            call("Just text\n\n"),
            call("## Section 1\n\n")
        ]
        handle.write.assert_has_calls(expected_calls, any_order=False)

    def test_clean_markdown_nodes_success(self):
        mock_llm = MagicMock()
        mock_response = {
            "reasoning": "Looks good",
            "nodes": [
                {"level": 1, "title": "Cleaned", "content": "Content"}
            ]
        }
        mock_llm.chat.return_value = (json.dumps(mock_response), None)
        
        raw_nodes = [RawNode(level=1, title="Raw", raw_content="Raw")]
        cleaned = clean_markdown_nodes(raw_nodes, mock_llm)
        
        self.assertEqual(len(cleaned), 1)
        self.assertEqual(cleaned[0].title, "Cleaned")
        self.assertTrue(mock_llm.chat.called)
        
    def test_clean_markdown_nodes_json_error(self):
        mock_llm = MagicMock()
        mock_llm.chat.return_value = ("Invalid JSON", None)
        
        raw_nodes = [RawNode(level=1, title="Raw", raw_content="Raw Content")]
        cleaned = clean_markdown_nodes(raw_nodes, mock_llm)
        
        # Fallback to original
        self.assertEqual(len(cleaned), 1)
        self.assertEqual(cleaned[0].title, "Raw")
        self.assertEqual(cleaned[0].content, "Raw Content")
        
    def test_clean_markdown_nodes_no_content(self):
        mock_llm = MagicMock()
        raw_nodes = [RawNode(level=0, title="", raw_content="   \n   ")]
        cleaned = clean_markdown_nodes(raw_nodes, mock_llm)
        self.assertEqual(len(cleaned), 0)
        self.assertFalse(mock_llm.chat.called)

    @patch("src.tools.md_cleaner.get_raw_markdown")
    @patch("src.tools.md_cleaner.parse_markdown_from_string")
    @patch("src.tools.md_cleaner.clean_markdown_nodes")
    @patch("src.tools.md_cleaner.save_nodes_to_file")
    @patch("src.tools.md_cleaner.LLMClient")
    @patch("sys.argv", ["md_cleaner.py", "-i", "input.md", "-o", "output.md", "--limit", "1", "--debug"])
    @patch("src.tools.md_cleaner.os.getenv")
    def test_main(self, mock_getenv, mock_llm_class, mock_save, mock_clean, mock_parse, mock_get_raw):
        mock_getenv.side_effect = lambda k, d=None: "dummy" if k in ["DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL"] else d
        
        mock_get_raw.return_value = "raw"
        mock_parse.return_value = [RawNode(level=1, title="T", raw_content="C")]
        mock_clean.return_value = [CleanedNode(level=1, title="T", content="C")]
        
        main()
        
        mock_get_raw.assert_called_once_with("input.md")
        mock_parse.assert_called_once_with("raw")
        mock_clean.assert_called_once()
        mock_save.assert_called_once()

    @patch("sys.argv", ["md_cleaner.py", "-i", "input.md", "-o", "output.md"])
    @patch("src.tools.md_cleaner.os.getenv")
    def test_main_missing_env(self, mock_getenv):
        mock_getenv.return_value = None
        with self.assertRaises(SystemExit):
            main()

    @patch("src.tools.md_cleaner.get_raw_markdown")
    @patch("src.tools.md_cleaner.parse_markdown_from_string")
    @patch("src.tools.md_cleaner.save_nodes_to_file")
    @patch("src.tools.md_cleaner.LLMClient")
    @patch("sys.argv", ["md_cleaner.py", "-i", "input.md", "-o", "output.md", "--debug"])
    @patch("src.tools.md_cleaner.os.getenv")
    @patch("src.tools.md_cleaner.os.path.exists")
    @patch("src.tools.md_cleaner.os.remove")
    def test_main_with_hierarchy_and_debug(self, mock_remove, mock_exists, mock_getenv, mock_llm_class, mock_save, mock_parse, mock_get_raw):
        # 补齐所有覆盖率缺失，包括 get_parent_node, context 拼接, debug 日志写入, Exception fallback
        mock_getenv.side_effect = lambda k, d=None: "dummy" if k in ["DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL"] else d
        mock_exists.return_value = True
        
        # 构造节点模拟：
        # 1. 第一章 (level 1)
        # 2. 第二章 (level 1) -> 测试 parent 为 None
        # 3. 小节 (level 2) -> 测试 parent 为 第二章
        # 4. 孙节 (level 3) -> 测试 parent 为 小节
        # 其中一个节点让 LLM 抛出异常，测试 fallback
        
        mock_get_raw.return_value = "raw"
        mock_parse.return_value = [
            RawNode(level=0, title="", raw_content="0"), # hit line 66
            RawNode(level=1, title="C1", raw_content="A"),
            RawNode(level=1, title="C2", raw_content="B" * 600), # > 500 chars to hit next_text truncation
            RawNode(level=2, title="S1", raw_content="C"),
            RawNode(level=3, title="SS1", raw_content="D")
        ]
        
        mock_llm_instance = MagicMock()
        mock_llm_class.return_value = mock_llm_instance
        
        def mock_chat_side_effect(*args, **kwargs):
            if "S1" in kwargs.get("user_message", ""):
                raise Exception("Test Exception for 240")
            return (json.dumps({"nodes": [{"level": 1, "title": "OK", "content": "OK"}]}), None)
            
        mock_llm_instance.chat.side_effect = mock_chat_side_effect
        
        m_open = mock_open()
        with patch("src.tools.md_cleaner.open", m_open, create=True):
            main()
            
        # 验证 Debug 模式下文件被打开并写入 (md_cleaner_debug.log)
        m_open.assert_any_call("md_cleaner_debug.log", "a", encoding="utf-8")
