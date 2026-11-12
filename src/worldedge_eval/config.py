"""Configuration checks and derived schedules, never backend readiness checks."""

from __future__ import annotations

import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml


READINESS_NOTE = (
    "Configuration checks only. No simulator, checkpoint, action adapter, "
    "physical feasibility, or completed experiment is verified."
)
REQUIRED_EVIDENCE_FIELDS = (
    "policy.checkpoint_manifest", "policy.thresholds_frozen_manifest",
    "policy.settings.manipulation.runtime_action_and_sensor_contract",
    "policy.settings.mobile_manipulation.runtime_action_and_sensor_contract",
    "provenance.evaluated_source_lock", "splits.split_manifest_sha256",
    "video_world_models.camera.calibrated_camera_manifest", "video_world_models.checkpoint_manifest",
    "video_world_models.collector.action_contract", "video_world_models.collector.action_dimension",
    "video_world_models.dataset.immutable_pair_manifest_sha256",
    "video_world_models.inference.denoising_and_guidance_manifest",
    "video_world_models.scoring.judge_manifest", "video_world_models.training.hardware_and_microbatch_manifest",
    "video_world_models.training.selection_subset_manifest_sha256", "worlds.accepted_world_manifest_sha256",
    "worlds.admission_reference_controller_manifest", "worlds.physical_asset_bounds",
    "worlds.scene_compilation.growth_runtime_mode_manifest",
)


def load_config(path: str | Path) -> dict:
    """Read safe YAML. Reject scalar/list roots; leave null manifests unresolved."""
    try:
        config = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML: {exc}") from exc
    if not isinstance(config, dict):
        raise ValueError("Configuration root must be a mapping")
    return config


def _get(config: Any, path: str) -> Any:
    value = config
    for key in path.split("."):
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value


class _Checks:
    def __init__(self, config: dict):
        self.config, self.errors = config, []

    def check(self, condition: bool, message: str) -> None:
        if not condition:
            self.errors.append(message)

    def number(self, path: str, *, integer: bool = False, zero: bool = False):
        value = _get(self.config, path)
        valid_type = type(value) is int if integer else type(value) in (int, float)
        try:
            valid = valid_type and math.isfinite(value) and (value >= 0 if zero else value > 0)
        except OverflowError:
            valid = False
        self.check(valid, f"{path}: expected {'nonnegative' if zero else 'positive'} "
                   f"{'integer' if integer else 'finite number'} (not boolean)")
        return value if valid else None

    def equal(self, path: str, expected: Any) -> None:
        value = _get(self.config, path)
        ok = value == expected and (type(value) is type(expected) if type(expected) in (bool, int) else True)
        self.check(ok, f"{path}: must be {expected!r}")

    def strings(self, path: str, *, empty: bool = False) -> list:
        value = _get(self.config, path)
        ok = isinstance(value, list) and (empty or bool(value))
        ok = ok and all(isinstance(x, str) and x.strip() for x in value)
        ok = ok and len(set(value)) == len(value)
        self.check(ok, f"{path}: expected a list of distinct nonempty strings")
        return value if ok else []

    def seeds(self, path: str) -> list:
        value = _get(self.config, path)
        ok = isinstance(value, list) and bool(value)
        ok = ok and all(type(x) is int and x >= 0 for x in value)
        ok = ok and len(set(value)) == len(value)
        self.check(ok, f"{path}: expected distinct nonnegative integer seeds (not booleans)")
        return value if ok else []


