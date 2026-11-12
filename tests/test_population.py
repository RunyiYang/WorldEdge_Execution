"""Synthetic checks for configured population and pairing audits."""

from copy import deepcopy
import unittest

from worldedge_eval.population import audit_populations
from worldedge_eval.scoring import score_policy, score_video


def configuration():
    return {
        "policy": {
            "rollout_seeds": [0, 1], "reuse_pairs": [[1, 4], [4, 7], [7, 10]],
            "settings": {
                "manipulation": {"test_worlds": 2, "embodiment_id": "dual_arx_x5",
                                 "model_ids": ["policy_a", "policy_b"]},
                "mobile_manipulation": {"test_worlds": 2, "embodiment_id": "lift2_r5a",
                                        "model_ids": ["policy_mobile"]},
            },
        },
        "video_world_models": {
            "primary_setting": "manipulation", "embodiment_id": "dual_arx_x5",
            "generation_seeds": [0, 1],
            "dataset": {"clips_per_world": 4, "pair_counts_per_world": {"delayed_revisit": 1}},
        },
        "splits": {"wm_test_worlds": 2, "wm_test_reuses_policy_manipulation_test_worlds": True},
    }


def policy_score(model="policy_a", worlds=2, seeds=(0, 1), prefix="world", missing=False):
    mobile = model == "policy_mobile"
    manifest = [{
        "run_id": f"{model}_{world}_{seed}", "model_id": model,
        "setting": "mobile_manipulation" if mobile else "manipulation",
        "embodiment_id": "lift2_r5a" if mobile else "dual_arx_x5", "split": "test",
        "world_id": f"{prefix}_{world}", "source_group_id": f"{prefix}_source_{world}",
        "seed": seed,
    } for world in range(worlds) for seed in seeds]
    records = [{**item, "status": "completed", "successes": [1] * 10} for item in manifest]
    return score_policy(records[:-1] if missing else records, manifest, model)


def video_score(model="video_a", worlds=2, clips=4, prefix="world", clip_prefix="clip", missing=False):
    manifest = [{
        "world_id": f"{prefix}_{world}", "source_group_id": f"{prefix}_source_{world}",
        "clip_id": f"{clip_prefix}_{clip}", "ref_outcome": clip % 2,
        "revisit_expected": clip < clips // 2,
        "setting": "manipulation", "embodiment_id": "dual_arx_x5", "split": "test",
    } for world in range(worlds) for clip in range(clips)]
    records = [{
        **item, "model_id": model, "model_seed": seed, "valid_video": True,
        "pred_outcome": "success" if item["ref_outcome"] else "failure",
        "revisit_correct": True if item["revisit_expected"] else None,
        "lpips5": 0.1, "lpips30": 0.2,
    } for item in manifest for seed in (0, 1)]
    return score_video(records[:-1] if missing else records, manifest, model)


