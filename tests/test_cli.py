"""Synthetic I/O and command tests; no scientific runs or scores."""

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from worldedge_eval.cli import main
from worldedge_eval.io import read_records


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "experiment.yaml"


class CommandTests(unittest.TestCase):
    def invoke(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_plan_matches_declared_campaign_without_running_it(self):
        code, out, _ = self.invoke("plan", "--config", str(CONFIG))
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertEqual(result["policy"]["total_lifetimes"], 540)
        self.assertEqual(result["policy"]["total_scheduled_tasks"], 5400)
        self.assertEqual(result["rooms"]["accepted_total"], 590)

    def test_preflight_retains_unresolved_fields_and_nonzero_exit(self):
        code, out, _ = self.invoke("preflight", "--config", str(CONFIG))
        self.assertEqual(code, 2)
        result = json.loads(out)
        self.assertTrue(result["structurally_valid"])
        self.assertFalse(result["configuration_complete"])
        self.assertGreater(len(result["unresolved_fields"]), 0)

    def test_malformed_json_and_nonfinite_inputs_fail_clearly(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.jsonl"
            path.write_text('{"value": NaN}\n')
            with self.assertRaises(ValueError):
                read_records(path)
            path.write_text("3\n")
            with self.assertRaises(ValueError):
                read_records(path)

    def test_validate_checks_each_record_and_does_not_accept_empty_input(self):
        with tempfile.TemporaryDirectory() as directory:
            schema = Path(directory) / "schema.json"
            data = Path(directory) / "data.jsonl"
            schema.write_text(json.dumps({
                "type": "object",
                "properties": {"synthetic": {"type": "boolean"}},
                "required": ["synthetic"],
            }))
            data.write_text('{"synthetic": true}\n{"synthetic": 3}\n')
            code, out, _ = self.invoke("validate", "--schema", str(schema), "--input", str(data))
            self.assertEqual(code, 2)
            self.assertEqual(json.loads(out)["errors"][0]["record_index"], 1)
            data.write_text("")
            code, _, err = self.invoke("validate", "--schema", str(schema), "--input", str(data))
            self.assertEqual(code, 2)
            self.assertIn("at least one record", err)

    def test_empty_outcomes_remain_missing_scheduled_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            schedule = Path(directory) / "schedule.json"
            outcomes = Path(directory) / "outcomes.jsonl"
            result = Path(directory) / "score.json"
            schedule.write_text(json.dumps([{
                "run_id": "synthetic_run",
                "model_id": "synthetic_model",
                "setting": "manipulation",
                "world_id": "synthetic_world",
                "source_group_id": "synthetic_group",
                "seed": 0,
            }]))
            outcomes.write_text("")
            code, _, _ = self.invoke(
                "score-policy", "--manifest", str(schedule), "--records", str(outcomes),
                "--model", "synthetic_model", "--output", str(result),
            )
            self.assertEqual(code, 2)
            payload = json.loads(result.read_text())
            self.assertFalse(payload["reportable"])
            self.assertIsNone(payload["metrics"])
            self.assertEqual(payload["missing_run_ids"], ["synthetic_run"])

    def test_templates_are_unmeasured_and_final_export_rejects_missing_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            code, _, _ = self.invoke(
                "tables", "--config", str(CONFIG), "--output-dir", directory,
            )
            self.assertEqual(code, 0)
            path = Path(directory)
            self.assertIn("Manipulation", (path / "table4.tex").read_text())
            self.assertIn("--", (path / "table5.tex").read_text())
            self.assertNotIn("DreamDojo-14B", (path / "table5.tex").read_text())
            coverage = json.loads((path / "coverage.json").read_text())
            self.assertFalse(coverage["all_configured_rows_complete"])
            self.assertTrue(all(row["status"] == "not_run" for row in coverage["policy_rows"]))
            code, _, err = self.invoke(
                "tables", "--config", str(CONFIG), "--output-dir", str(path / "final"),
                "--require-complete",
            )
            self.assertEqual(code, 2)
            self.assertIn("unrun/incomplete", err)
            self.assertFalse((path / "final").exists())


if __name__ == "__main__":
    unittest.main()
