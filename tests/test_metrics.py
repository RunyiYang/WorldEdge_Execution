"""Synthetic contract checks only. These fixtures are NOT experiment data."""

import unittest

from worldedge_eval.metrics import policy_metrics, video_metrics


def synthetic_manifest():
    return [
        {"world_id": "synthetic_world_a", "clip_id": "synthetic_positive",
         "ref_outcome": 1, "revisit_expected": True},
        {"world_id": "synthetic_world_b", "clip_id": "synthetic_negative",
         "ref_outcome": 0, "revisit_expected": False},
    ]


def synthetic_outputs():
    rows = []
    for index, clip in enumerate(synthetic_manifest()):
        for seed in (0, 1):
            rows.append({
                **clip, "model_seed": seed,
                "pred_outcome": "success" if clip["ref_outcome"] else "failure",
                "valid_video": True,
                "revisit_correct": True if clip["revisit_expected"] else None,
                "lpips5": 0.1 + 0.2 * index + 0.2 * seed,
                "lpips30": 0.3 + 0.1 * index + 0.2 * seed,
            })
    return rows


class PolicyMetricContractTests(unittest.TestCase):
    def test_fail_then_recover_is_not_successful_prefix_length(self):
        result = policy_metrics([[0] + [1] * 9])
        self.assertEqual(result["completed10_mean"], 9)
        self.assertEqual(result["csr5_percent"], 0)
        self.assertEqual(result["csr10_percent"], 0)

    def test_failed_anchor_stays_in_scheduled_reuse_denominator(self):
        result = policy_metrics([[0] + [1] * 9])
        self.assertEqual(result["delayed_reuse_numerator"], 2)
        self.assertEqual(result["delayed_reuse_denominator"], 3)
        self.assertAlmostEqual(result["delayed_reuse_percent"], 200 / 3)

    def test_csr5_and_csr10_have_distinct_prefixes(self):
        result = policy_metrics([[1] * 5 + [0] + [1] * 4])
        self.assertEqual(result["csr5_percent"], 100)
        self.assertEqual(result["csr10_percent"], 0)
        self.assertEqual(result["completed10_mean"], 9)

    def test_multiple_lifetimes_keep_declared_scales(self):
        result = policy_metrics([[1] * 10, [0] + [1] * 9])
        self.assertEqual(result["csr5_percent"], 50)
        self.assertEqual(result["csr10_percent"], 50)
        self.assertEqual(result["completed10_mean"], 9.5)
        self.assertEqual(result["n_scheduled_tasks"], 20)
        self.assertAlmostEqual(result["delayed_reuse_percent"], 500 / 6)

    def test_reject_incomplete_lifetime_or_duplicate_reuse_pair(self):
        with self.assertRaisesRegex(ValueError, "exactly 10"):
            policy_metrics([[1] * 9])
        with self.assertRaisesRegex(ValueError, "duplicate reuse"):
            policy_metrics([[1] * 10], reuse_pairs=((1, 4), (1, 4)))


