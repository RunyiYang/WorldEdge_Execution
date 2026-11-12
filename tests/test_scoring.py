"""Synthetic reconciliation checks. These fixtures are not experiment results."""

from copy import deepcopy
import unittest

from worldedge_eval.scoring import score_policy, score_video


def policy_schedule(model="synthetic_policy"):
    return [{
        "run_id": f"{model}_run_{seed}", "model_id": model,
        "setting": "manipulation", "world_id": "synthetic_world",
        "source_group_id": "synthetic_source", "seed": seed,
    } for seed in (0, 1)]


def policy_outputs(model="synthetic_policy"):
    rows = [{**item, "status": "completed", "successes": [1] * 10}
            for item in policy_schedule(model)]
    rows[1]["successes"][0] = 0
    return rows


def video_schedule():
    return [{
        "world_id": "synthetic_world", "source_group_id": "synthetic_source",
        "clip_id": f"synthetic_clip_{label}", "ref_outcome": label,
        "revisit_expected": label == 1,
    } for label in (0, 1)]


def video_outputs(model="synthetic_video"):
    return [{
        **clip, "model_id": model, "model_seed": seed,
        "pred_outcome": "success" if clip["ref_outcome"] else "failure",
        "valid_video": True,
        "revisit_correct": True if clip["revisit_expected"] else None,
        "lpips5": 0.1 + seed * 0.2, "lpips30": 0.3 + seed * 0.2,
    } for clip in video_schedule() for seed in (0, 1)]