def validate_config(config: dict) -> list[str]:
    """Return structural/scientific errors. Null evidence manifests are not errors."""
    if not isinstance(config, dict):
        return ["Configuration root must be a mapping"]
    c = _Checks(config)
    for section in ("protocol", "provenance", "splits", "worlds", "policy",
                    "video_world_models", "statistics", "adaptive_demo", "gates"):
        c.check(isinstance(config.get(section), Mapping), f"{section}: expected a mapping")
    protocol_id = _get(config, "protocol.id")
    c.check(isinstance(protocol_id, str) and bool(protocol_id.strip()), "protocol.id: expected a nonempty string")
    split_keys = ("policy_dev_worlds_per_setting", "policy_dev_smoke_worlds_per_setting",
                  "policy_dev_pilot_worlds_per_setting", "policy_test_worlds_per_setting",
                  "wm_train_worlds", "wm_dev_worlds", "wm_test_worlds")
    counts = {key: c.number(f"splits.{key}", integer=True) for key in split_keys}
    if all(counts[k] is not None for k in split_keys[:3]):
        c.check(counts[split_keys[0]] == counts[split_keys[1]] + counts[split_keys[2]],
                "splits: development worlds must equal smoke plus pilot worlds")
    for flag in ("wm_test_reuses_policy_manipulation_test_worlds", "policy_manipulation_dev_is_subset_of_wm_dev"):
        c.check(type(_get(config, f"splits.{flag}")) is bool, f"splits.{flag}: expected boolean")
    c.number("worlds.generation_max_attempts_per_bundle_slot", integer=True)
    rounds = c.number("policy.rounds_per_lifetime", integer=True)
    c.check(rounds == 10, "policy.rounds_per_lifetime: this protocol requires 10 rounds")
    c.seeds("policy.rollout_seeds")
    c.equal("policy.chain_success_prefixes", [5, 10])
    dwell = c.number("policy.success_dwell_s")
    c.number("policy.inference_service_timeout_wall_s")
    c.number("policy.infrastructure_deterministic_retries", integer=True, zero=True)
    settings = _get(config, "policy.settings")
    c.check(isinstance(settings, Mapping) and set(settings) == {"manipulation", "mobile_manipulation"},
            "policy.settings: this protocol requires exactly manipulation and mobile_manipulation")
    families = _get(config, "policy.task_families")
    valid_families = isinstance(families, list) and bool(families)
    valid_families = valid_families and all(isinstance(f, Mapping) and isinstance(f.get("id"), str)
        and f["id"].strip() and type(f.get("test_worlds")) is int and f["test_worlds"] > 0 for f in families)
    c.check(valid_families, "policy.task_families: expected named families with positive integer counts")
    if valid_families:
        c.check(len({f["id"] for f in families}) == len(families), "policy.task_families: duplicate family id")
        c.check(sum(f["test_worlds"] for f in families) == counts["policy_test_worlds_per_setting"],
                "policy.task_families: counts must sum to test worlds per setting")
    pairs = _get(config, "policy.reuse_pairs")
    valid_pairs = isinstance(pairs, list) and bool(pairs) and all(isinstance(p, list) and len(p) == 2
        and all(type(n) is int for n in p) and 1 <= p[0] < p[1] <= 10 for p in pairs)
    c.check(valid_pairs, "policy.reuse_pairs: require one-based integer pairs 1 <= anchor < reuse <= 10")
    if valid_pairs:
        c.check(len({tuple(p) for p in pairs}) == len(pairs), "policy.reuse_pairs: duplicate pair")
    policy_model_ids = []
    for setting, room_count in (("manipulation", 1), ("mobile_manipulation", 10)):
        base = f"policy.settings.{setting}"
        worlds = c.number(base + ".test_worlds", integer=True)
        rooms = c.number(base + ".rooms_per_world", integer=True)
        c.check(worlds == counts["policy_test_worlds_per_setting"], f"{base}.test_worlds: inconsistent with splits")
        c.check(rooms == room_count, f"{base}.rooms_per_world: must equal {room_count}")
        deadline = c.number(base + ".deadline_per_task_sim_s")
        if deadline is not None and dwell is not None:
            c.check(deadline >= dwell, f"{base}: deadline must include the success dwell")
        physics = c.number(base + ".provisional_physics_hz")
        control = c.number(base + ".provisional_control_hz")
        if physics is not None and control is not None:
            c.check(control <= physics, f"{base}: control frequency exceeds physics frequency")
        policy_model_ids.extend(c.strings(base + ".model_ids"))
        c.equal(base + ".embodiment_id", "dual_arx_x5" if setting == "manipulation" else "lift2_r5a")
    c.check(len(policy_model_ids) == len(set(policy_model_ids)), "policy.settings: model_ids must be unique across embodiment blocks")
    c.equal("policy.settings.mobile_manipulation.append_one_room_before_rounds", list(range(2, 11)))
    c.equal("policy.settings.mobile_manipulation.seed_room_is_round_one", True)
    c.equal("policy.settings.mobile_manipulation.each_round_uses_its_new_room", True)
    v = "video_world_models."
    c.equal(v + "primary_setting", "manipulation")
    c.equal(v + "embodiment_id", "dual_arx_x5")
    c.equal(v + "mobile_extension_enabled", False)
    primary = c.strings(v + "primary_models")
    optional_enabled = _get(config, v + "optional_models_enabled")
    c.check(type(optional_enabled) is bool, v + "optional_models_enabled: expected boolean")
    optional = c.strings(v + "optional_models", empty=not optional_enabled) if (
        optional_enabled or _get(config, v + "optional_models") is not None) else []
    c.check(not set(primary).intersection(optional), v + "optional_models: duplicates primary model ids")
    c.seeds(v + "generation_seeds")
    duration, fps = c.number(v + "clip_duration_s"), c.number(v + "video_fps")
    frames = c.number(v + "frames_including_initial", integer=True)
    new = c.number(v + "inference.new_frames_per_chunk", integer=True)
    chunk_frames = c.number(v + "inference.frames_per_chunk", integer=True)
    chunks = c.number(v + "inference.chunks", integer=True)
    if duration is not None and fps is not None and frames is not None:
        c.check(math.isclose(duration * fps + 1, frames, abs_tol=1e-8), v + "frames_including_initial: duration * fps + 1 mismatch")
    if None not in (new, chunk_frames, chunks, frames):
        c.check(chunk_frames == new + 1 and chunks * new + 1 == frames, v + "inference: chunk/frame schedule is inconsistent")
    indices = _get(config, v + "scored_frame_indices")
    valid_indices = isinstance(indices, list) and len(indices) == 2 and all(type(i) is int for i in indices)
    c.check(valid_indices, v + "scored_frame_indices: require two integer frame indices")
    if valid_indices and fps is not None and frames is not None:
        c.check(indices == [5 * fps, 30 * fps] and all(0 <= i < frames for i in indices), v + "scored_frame_indices: must address 5 s and 30 s within the clip")
    hz, hold = c.number(v + "collector.command_hz"), c.number(v + "collector.command_hold_s")
    physics = c.number(v + "collector.physics_hz")
    substeps = c.number(v + "collector.physics_steps_per_command", integer=True)
    if None not in (hz, hold, physics, substeps, fps):
        c.check(math.isclose(hz * hold, 1) and math.isclose(hz, fps)
                and math.isclose(physics * hold, substeps), v + "collector: rates, hold duration, and physics substeps disagree")
    if _get(config, v + "collector.action_dimension") is not None:
        c.number(v + "collector.action_dimension", integer=True)
    clips = c.number(v + "dataset.clips_per_world", integer=True)
    branches = c.number(v + "dataset.paired_branches_per_world", integer=True)
    categories = _get(config, v + "dataset.pair_counts_per_world")
    valid_categories = isinstance(categories, Mapping) and bool(categories) and all(type(n) is int and n > 0 for n in categories.values())
    c.check(valid_categories, v + "dataset.pair_counts_per_world: expected positive integer category counts")
    if clips is not None and branches is not None:
        c.check(clips == 2 * branches, v + "dataset: clips must equal two branches per pair")
    if valid_categories:
        c.check(set(categories) == {"placement", "sorting", "multiobject_ordering", "delayed_revisit"},
                v + "dataset.pair_counts_per_world: require exactly placement, sorting, multiobject_ordering, delayed_revisit")
        c.check(sum(categories.values()) == branches, v + "dataset: category counts must sum to the number of pairs")
    if _get(config, "splits.wm_test_reuses_policy_manipulation_test_worlds") is True:
        c.check(counts["wm_test_worlds"] == counts["policy_test_worlds_per_setting"], "splits: shared WM/policy test world counts differ")
    if _get(config, "splits.policy_manipulation_dev_is_subset_of_wm_dev") is True and None not in (counts["policy_dev_worlds_per_setting"], counts["wm_dev_worlds"]):
        c.check(counts["policy_dev_worlds_per_setting"] <= counts["wm_dev_worlds"], "splits: policy development subset exceeds WM development population")
    for key in ("render_height", "render_width", "training.updates", "training.effective_batch_size",
                "training.frames_per_sample", "training.future_frames_per_sample", "training.selection_dev_clips",
                "scoring.lpips_height", "scoring.lpips_width", "scoring.judge_calibration_dev_clips"):
        c.number(v + key, integer=True)
    for key in ("training.seed", "training.warmup_updates", "training.selection_generation_seed",
                "inference.infrastructure_deterministic_retries"):
        c.number(v + key, integer=True, zero=True)
    for key in ("training.learning_rate", "training.final_learning_rate", "training.optimizer_epsilon",
                "training.gradient_clip_norm", "dataset.goal_dwell_at_endpoint_s"):
        c.number(v + key)
    c.number(v + "training.weight_decay", zero=True)
    updates, warmup = _get(config, v + "training.updates"), _get(config, v + "training.warmup_updates")
    checkpoints = _get(config, v + "training.checkpoints_at_updates")
    if type(updates) is int and type(warmup) is int:
        c.check(warmup < updates, v + "training.warmup_updates: must be less than total updates")
    valid_checkpoints = isinstance(checkpoints, list) and bool(checkpoints) and all(type(n) is int and n > 0 for n in checkpoints)
    c.check(valid_checkpoints, v + "training.checkpoints_at_updates: expected positive integer updates")
    if valid_checkpoints and type(updates) is int:
        c.check(checkpoints == sorted(set(checkpoints)) and checkpoints[-1] == updates,
                v + "training.checkpoints_at_updates: must be unique, ordered, and end at total updates")
    train_frames = _get(config, v + "training.frames_per_sample")
    train_future = _get(config, v + "training.future_frames_per_sample")
    if type(train_frames) is int and type(train_future) is int:
        c.check(train_frames == train_future + 1 == chunk_frames, v + "training: sample and inference frame counts disagree")
    selected = _get(config, v + "training.selection_dev_clips")
    if type(selected) is int and clips is not None and counts["wm_dev_worlds"] is not None:
        c.check(selected <= clips * counts["wm_dev_worlds"], v + "training.selection_dev_clips: exceeds development population")
    c.number("statistics.bootstrap_resamples", integer=True)
    confidence = c.number("statistics.confidence_level")
    if confidence is not None:
        c.check(confidence < 1, "statistics.confidence_level: must be less than 1")
    demo_enabled = _get(config, "adaptive_demo.enabled")
    c.check(type(demo_enabled) is bool, "adaptive_demo.enabled: expected boolean")
    if demo_enabled is True:
        c.number("adaptive_demo.worlds", integer=True)
        c.number("adaptive_demo.max_rounds_per_world", integer=True)
    expected = {
        "protocol.test_driven_tuning": "forbidden", "worlds.policy_independent_admission": True,
        "worlds.immutable_test_task_schedule": True, "policy.training_on_worldedge": False,
        "worlds.scene_compilation.existing_entities_unchanged_during_append": True,
        "policy.physical_reset_between_tasks": False, "policy.continue_after_task_failure": True,
        "policy.success_source": "independent_simulator_state_and_trace",
        "policy.privileged_policy_observations": "forbidden", "policy.unreached_tasks_score": 0,
        "statistics.unit": "independent_world_group", v + "common_initial_input": ["rgb_frame_0"],
        v + "fixed_text_prompt": "", v + "native_caption_and_goal_text_conditioning": "forbidden",
        v + "future_input": "issued_controls", v + "future_realized_states_as_input": "forbidden",
        v + "future_video_latent_actions_as_input": "forbidden", v + "future_ground_truth_image_refresh": "forbidden",
        v + "room_insertion_inside_scored_clip": "forbidden", v + "camera.same_camera_for_all_models": True,
        v + "target_embodiment_posttraining_required": True,
        v + "collector.command_normalization_statistics_split": "train_only",
        v + "collector.reuse_policy_video_after_downsampling_controls": "forbidden",
        v + "collector.relative_increment_application": "once_per_interval_then_hold_resolved_target",
        v + "inference.append_initial_frame_once": True, v + "inference.best_of_n_selection": "forbidden",
        v + "inference.source_of_continuation": "generated_frames_and_native_generated_memory",
        v + "dataset.balanced_success_failure": True, v + "training.test_access_during_selection": "forbidden",
        v + "dataset.stage_goal_initially_false": True, v + "scoring.outcome": "balanced_accuracy",
        v + "scoring.seed_aggregation": "average_within_clip",
        v + "scoring.unknown_outcome": "incorrect_for_both_classes",
    }
    for path, value in expected.items():
        c.equal(path, value)
    return c.errors


