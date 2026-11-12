"""Synthetic publication-accounting checks. Fixtures are not benchmark results."""

from pathlib import Path
import tempfile
import unittest

from worldedge_eval.config import load_config
from worldedge_eval.metrics import policy_metrics
from worldedge_eval.reporting import export_tables


ROOT = Path(__file__).resolve().parents[1]


class ReportingTests(unittest.TestCase):
    def setUp(self):
        self.config = load_config(ROOT / "configs/experiment.yaml")

    def test_small_complete_manifest_is_not_full_campaign_evidence(self):
        score = {
            "suite": "policy", "model_id": "pi05_robodojo",
            "setting": "manipulation", "reportable": True,
            "metrics": policy_metrics([[1] * 10]),
        }
        with tempfile.TemporaryDirectory() as directory:
            export_tables(self.config, [score], [], directory)
            tex = (Path(directory) / "table4.tex").read_text()
            self.assertIn(r"$\pi_{0.5}$ & NR & NR & NR & NR", tex)
            self.assertNotIn("100.0", tex)

    def test_duplicate_and_disabled_models_fail_instead_of_being_silently_ignored(self):
        score = {"suite": "policy", "model_id": "pi05_robodojo", "reportable": False}
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                export_tables(self.config, [score, score], [], directory)
            with self.assertRaisesRegex(ValueError, "disabled"):
                export_tables(
                    self.config, [],
                    [{"suite": "video", "model_id": "dreamdojo_14b", "reportable": False}],
                    directory,
                )

    def test_wrong_setting_cannot_be_presented_in_another_block(self):
        score = {
            "suite": "policy", "model_id": "pi05_robodojo",
            "setting": "mobile_manipulation", "reportable": True,
            "metrics": policy_metrics([[1] * 10 for _ in range(60)]),
        }
        with tempfile.TemporaryDirectory() as directory:
            export_tables(self.config, [score], [], directory)
            text = (Path(directory) / "table4.tex").read_text()
            self.assertIn(r"$\pi_{0.5}$ & NR & NR & NR & NR", text)


if __name__ == "__main__":
    unittest.main()