class PolicyScoringTests(unittest.TestCase):
    def test_complete_schedule_reduces_all_ten_tasks_and_retains_cluster(self):
        result = score_policy(policy_outputs(), policy_schedule(), "synthetic_policy")
        self.assertEqual(result["suite"], "policy")
        self.assertEqual(result["setting"], "manipulation")
        self.assertTrue(result["reportable"])
        self.assertTrue(all(result["metric_reportability"].values()))
        self.assertEqual(result["metrics"]["csr5_percent"], 50)
        self.assertEqual(result["metrics"]["csr10_percent"], 50)
        self.assertEqual(result["metrics"]["completed10_mean"], 9.5)
        self.assertAlmostEqual(result["metrics"]["delayed_reuse_percent"], 500 / 6)
        self.assertEqual(result["n_scheduled_tasks"], 20)
        self.assertEqual(result["n_worlds"], 1)
        self.assertEqual(result["source_group_by_world"], {"synthetic_world": "synthetic_source"})
        self.assertEqual([row["seed"] for row in result["per_run"]], [0, 1])

    def test_physical_policy_termination_is_scored_with_supplied_zero_slots(self):
        rows = policy_outputs()
        rows[1].update(status="terminated_policy", successes=[0] * 10)
        result = score_policy(rows, policy_schedule(), "synthetic_policy")
        self.assertTrue(result["reportable"])
        self.assertEqual(result["metrics"]["completed10_mean"], 5)
        self.assertEqual(result["status_counts"]["terminated_policy"], 1)

    def test_missing_run_makes_entire_row_unreportable(self):
        result = score_policy(policy_outputs()[:1], policy_schedule(), "synthetic_policy")
        self.assertFalse(result["reportable"])
        self.assertFalse(result["coverage_complete"])
        self.assertIsNone(result["metrics"])
        self.assertFalse(any(result["metric_reportability"].values()))
        self.assertEqual(result["n_scheduled_runs"], 2)
        self.assertEqual(result["n_present_runs"], 1)
        self.assertEqual(result["missing_run_ids"], ["synthetic_policy_run_1"])
        self.assertEqual(result["per_run"][1]["status"], "missing")

    def test_infrastructure_failures_accept_partial_or_absent_outcomes_but_never_score(self):
        for partial in (None, [], [1, 0], [0] * 10):
            with self.subTest(partial=partial):
                rows = policy_outputs()
                rows[1].update(status="incomplete_infrastructure", successes=partial)
                result = score_policy(rows, policy_schedule(), "synthetic_policy")
                self.assertTrue(result["coverage_complete"])
                self.assertFalse(result["reportable"])
                self.assertIsNone(result["metrics"])
                self.assertEqual(result["infrastructure_run_ids"], ["synthetic_policy_run_1"])

    def test_duplicate_manifest_or_lifetime_or_output_is_rejected(self):
        schedule = policy_schedule()
        with self.assertRaisesRegex(ValueError, "duplicate manifest run_id"):
            score_policy([], schedule + [schedule[0]], "synthetic_policy")
        with self.assertRaisesRegex(ValueError, "duplicate scheduled lifetime"):
            score_policy([], schedule + [{**schedule[0], "run_id": "different"}], "synthetic_policy")
        rows = policy_outputs()
        with self.assertRaisesRegex(ValueError, "duplicate output run_id"):
            score_policy(rows + [rows[0]], schedule, "synthetic_policy")

    def test_unscheduled_output_and_each_identity_disagreement_are_rejected(self):
        replacements = {
            "run_id": "unknown", "model_id": "typo", "setting": "mobile_manipulation",
            "world_id": "wrong_world", "source_group_id": "wrong_source", "seed": 5,
        }
        for field, value in replacements.items():
            with self.subTest(field=field):
                rows = policy_outputs()
                rows[0][field] = value
                with self.assertRaisesRegex(ValueError, "unscheduled|mismatch"):
                    score_policy(rows, policy_schedule(), "synthetic_policy")

    def test_known_other_model_is_validated_and_excluded(self):
        schedule = policy_schedule() + policy_schedule("other_policy")
        rows = policy_outputs() + policy_outputs("other_policy")
        result = score_policy(rows, schedule, "synthetic_policy")
        self.assertEqual(result["metrics"]["n_lifetimes"], 2)
        rows[-1]["source_group_id"] = "wrong"
        with self.assertRaisesRegex(ValueError, "metadata mismatch"):
            score_policy(rows, schedule, "synthetic_policy")

    def test_mixed_scope_and_inconsistent_source_cluster_are_rejected(self):
        for field in ("setting", "split", "embodiment_id", "pool"):
            with self.subTest(field=field):
                schedule = policy_schedule()
                schedule[0][field], schedule[1][field] = "first", "second"
                with self.assertRaisesRegex(ValueError, f"mixed {field}"):
                    score_policy([], schedule, "synthetic_policy")
        schedule = policy_schedule()
        schedule[1]["source_group_id"] = "conflicting_source"
        with self.assertRaisesRegex(ValueError, "inconsistent source_group_id"):
            score_policy([], schedule, "synthetic_policy")

    def test_optional_metadata_can_be_inherited_but_cannot_override_manifest(self):
        schedule = [{**item, "split": "test"} for item in policy_schedule()]
        result = score_policy(policy_outputs(), schedule, "synthetic_policy")
        self.assertEqual(result["split"], "test")
        rows = policy_outputs()
        rows[0]["split"] = "dev"
        with self.assertRaisesRegex(ValueError, "metadata mismatch"):
            score_policy(rows, schedule, "synthetic_policy")
        with self.assertRaisesRegex(ValueError, "not declared"):
            score_policy(rows, policy_schedule(), "synthetic_policy")

    def test_invalid_outcomes_seed_and_status_are_rejected_without_padding(self):
        for outcomes in ([1] * 9, [1] * 11, [1.0] * 10, [2] * 10, None):
            with self.subTest(outcomes=outcomes):
                rows = policy_outputs()
                rows[0]["successes"] = outcomes
                with self.assertRaises(ValueError):
                    score_policy(rows, policy_schedule(), "synthetic_policy")
        for seed in (True, 0.0, -1):
            with self.subTest(seed=seed):
                rows = policy_outputs()
                rows[0]["seed"] = seed
                with self.assertRaisesRegex(ValueError, "nonnegative integer"):
                    score_policy(rows, policy_schedule(), "synthetic_policy")
        rows = policy_outputs()
        rows[0]["status"] = "success"
        with self.assertRaisesRegex(ValueError, "unsupported policy status"):
            score_policy(rows, policy_schedule(), "synthetic_policy")

    def test_empty_output_stays_unreportable_and_invalid_reuse_is_still_rejected(self):
        result = score_policy([], policy_schedule(), "synthetic_policy")
        self.assertEqual(result["status_counts"]["missing"], 2)
        with self.assertRaisesRegex(ValueError, "duplicate reuse"):
            score_policy([], policy_schedule(), "synthetic_policy", reuse_pairs=((1, 4), (1, 4)))

    def test_inputs_are_not_modified(self):
        rows, schedule = policy_outputs(), policy_schedule()
        before = deepcopy((rows, schedule))
        score_policy(rows, schedule, "synthetic_policy")
        self.assertEqual((rows, schedule), before)