def plan(config: dict) -> dict:
    """Derive the primary schedule; raise ValueError if configuration is invalid."""
    errors = validate_config(config)
    if errors:
        raise ValueError("Invalid configuration:\n" + "\n".join(errors))
    p, v, splits = config["policy"], config["video_world_models"], config["splits"]
    setting_plans = {}
    for name in ("manipulation", "mobile_manipulation"):
        setting = p["settings"][name]
        lifetimes = len(setting["model_ids"]) * setting["test_worlds"] * len(p["rollout_seeds"])
        tasks = lifetimes * p["rounds_per_lifetime"]
        setting_plans[name] = {"model_count": len(setting["model_ids"]), "lifetimes": lifetimes,
            "scheduled_tasks": tasks, "max_simulated_hours": tasks * setting["deadline_per_task_sim_s"] / 3600}
    references = {split: splits[f"wm_{split}_worlds"] * v["dataset"]["clips_per_world"] for split in ("train", "dev", "test")}
    predictions_per_model = references["test"] * len(v["generation_seeds"])
    optional_count = len(v["optional_models"]) if v["optional_models_enabled"] else 0
    rooms = {"policy_test": sum(s["test_worlds"] * s["rooms_per_world"] for s in p["settings"].values()),
             "wm_train_dev_additional": splits["wm_train_worlds"] + splits["wm_dev_worlds"],
             "wm_test_additional": 0 if splits["wm_test_reuses_policy_manipulation_test_worlds"] else splits["wm_test_worlds"]}
    rooms["policy_dev_additional"] = sum(splits["policy_dev_worlds_per_setting"] * setting["rooms_per_world"]
        for name, setting in p["settings"].items() if name != "manipulation" or not splits["policy_manipulation_dev_is_subset_of_wm_dev"])
    rooms["accepted_total"] = sum(rooms.values())
    return {"protocol_id": config["protocol"].get("id"), "readiness_note": READINESS_NOTE,
        "policy": {"settings": setting_plans, "total_lifetimes": sum(s["lifetimes"] for s in setting_plans.values()),
                   "total_scheduled_tasks": sum(s["scheduled_tasks"] for s in setting_plans.values()),
                   "max_simulated_hours": sum(s["max_simulated_hours"] for s in setting_plans.values())},
        "video_world_models": {"reference_clips": references, "predicted_test_videos_per_model": predictions_per_model,
            "primary_predicted_test_videos": predictions_per_model * len(v["primary_models"]),
            "enabled_optional_predicted_test_videos": predictions_per_model * optional_count,
            "total_predicted_test_videos": predictions_per_model * (len(v["primary_models"]) + optional_count)},
        "rooms": rooms}


