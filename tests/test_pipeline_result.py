import unittest

from src.models import AgentNote, RollResult
from src.pipeline.pipeline_result import PipelineResult


class TestPipelineResult(unittest.TestCase):
    def test_full_pipeline(self):
        tag_note = AgentNote(
            reasoning="标签匹配分析", structured={"matched_power_tags": [{"name": "快速拔枪"}]}
        )
        roll = RollResult(power=2, dice=(5, 4), total=11, outcome="full_success")
        effect_note = AgentNote(
            reasoning="效果推演",
            structured={
                "effects": [{"effect_type": "attack", "tier": 2, "target": "挑战", "label": "受伤"}]
            },
        )
        consequence_note = AgentNote(
            reasoning="后果分析", structured={"consequences": [{"threat_manifested": "保镖介入"}]}
        )
        narrator_note = AgentNote(reasoning="叙事策略", structured={"narrative": "你迅速拔枪..."})

        result = PipelineResult(
            tag_note=tag_note,
            roll=roll,
            effect_note=effect_note,
            consequence_note=consequence_note,
            narrator_note=narrator_note,
        )

        self.assertIs(result.tag_note, tag_note)
        self.assertIs(result.roll, roll)
        self.assertIs(result.effect_note, effect_note)
        self.assertIs(result.consequence_note, consequence_note)
        self.assertIs(result.narrator_note, narrator_note)

    def test_minimal(self):
        tag_note = AgentNote(reasoning="分析", structured={})
        roll = RollResult(power=1, dice=(3, 3), total=7, outcome="partial_success")
        narrator_note = AgentNote(reasoning="叙事", structured={"narrative": "..."})

        result = PipelineResult(
            tag_note=tag_note,
            roll=roll,
            narrator_note=narrator_note,
        )

        self.assertIsNone(result.effect_note)
        self.assertIsNone(result.consequence_note)

    def test_partial_effect_only(self):
        tag_note = AgentNote(reasoning="标签分析", structured={})
        roll = RollResult(power=1, dice=(4, 2), total=7, outcome="partial_success")
        effect_note = AgentNote(reasoning="效果", structured={"effects": []})
        narrator_note = AgentNote(reasoning="叙事", structured={})

        result = PipelineResult(
            tag_note=tag_note,
            roll=roll,
            effect_note=effect_note,
            narrator_note=narrator_note,
        )

        self.assertIsNotNone(result.effect_note)
        self.assertIsNone(result.consequence_note)


if __name__ == "__main__":
    unittest.main()
