"""Configuration/schedule contracts only; no backend or experiment is exercised."""

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from worldedge_eval.config import load_config, plan, preflight, validate_config


CONFIG = Path(__file__).resolve().parents[1] / "configs" / "experiment.yaml"


def set_path(config, path, value):
    keys = path.split(".")
    target = config
    for key in keys[:-1]:
        target = target[key]
    target[keys[-1]] = value


class ConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = load_config(CONFIG)

    def setUp(self):
        self.config = deepcopy(self.source)

    def test_proposed_config_valid_but_null_manifests_are_unresolved(self):
        self.assertEqual(validate_config(self.config), [])
        result = preflight(self.config)
        self.assertTrue(result["structurally_valid"])
        self.assertFalse(result["configuration_complete"])
        self.assertIn("policy.checkpoint_manifest", result["unresolved_fields"])
        self.assertIn("No simulator", result["readiness_note"])
        self.assertNotIn("ready", result)

    def test_derived_default_counts(self):
        result = plan(self.config)
        self.assertEqual(result["policy"]["total_lifetimes"], 540)
        self.assertEqual(result["policy"]["total_scheduled_tasks"], 5400)
        self.assertEqual(result["policy"]["max_simulated_hours"], 300)
        video = result["video_world_models"]
        self.assertEqual(video["reference_clips"], {"train": 3200, "dev": 400, "test": 600})
        self.assertEqual(video["predicted_test_videos_per_model"], 1200)
        self.assertEqual(video["primary_predicted_test_videos"], 2400)
        self.assertEqual(result["rooms"]["policy_test"], 330)
        self.assertEqual(result["rooms"]["accepted_total"], 590)

    def test_count_changes_are_derived_not_literal_constants(self):
        self.config["policy"]["rollout_seeds"] = [0, 1, 2]
        self.config["video_world_models"]["optional_models_enabled"] = True
        result = plan(self.config)
        self.assertEqual(result["policy"]["total_lifetimes"], 810)
        self.assertEqual(result["policy"]["max_simulated_hours"], 450)
        self.assertEqual(result["video_world_models"]["enabled_optional_predicted_test_videos"], 1200)
        self.assertEqual(result["video_world_models"]["total_predicted_test_videos"], 3600)
        self.assertEqual(result["rooms"]["accepted_total"], 590)

    def test_scalar_and_list_yaml_roots_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.yaml"
            for text in ("true", "17", "null", "- one\n- two\n"):
                path.write_text(text)
                with self.subTest(text=text), self.assertRaisesRegex(ValueError, "root must be a mapping"):
                    load_config(path)
        for value in (None, True, 17, [], "config"):
            with self.subTest(value=value):
                self.assertTrue(validate_config(value))
                with self.assertRaises(ValueError):
                    plan(value)

    def test_boolean_nonnumeric_and_nonfinite_numbers_are_invalid(self):
        cases = [("splits.wm_train_worlds", True), ("splits.wm_train_worlds", 1.5),
                 ("policy.rounds_per_lifetime", "10"),
                 ("video_world_models.clip_duration_s", False),
                 ("video_world_models.clip_duration_s", "30"),
                 ("video_world_models.video_fps", float("nan")),
                 ("video_world_models.collector.command_hold_s", float("inf")),
                 ("video_world_models.dataset.clips_per_world", 0)]
        for path, value in cases:
            config = deepcopy(self.source)
            set_path(config, path, value)
            with self.subTest(path=path, value=value):
                self.assertTrue(validate_config(config))

    def test_invalid_seed_sequences(self):
        for path in ("policy.rollout_seeds", "video_world_models.generation_seeds"):
            for seeds in ([], [0, 0], [False, 1], [0, 1.0], [0, -1], "0,1", [{}]):
                config = deepcopy(self.source)
                set_path(config, path, seeds)
                with self.subTest(path=path, seeds=seeds):
                    self.assertTrue(validate_config(config))

    def test_inconsistent_time_frame_chunk_and_substep_schedules(self):
        cases = [("video_world_models.clip_duration_s", -30),
                 ("video_world_models.frames_including_initial", 300),
                 ("video_world_models.inference.chunks", 24),
                 ("video_world_models.collector.physics_steps_per_command", 10),
                 ("video_world_models.collector.command_hold_s", 0.2),
                 ("video_world_models.scored_frame_indices", [50, 299])]
        for path, value in cases:
            config = deepcopy(self.source)
            set_path(config, path, value)
            with self.subTest(path=path):
                self.assertTrue(validate_config(config))

    def test_invalid_family_and_pair_category_counts(self):
        self.config["policy"]["task_families"][0]["test_worlds"] = 9
        self.assertTrue(validate_config(self.config))
        for value in (2, True, "3", -1):
            config = deepcopy(self.source)
            config["video_world_models"]["dataset"]["pair_counts_per_world"]["placement"] = value
            with self.subTest(value=value):
                self.assertTrue(validate_config(config))

    def test_ground_truth_conditioning_is_rejected(self):
        self.config["video_world_models"]["future_realized_states_as_input"] = "allowed"
        errors = validate_config(self.config)
        self.assertTrue(any("future_realized_states_as_input" in error for error in errors))

    def test_disabled_scope_nulls_do_not_block_primary_configuration(self):
        self.config["adaptive_demo"]["runtime_manifest"] = None
        self.config["video_world_models"]["mobile_extension_manifest"] = None
        self.config["video_world_models"]["model_manifests"] = {
            "dreamdojo_14b": {"checkpoint": None},
            "dreamdojo_2b": {"checkpoint": None},
        }
        result = preflight(self.config)
        self.assertIn("adaptive_demo.runtime_manifest", result["ignored_disabled_null_fields"])
        self.assertIn("video_world_models.mobile_extension_manifest", result["ignored_disabled_null_fields"])
        optional_path = "video_world_models.model_manifests.dreamdojo_14b.checkpoint"
        self.assertIn(optional_path, result["ignored_disabled_null_fields"])
        self.assertNotIn(optional_path, result["unresolved_fields"])
        self.assertIn("video_world_models.model_manifests.dreamdojo_2b.checkpoint", result["unresolved_fields"])
        self.config["video_world_models"]["optional_models_enabled"] = True
        self.assertIn(optional_path, preflight(self.config)["unresolved_fields"])

    def test_nested_missing_sections_return_errors_not_tracebacks(self):
        for section in ("policy", "video_world_models", "splits"):
            config = deepcopy(self.source)
            config[section] = "invalid"
            with self.subTest(section=section):
                self.assertTrue(validate_config(config))
                self.assertFalse(preflight(config)["structurally_valid"])

    def test_unregistered_setting_cannot_silently_change_room_plan(self):
        self.config["policy"]["settings"]["unknown_setting"] = True
        self.assertTrue(validate_config(self.config))
        with self.assertRaises(ValueError):
            plan(self.config)

    def test_checkpoint_schedule_cannot_exceed_declared_training_budget(self):
        self.config["video_world_models"]["training"]["checkpoints_at_updates"] = [5000, 25000]
        self.assertTrue(validate_config(self.config))

    def test_reporter_category_keys_are_required_even_when_totals_match(self):
        categories = self.config["video_world_models"]["dataset"]["pair_counts_per_world"]
        categories["renamed_revisit"] = categories.pop("delayed_revisit")
        errors = validate_config(self.config)
        self.assertTrue(any("require exactly placement" in error for error in errors))
        with self.assertRaises(ValueError):
            plan(self.config)

    def test_protocol_identity_and_embodiments_cannot_be_empty_or_changed(self):
        cases = [("protocol.id", " "), ("protocol.id", 7),
                 ("policy.settings.manipulation.embodiment_id", "panda"),
                 ("policy.settings.mobile_manipulation.embodiment_id", "dual_arx_x5"),
                 ("video_world_models.embodiment_id", "lift2_r5a")]
        for path, value in cases:
            config = deepcopy(self.source)
            set_path(config, path, value)
            with self.subTest(path=path, value=value):
                self.assertTrue(validate_config(config))

    def test_policy_model_ids_are_unique_across_blocks(self):
        settings = self.config["policy"]["settings"]
        settings["mobile_manipulation"]["model_ids"][0] = settings["manipulation"]["model_ids"][0]
        self.assertTrue(any("unique across embodiment blocks" in error for error in validate_config(self.config)))

    def test_deleting_all_null_evidence_fields_does_not_complete_configuration(self):
        required = preflight(self.config)["unresolved_fields"]
        for path in required:
            keys = path.split(".")
            target = self.config
            for key in keys[:-1]:
                target = target[key]
            del target[keys[-1]]
        result = preflight(self.config)
        self.assertFalse(result["configuration_complete"])
        self.assertEqual(set(result["unresolved_fields"]), set(required))


if __name__ == "__main__":
    unittest.main()
