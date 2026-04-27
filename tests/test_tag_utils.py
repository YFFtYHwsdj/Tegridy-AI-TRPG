import unittest
from src.pipeline._tag_utils import extract_tag_names, extract_status_names, extract_status_tiers
from src.models import AgentNote


class TestExtractNames(unittest.TestCase):

    def test_empty(self):
        self.assertEqual(extract_tag_names([]), [])
        self.assertEqual(extract_status_names([]), [])

    def test_dict_items(self):
        items = [{"name": "快速拔枪"}, {"name": "读懂房间"}]
        self.assertEqual(extract_tag_names(items), ["快速拔枪", "读懂房间"])

    def test_string_items(self):
        items = ["前公司安保", "信用破产"]
        self.assertEqual(extract_tag_names(items), ["前公司安保", "信用破产"])

    def test_mixed_and_missing_keys(self):
        items = [{"name": "A"}, "B", {"other": "C"}]
        self.assertEqual(extract_tag_names(items), ["A", "B"])

    def test_custom_key(self):
        items = [{"status_name": "受伤"}, {"status_name": "被说服"}]
        # extract_tag_names 和 extract_status_names 使用不同的 key 会不同吗？
        # 它们都是同一个 _extract_names_from_tags，默认 key="name"
        # 所以用 status_name 键时不会被提取（除非改名调用）
        self.assertEqual(extract_tag_names(items), [])


class TestExtractStatusTiers(unittest.TestCase):

    def test_both_present(self):
        note = AgentNote(
            reasoning="分析",
            structured={
                "helping_statuses": [
                    {"name": "高位", "tier": 3},
                ],
                "hindering_statuses": [
                    {"name": "受伤", "tier": 2},
                ],
            },
        )
        best, worst = extract_status_tiers(note)
        self.assertEqual(best, 3)
        self.assertEqual(worst, 2)

    def test_only_helping(self):
        note = AgentNote(
            reasoning="分析",
            structured={
                "helping_statuses": [{"name": "优势", "tier": 2}],
                "hindering_statuses": [],
            },
        )
        best, worst = extract_status_tiers(note)
        self.assertEqual(best, 2)
        self.assertEqual(worst, 0)

    def test_only_hindering(self):
        note = AgentNote(
            reasoning="分析",
            structured={
                "helping_statuses": [],
                "hindering_statuses": [{"name": "受伤", "tier": 1}],
            },
        )
        best, worst = extract_status_tiers(note)
        self.assertEqual(best, 0)
        self.assertEqual(worst, 1)

    def test_empty(self):
        note = AgentNote(reasoning="空", structured={})
        best, worst = extract_status_tiers(note)
        self.assertEqual(best, 0)
        self.assertEqual(worst, 0)

    def test_multiple_helping_takes_max(self):
        note = AgentNote(
            reasoning="分析",
            structured={
                "helping_statuses": [
                    {"name": "A", "tier": 1},
                    {"name": "B", "tier": 4},
                    {"name": "C", "tier": 2},
                ],
                "hindering_statuses": [],
            },
        )
        best, worst = extract_status_tiers(note)
        self.assertEqual(best, 4)
        self.assertEqual(worst, 0)

    def test_missing_tier_key_skipped(self):
        note = AgentNote(
            reasoning="分析",
            structured={
                "helping_statuses": [
                    {"name": "位置优势"},
                ],
                "hindering_statuses": [],
            },
        )
        best, worst = extract_status_tiers(note)
        self.assertEqual(best, 0)
        self.assertEqual(worst, 0)


if __name__ == "__main__":
    unittest.main()