class PopulationAuditTests(unittest.TestCase):
    def test_paired_configured_populations_are_accepted(self):
        result = audit_populations(configuration(),
            [policy_score(), policy_score("policy_b"), policy_score("policy_mobile", prefix="mobile")],
            [video_score(), video_score("video_b")])
        self.assertTrue(all(not messages for messages in result.values()), result)

    def test_same_total_runs_cannot_replace_worlds_with_extra_seeds(self):
        score = policy_score(worlds=1, seeds=(0, 1, 2, 3))
        self.assertEqual(score["metrics"]["n_lifetimes"], 4)
        messages = audit_populations(configuration(), [score], [])["policy_a"]
        self.assertTrue(any("distinct worlds" in message for message in messages))
        self.assertTrue(any("rollout seed exactly once" in message for message in messages))

    def test_wrong_seed_values_are_rejected_even_when_world_and_run_counts_match(self):
        messages = audit_populations(configuration(), [policy_score(seeds=(2, 3))], [])["policy_a"]
        self.assertTrue(any("rollout seed exactly once" in message for message in messages))

    def test_video_global_totals_cannot_replace_worlds_with_extra_clips(self):
        score = video_score(worlds=1, clips=8)
        self.assertEqual(score["metrics"]["n_clips"], 8)
        self.assertEqual(score["metrics"]["n_revisit_clips"], 4)
        messages = audit_populations(configuration(), [], [score])["video_a"]
        self.assertTrue(any("distinct worlds" in message for message in messages))
        self.assertTrue(any("expected 4 reference clips" in message for message in messages))
        self.assertTrue(any("expected 2 revisit clips" in message for message in messages))

    def test_video_world_balance_is_checked_beneath_balanced_global_totals(self):
        score = video_score()
        for clip in score["metrics"]["per_clip"]:
            clip["ref_outcome"] = int(clip["world_id"] == "world_1")
        messages = audit_populations(configuration(), [], [score])["video_a"]
        self.assertTrue(any("balanced within the world" in message for message in messages))

    def test_repeated_source_groups_do_not_count_as_independent_worlds(self):
        score = policy_score()
        for run in score["per_run"]:
            run["source_group_id"] = "same_source"
        score["source_group_by_world"] = {world: "same_source" for world in score["source_group_by_world"]}
        score["n_source_groups"] = 1
        messages = audit_populations(configuration(), [score], [])["policy_a"]
        self.assertTrue(any("independent source groups" in message for message in messages))

    def test_policy_pairing_mismatch_flags_both_models(self):
        result = audit_populations(configuration(), [policy_score(), policy_score("policy_b", prefix="other")], [])
        self.assertTrue(all(any("Paired policy" in issue for issue in result[model])
                            for model in ("policy_a", "policy_b")))

    def test_video_clip_identity_mismatch_flags_both_models(self):
        result = audit_populations(configuration(), [], [video_score(), video_score("video_b", clip_prefix="other")])
        self.assertTrue(all(any("clip identities/reference labels" in issue for issue in result[model])
                            for model in ("video_a", "video_b")))

    def test_video_reference_label_mismatch_flags_both_models(self):
        first, second = video_score(), video_score("video_b")
        for clip in second["metrics"]["per_clip"]:
            clip["ref_outcome"] = 1 - clip["ref_outcome"]
        result = audit_populations(configuration(), [], [first, second])
        self.assertTrue(all(any("clip identities/reference labels" in issue for issue in result[model])
                            for model in ("video_a", "video_b")))

    def test_shared_policy_video_world_requirement_is_configured(self):
        config = configuration()
        policy, video = policy_score(), video_score(prefix="other")
        result = audit_populations(config, [policy], [video])
        self.assertTrue(all(any("Shared manipulation/video" in issue for issue in result[model])
                            for model in ("policy_a", "video_a")))
        config["splits"]["wm_test_reuses_policy_manipulation_test_worlds"] = False
        self.assertEqual(audit_populations(config, [policy], [video]), {"policy_a": [], "video_a": []})

    def test_explicit_wrong_scope_and_reuse_definition_are_rejected(self):
        policy, video = policy_score(), video_score()
        policy["split"] = "dev"
        policy["reuse_pairs"] = [[2, 5]]
        policy["metrics"]["reuse_pairs"] = [[2, 5]]
        video["embodiment_id"] = "native_other_robot"
        video["setting"] = "mobile_manipulation"
        result = audit_populations(configuration(), [policy], [video])
        self.assertTrue(any("split" in issue for issue in result["policy_a"]))
        self.assertTrue(any("Reuse pairs" in issue for issue in result["policy_a"]))
        self.assertTrue(any("Metric reuse pairs" in issue for issue in result["policy_a"]))
        self.assertTrue(any("embodiment_id" in issue for issue in result["video_a"]))
        self.assertTrue(any("setting" in issue for issue in result["video_a"]))

    def test_incomplete_outputs_still_have_auditable_scheduled_populations(self):
        policy, video = policy_score(missing=True), video_score(missing=True)
        self.assertFalse(policy["reportable"])
        self.assertFalse(video["reportable"])
        self.assertEqual(audit_populations(configuration(), [policy], [video]),
                         {"policy_a": [], "video_a": []})

    def test_missing_or_malformed_detail_is_an_issue_not_a_crash(self):
        for value in (None, "not_a_list", [None], [{"world_id": [], "source_group_id": {}}]):
            with self.subTest(value=value):
                policy, video = policy_score(), video_score()
                policy["per_run"] = value
                video["metrics"]["per_clip"] = value
                result = audit_populations(configuration(), [policy], [video])
                self.assertTrue(result["policy_a"])
                self.assertTrue(result["video_a"])
        result = audit_populations(configuration(), [], [{"model_id": "video_a", "metrics": None}])
        self.assertTrue(result["video_a"])

    def test_duplicate_clip_and_inconsistent_declared_map_are_rejected(self):
        score = video_score()
        score["metrics"]["per_clip"][1]["clip_id"] = score["metrics"]["per_clip"][0]["clip_id"]
        score["source_group_by_world"] = {}
        messages = audit_populations(configuration(), [], [score])["video_a"]
        self.assertTrue(any("duplicate world/clip" in issue for issue in messages))
        self.assertTrue(any("source_group_by_world disagrees" in issue for issue in messages))

    def test_inputs_are_not_modified(self):
        config, policies, videos = configuration(), [policy_score()], [video_score()]
        before = deepcopy((config, policies, videos))
        audit_populations(config, policies, videos)
        self.assertEqual((config, policies, videos), before)


if __name__ == "__main__":
    unittest.main()