class VideoMetricContractTests(unittest.TestCase):
    def test_seed_average_then_clip_average_and_complete_manifest(self):
        result = video_metrics(synthetic_outputs(), synthetic_manifest())
        self.assertTrue(result["coverage_complete"])
        self.assertTrue(result["all_videos_valid"])
        self.assertEqual(result["n_scheduled_outputs"], 4)
        self.assertEqual(result["outcome_ba_percent"], 100)
        self.assertEqual(result["revisit_accuracy_percent"], 100)
        self.assertAlmostEqual(result["per_clip"][0]["lpips5_mean"], 0.2)
        self.assertAlmostEqual(result["per_clip"][1]["lpips5_mean"], 0.4)
        self.assertAlmostEqual(result["lpips5_mean"], 0.3)
        self.assertAlmostEqual(result["lpips30_mean"], 0.45)

    def test_unknown_negative_is_not_a_correct_failure_prediction(self):
        rows = synthetic_outputs()
        for row in rows:
            if row["ref_outcome"] == 0:
                row["pred_outcome"] = "unknown"
        result = video_metrics(rows, synthetic_manifest())
        self.assertEqual(result["outcome_positive_accuracy_percent"], 100)
        self.assertEqual(result["outcome_negative_accuracy_percent"], 0)
        self.assertEqual(result["outcome_ba_percent"], 50)

    def test_missing_seed_is_penalized_and_never_silently_dropped(self):
        rows = synthetic_outputs()
        del rows[1]  # Missing seed 1 of the positive, revisit-eligible clip.
        result = video_metrics(rows, synthetic_manifest())
        self.assertFalse(result["coverage_complete"])
        self.assertEqual(result["n_scheduled_outputs"], 4)
        self.assertEqual(result["n_present_outputs"], 3)
        self.assertEqual(result["outcome_ba_percent"], 75)
        self.assertEqual(result["revisit_accuracy_percent"], 50)
        self.assertEqual(result["per_clip"][0]["missing_model_seeds"], [1])
        self.assertIsNone(result["lpips5_mean"])
        self.assertIsNone(result["lpips30_mean"])

    def test_invalid_video_cannot_claim_correct_outcome_or_revisit(self):
        rows = synthetic_outputs()
        rows[0]["valid_video"] = False
        result = video_metrics(rows, synthetic_manifest())
        self.assertTrue(result["coverage_complete"])
        self.assertFalse(result["all_videos_valid"])
        self.assertEqual(result["n_valid_videos"], 3)
        self.assertEqual(result["outcome_ba_percent"], 75)
        self.assertEqual(result["revisit_accuracy_percent"], 50)
        self.assertIsNone(result["lpips5_mean"])
        self.assertIsNone(result["lpips30_mean"])

    def test_missing_lpips_invalidates_whole_aggregate_for_that_horizon(self):
        rows = synthetic_outputs()
        rows[0]["lpips30"] = None
        result = video_metrics(rows, synthetic_manifest())
        self.assertTrue(result["coverage_complete"])
        self.assertAlmostEqual(result["lpips5_mean"], 0.3)
        self.assertIsNone(result["lpips30_mean"])
        self.assertFalse(result["lpips30_complete"])

    def test_balanced_accuracy_is_not_frequency_weighted_accuracy(self):
        manifest = synthetic_manifest()
        extra = {"world_id": "synthetic_world_c", "clip_id": "synthetic_positive_2",
                 "ref_outcome": 1, "revisit_expected": False}
        manifest.append(extra)
        rows = synthetic_outputs()
        rows.extend({**extra, "model_seed": seed, "pred_outcome": "success",
                     "valid_video": True, "lpips5": 0.2, "lpips30": 0.4}
                    for seed in (0, 1))
        for row in rows:
            if row["ref_outcome"] == 0:
                row["pred_outcome"] = "success"
        result = video_metrics(rows, manifest)
        self.assertEqual(result["outcome_ba_percent"], 50)

    def test_reject_duplicate_output_manifest_and_unscheduled_seed(self):
        rows = synthetic_outputs()
        with self.assertRaisesRegex(ValueError, "duplicate output"):
            video_metrics(rows + [dict(rows[0])], synthetic_manifest())
        manifest = synthetic_manifest()
        with self.assertRaisesRegex(ValueError, "duplicate manifest"):
            video_metrics(rows, manifest + [dict(manifest[0])])
        rows[0]["model_seed"] = 8
        with self.assertRaisesRegex(ValueError, "unscheduled model_seed"):
            video_metrics(rows, synthetic_manifest())

    def test_reject_relabeling_revisit_denominator_or_reference_outcome(self):
        rows = synthetic_outputs()
        rows[0]["revisit_expected"] = False
        with self.assertRaisesRegex(ValueError, "metadata mismatch"):
            video_metrics(rows, synthetic_manifest())
        rows = synthetic_outputs()
        rows[0]["ref_outcome"] = 0
        with self.assertRaisesRegex(ValueError, "metadata mismatch"):
            video_metrics(rows, synthetic_manifest())

    def test_zero_outputs_keep_entire_schedule_and_return_no_lpips(self):
        result = video_metrics([], synthetic_manifest())
        self.assertEqual(result["n_scheduled_outputs"], 4)
        self.assertEqual(result["outcome_ba_percent"], 0)
        self.assertEqual(result["revisit_accuracy_percent"], 0)
        self.assertFalse(result["coverage_complete"])
        self.assertIsNone(result["lpips5_mean"])


if __name__ == "__main__":
    unittest.main()