class VideoScoringTests(unittest.TestCase):
    def test_complete_video_schedule_has_four_reportable_cells(self):
        result = score_video(video_outputs(), video_schedule(), "synthetic_video")
        self.assertEqual(result["suite"], "video")
        self.assertTrue(result["reportable"])
        self.assertTrue(all(result["metric_reportability"].values()))
        self.assertEqual(result["metrics"]["outcome_ba_percent"], 100)
        self.assertEqual(result["metrics"]["revisit_accuracy_percent"], 100)
        self.assertAlmostEqual(result["metrics"]["lpips5_mean"], 0.2)
        self.assertAlmostEqual(result["metrics"]["lpips30_mean"], 0.4)
        self.assertEqual(result["metrics"]["n_scheduled_outputs"], 4)
        self.assertTrue(all(clip["source_group_id"] == "synthetic_source"
                            for clip in result["metrics"]["per_clip"]))

    def test_missing_output_keeps_denominator_and_diagnostic_metrics(self):
        result = score_video(video_outputs()[:-1], video_schedule(), "synthetic_video")
        self.assertFalse(result["reportable"])
        self.assertFalse(result["coverage_complete"])
        self.assertFalse(any(result["metric_reportability"].values()))
        self.assertEqual(result["metrics"]["n_scheduled_outputs"], 4)
        self.assertEqual(result["metrics"]["outcome_ba_percent"], 75)
        self.assertEqual(result["metrics"]["revisit_accuracy_percent"], 50)
        self.assertIsNone(result["metrics"]["lpips5_mean"])

    def test_invalid_video_cannot_claim_a_correct_prediction(self):
        rows = video_outputs()
        rows[-1]["valid_video"] = False
        result = score_video(rows, video_schedule(), "synthetic_video")
        self.assertTrue(result["coverage_complete"])
        self.assertFalse(result["reportable"])
        self.assertEqual(result["metrics"]["outcome_ba_percent"], 75)
        self.assertEqual(result["metrics"]["revisit_accuracy_percent"], 50)

    def test_lpips_horizon_completeness_is_independent(self):
        rows = video_outputs()
        rows[0].pop("lpips30")
        result = score_video(rows, video_schedule(), "synthetic_video")
        self.assertFalse(result["reportable"])
        self.assertTrue(result["metric_reportability"]["lpips5_mean"])
        self.assertFalse(result["metric_reportability"]["lpips30_mean"])
        self.assertTrue(result["metric_reportability"]["outcome_ba_percent"])
        self.assertTrue(result["metric_reportability"]["revisit_accuracy_percent"])
        self.assertIsNone(result["metrics"]["lpips30_mean"])

    def test_unknown_annotation_is_an_error_not_an_omitted_example(self):
        rows = video_outputs()
        rows[0]["pred_outcome"] = "unknown"
        rows[-1]["revisit_correct"] = None
        result = score_video(rows, video_schedule(), "synthetic_video")
        self.assertTrue(result["reportable"])
        self.assertEqual(result["metrics"]["outcome_ba_percent"], 75)
        self.assertEqual(result["metrics"]["revisit_accuracy_percent"], 50)

    def test_shared_manifest_rejects_other_models_instead_of_ignoring_typos(self):
        with self.assertRaisesRegex(ValueError, "unknown output model_id"):
            score_video(video_outputs() + video_outputs("typo"), video_schedule(), "synthetic_video")

    def test_model_specific_manifest_validates_and_filters_known_other_models(self):
        schedule = [{**clip, "model_id": model}
                    for model in ("synthetic_video", "other_video") for clip in video_schedule()]
        rows = video_outputs() + video_outputs("other_video")
        result = score_video(rows, schedule, "synthetic_video")
        self.assertTrue(result["reportable"])
        self.assertEqual(result["metrics"]["n_present_outputs"], 4)
        rows[-1]["ref_outcome"] = 0
        with self.assertRaisesRegex(ValueError, "reference metadata mismatch"):
            score_video(rows, schedule, "synthetic_video")
        with self.assertRaisesRegex(ValueError, "unknown output model_id"):
            score_video(video_outputs("typo"), schedule, "synthetic_video")

    def test_ambiguous_model_manifest_and_changed_crossmodel_labels_are_rejected(self):
        schedule = video_schedule()
        schedule[0]["model_id"] = "synthetic_video"
        with self.assertRaisesRegex(ValueError, "every entry or no entries"):
            score_video([], schedule, "synthetic_video")
        schedule = [{**clip, "model_id": model}
                    for model in ("synthetic_video", "other_video") for clip in video_schedule()]
        schedule[-1]["ref_outcome"] = 0
        with self.assertRaisesRegex(ValueError, "differs across models"):
            score_video([], schedule, "synthetic_video")

    def test_duplicates_unscheduled_seed_and_copied_label_disagreements_are_rejected(self):
        rows = video_outputs()
        with self.assertRaisesRegex(ValueError, "duplicate output"):
            score_video(rows + [rows[0]], video_schedule(), "synthetic_video")
        schedule = video_schedule()
        with self.assertRaisesRegex(ValueError, "duplicate manifest clip"):
            score_video([], schedule + [schedule[0]], "synthetic_video")
        for field, value in (("clip_id", "unknown"), ("model_seed", 2), ("ref_outcome", 1)):
            with self.subTest(field=field):
                rows = video_outputs()
                rows[0][field] = value
                with self.assertRaisesRegex(ValueError, "unscheduled|mismatch"):
                    score_video(rows, video_schedule(), "synthetic_video")

    def test_source_groups_are_consistent_and_optional(self):
        schedule = video_schedule()
        schedule[1]["source_group_id"] = "conflict"
        with self.assertRaisesRegex(ValueError, "inconsistent source_group_id"):
            score_video([], schedule, "synthetic_video")
        rows = video_outputs()
        rows[0]["source_group_id"] = "conflict"
        with self.assertRaisesRegex(ValueError, "source_group_id metadata mismatch"):
            score_video(rows, video_schedule(), "synthetic_video")
        schedule = video_schedule()
        for clip in schedule:
            clip.pop("source_group_id")
        rows = video_outputs()
        for row in rows:
            row.pop("source_group_id")
        result = score_video(rows, schedule, "synthetic_video")
        self.assertEqual(result["source_group_by_world"], {"synthetic_world": "synthetic_world"})

    def test_mixed_splits_or_embodiments_are_not_pooled(self):
        for field in ("setting", "split", "embodiment_id", "pool"):
            with self.subTest(field=field):
                schedule = video_schedule()
                schedule[0][field], schedule[1][field] = "first", "second"
                with self.assertRaisesRegex(ValueError, f"mixed {field}"):
                    score_video([], schedule, "synthetic_video")

    def test_missing_class_or_revisit_subset_has_explicit_nonreportable_cell(self):
        schedule = video_schedule()[:1]
        result = score_video(video_outputs()[:2], schedule, "synthetic_video")
        self.assertFalse(result["reportable"])
        self.assertFalse(result["metric_reportability"]["outcome_ba_percent"])
        self.assertFalse(result["metric_reportability"]["revisit_accuracy_percent"])
        self.assertTrue(result["metric_reportability"]["lpips5_mean"])

    def test_invalid_seed_contract_and_empty_manifest_raise(self):
        for seeds in ((), (0, 0), (True, 1), (0, -1), (0.0, 1)):
            with self.subTest(seeds=seeds):
                with self.assertRaisesRegex(ValueError, "model_seeds"):
                    score_video([], video_schedule(), "synthetic_video", model_seeds=seeds)
        with self.assertRaisesRegex(ValueError, "at least one clip"):
            score_video([], [], "synthetic_video")

    def test_inputs_are_not_modified(self):
        rows, schedule = video_outputs(), video_schedule()
        before = deepcopy((rows, schedule))
        score_video(rows, schedule, "synthetic_video")
        self.assertEqual((rows, schedule), before)


if __name__ == "__main__":
    unittest.main()
