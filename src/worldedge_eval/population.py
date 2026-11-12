"""Audit scored populations against configured counts and paired identities.

This is an accounting check over scoring outputs. It does not inspect raw
artifacts or establish physical validity, source independence, or split
provenance beyond the supplied identifiers.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations
from typing import Any


def audit_populations(
    config: dict, policy_scores: list[dict], video_scores: list[dict],
) -> dict[str, list[str]]:
    """Return per-model issues; no files are read or written.

    The caller validates config and rejects duplicate/unconfigured model IDs.
    Scheduled identities remain auditable for incomplete scoring outputs.
    Missing details produce issues rather than silently satisfying a count.
    Optional scope declarations are checked whenever supplied. An omitted
    split/embodiment declaration is not evidence of split/embodiment validity.
    """
    issues: dict[str, list[str]] = {}
    policy_populations = defaultdict(dict)
    video_populations = {}
    video_clip_populations = {}
    p_cfg = config["policy"]
    v_cfg = config["video_world_models"]
    model_settings = {
        model: setting for setting, spec in p_cfg["settings"].items()
        for model in spec["model_ids"]
    }

    def add(model: str, message: str) -> None:
        if message not in issues[model]:
            issues[model].append(message)

    def register(score: dict) -> str:
        if not isinstance(score, dict):
            raise ValueError("population audit requires scoring-output mappings")
        model = score.get("model_id")
        if not isinstance(model, str) or not model.strip():
            raise ValueError("population audit requires a nonempty model_id")
        issues.setdefault(model, [])
        return model

    def valid_id(value: Any) -> bool:
        return isinstance(value, str) and bool(value.strip())

    def count(model: str, obj: dict, field: str, expected: int) -> None:
        value = obj.get(field)
        if type(value) is not int or value != expected:
            add(model, f"{field}: expected {expected} for the configured population")

    def metadata(model: str, obj: dict, *, setting: str, embodiment: str, video: bool) -> None:
        expected = {"setting": setting, "embodiment_id": embodiment, "split": "test"}
        if video:
            expected["pool"] = "primary"
        for field, value in expected.items():
            if field in obj and obj[field] != value:
                add(model, f"Declared {field} differs from configured test scope ({value!r})")

    def world_population(
        model: str, score: dict, details: list[dict], expected_worlds: int,
    ) -> dict[str, str] | None:
        groups = {}
        usable = True
        for item in details:
            world, source = item.get("world_id"), item.get("source_group_id")
            if not valid_id(world) or not valid_id(source):
                add(model, "Population details require nonempty world_id and source_group_id")
                usable = False
                continue
            if world in groups and groups[world] != source:
                add(model, f"World {world!r} has inconsistent source_group_id values")
                usable = False
            groups[world] = source
        if len(groups) != expected_worlds:
            add(model, f"Expected {expected_worlds} distinct worlds; found {len(groups)}")
        if len(set(groups.values())) != expected_worlds:
            add(model, f"Expected {expected_worlds} distinct independent source groups")
        count(model, score, "n_worlds", expected_worlds)
        count(model, score, "n_source_groups", expected_worlds)
        declared = score.get("source_group_by_world")
        if not isinstance(declared, dict) or declared != groups:
            add(model, "source_group_by_world disagrees with scheduled population details")
        return groups if usable else None

    for score in policy_scores:
        model = register(score)
        setting = model_settings.get(model)
        if setting is None:
            add(model, "Policy model is not assigned to a configured setting")
            continue
        spec = p_cfg["settings"][setting]
        expected_worlds = spec["test_worlds"]
        expected_seeds = p_cfg["rollout_seeds"]
        expected_runs = expected_worlds * len(expected_seeds)
        if score.get("setting") != setting:
            add(model, "Setting differs from the configured policy block")
        metadata(model, score, setting=setting, embodiment=spec["embodiment_id"], video=False)
        for field, expected in (("n_scheduled_runs", expected_runs),
                                ("n_scheduled_tasks", expected_runs * 10)):
            count(model, score, field, expected)
        if score.get("reuse_pairs") != p_cfg["reuse_pairs"]:
            add(model, "Reuse pairs differ from the frozen configuration")
        metrics = score.get("metrics")
        if isinstance(metrics, dict):
            if metrics.get("reuse_pairs") != p_cfg["reuse_pairs"]:
                add(model, "Metric reuse pairs differ from the frozen configuration")
            for field, expected in (("n_lifetimes", expected_runs),
                                    ("n_scheduled_tasks", expected_runs * 10),
                                    ("delayed_reuse_denominator", expected_runs * len(p_cfg["reuse_pairs"]))):
                count(model, metrics, field, expected)
        details = score.get("per_run")
        if not isinstance(details, list) or not all(isinstance(item, dict) for item in details):
            add(model, "Policy per_run population details are unavailable or malformed")
            continue
        if len(details) != expected_runs:
            add(model, f"Expected {expected_runs} scheduled per_run records")
        population = world_population(model, score, details, expected_worlds)
        seeds_by_world = defaultdict(list)
        run_ids = set()
        for item in details:
            metadata(model, item, setting=setting, embodiment=spec["embodiment_id"], video=False)
            if item.get("model_id") != model:
                add(model, "per_run model_id disagrees with its score")
            if item.get("setting") != setting:
                add(model, "per_run setting disagrees with configured policy block")
            run_id = item.get("run_id")
            if not valid_id(run_id) or run_id in run_ids:
                add(model, "per_run contains missing or duplicate run_id values")
            elif valid_id(run_id):
                run_ids.add(run_id)
            world, seed = item.get("world_id"), item.get("seed")
            if not valid_id(world):
                continue
            if type(seed) is not int or seed < 0:
                add(model, "Policy per_run seed must be a nonnegative integer")
                continue
            seeds_by_world[world].append(seed)
        for world, seeds in seeds_by_world.items():
            if Counter(seeds) != Counter(expected_seeds):
                add(model, f"World {world!r} does not contain each configured rollout seed exactly once")
        if population is not None:
            policy_populations[setting][model] = population

    for score in video_scores:
        model = register(score)
        metadata(model, score, setting=v_cfg["primary_setting"],
                 embodiment=v_cfg["embodiment_id"], video=True)
        expected_worlds = config["splits"]["wm_test_worlds"]
        clips_per_world = v_cfg["dataset"]["clips_per_world"]
        revisit_per_world = 2 * v_cfg["dataset"]["pair_counts_per_world"]["delayed_revisit"]
        expected_clips = expected_worlds * clips_per_world
        metrics = score.get("metrics")
        if not isinstance(metrics, dict):
            add(model, "Video metrics and per_clip population details are unavailable")
            continue
        expected_seeds = v_cfg["generation_seeds"]
        if metrics.get("model_seeds") != expected_seeds:
            add(model, "Prediction seeds differ from the frozen configuration")
        for field, expected in (
            ("n_clips", expected_clips), ("n_positive_clips", expected_clips // 2),
            ("n_negative_clips", expected_clips // 2),
            ("n_revisit_clips", expected_worlds * revisit_per_world),
            ("n_scheduled_outputs", expected_clips * len(expected_seeds)),
        ):
            count(model, metrics, field, expected)
        details = metrics.get("per_clip")
        if not isinstance(details, list) or not all(isinstance(item, dict) for item in details):
            add(model, "Video per_clip population details are unavailable or malformed")
            continue
        if len(details) != expected_clips:
            add(model, f"Expected {expected_clips} scheduled per_clip records")
        population = world_population(model, score, details, expected_worlds)
        by_world = defaultdict(list)
        clips = {}
        clips_usable = True
        for item in details:
            metadata(model, item, setting=v_cfg["primary_setting"],
                     embodiment=v_cfg["embodiment_id"], video=True)
            world, clip = item.get("world_id"), item.get("clip_id")
            if not valid_id(world) or not valid_id(clip):
                add(model, "per_clip requires nonempty world_id and clip_id")
                clips_usable = False
                continue
            label, revisit = item.get("ref_outcome"), item.get("revisit_expected")
            if type(label) not in (bool, int) or label not in (0, 1) or type(revisit) is not bool:
                add(model, "per_clip reference labels are malformed")
                clips_usable = False
                continue
            key = (world, clip)
            if key in clips:
                add(model, "per_clip contains duplicate world/clip identities")
                clips_usable = False
            clips[key] = (int(label), revisit)
            by_world[world].append((int(label), revisit))
            count(model, item, "n_scheduled_seeds", len(expected_seeds))
        for world, labels in by_world.items():
            if len(labels) != clips_per_world:
                add(model, f"World {world!r}: expected {clips_per_world} reference clips")
            if sum(label == 1 for label, _ in labels) != clips_per_world // 2 or sum(
                label == 0 for label, _ in labels
            ) != clips_per_world // 2:
                add(model, f"World {world!r}: reference outcomes must be balanced within the world")
            if sum(revisit for _, revisit in labels) != revisit_per_world:
                add(model, f"World {world!r}: expected {revisit_per_world} revisit clips")
        if population is not None:
            video_populations[model] = population
        if clips_usable:
            video_clip_populations[model] = clips

    def compare(populations: dict, label: str) -> None:
        for (first, a), (second, b) in combinations(populations.items(), 2):
            if a != b:
                add(first, f"{label} differs from model {second!r}")
                add(second, f"{label} differs from model {first!r}")

    for setting, populations in policy_populations.items():
        compare(populations, f"Paired policy world/source-group population ({setting})")
    compare(video_populations, "Paired video world/source-group population")
    compare(video_clip_populations, "Paired video clip identities/reference labels")
    if config["splits"]["wm_test_reuses_policy_manipulation_test_worlds"]:
        for policy_model, policy_population in policy_populations["manipulation"].items():
            for video_model, video_population in video_populations.items():
                if policy_population != video_population:
                    add(policy_model, f"Shared manipulation/video test worlds differ from {video_model!r}")
                    add(video_model, f"Shared manipulation/video test worlds differ from {policy_model!r}")
    return issues