def preflight(config: dict) -> dict:
    """Check configuration and active null fields without claiming physical readiness."""
    errors = validate_config(config)
    unresolved, ignored = [], []
    optional = _get(config, "video_world_models.optional_models")
    optional_ids = set(optional) if isinstance(optional, list) and all(isinstance(x, str) for x in optional) else set()

    def walk(value, parts=(), path="", inactive=False):
        if parts and parts[0] == "adaptive_demo" and _get(config, "adaptive_demo.enabled") is False:
            inactive = True
        if parts and parts[0] == "video_world_models":
            if _get(config, "video_world_models.optional_models_enabled") is False:
                inactive |= any(part in optional_ids or part.startswith("optional_") for part in parts[1:])
            if _get(config, "video_world_models.mobile_extension_enabled") is False:
                inactive |= any(part.startswith("mobile_extension") for part in parts[1:])
        if value is None:
            (ignored if inactive else unresolved).append(path or "$")
        elif isinstance(value, Mapping):
            for key, item in value.items():
                walk(item, parts + (str(key),), f"{path}.{key}" if path else str(key), inactive)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, parts, f"{path}[{index}]", inactive)

    walk(config)
    # Absent evidence fields stay unresolved; deleting nulls cannot complete a config.
    unresolved = sorted(set(unresolved) | {path for path in REQUIRED_EVIDENCE_FIELDS if _get(config, path) is None})
    return {"structurally_valid": not errors, "configuration_complete": not errors and not unresolved,
            "validation_errors": errors, "unresolved_fields": unresolved,
            "ignored_disabled_null_fields": sorted(ignored), "readiness_note": READINESS_NOTE}
