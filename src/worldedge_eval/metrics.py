"""Reference reductions for the proposed WorldEdge Tables 4 and 5.

This module contains metric contracts, not an experiment runner or results.
All percentages have a 0--100 scale. Completed@10 has a 0--10 scale.

policy_metrics receives one complete ten-round lifetime per input row. The
caller must supply every scheduled lifetime; this function cannot infer an
omitted lifetime from an unlabelled success matrix.

video_metrics receives outputs for ONE model and an independent expected
manifest with one entry per reference clip. Every manifest clip is scheduled
under every model seed (default: 0 and 1). Missing outputs remain in all
denominators. coverage_complete=False identifies incomplete output coverage.
Duplicate, unscheduled, or inconsistent records raise ValueError.

Seeds are averaged within each clip before clips are aggregated. Outcome BA
is 0.5 * (positive-class accuracy + negative-class accuracy). An unknown
outcome is incorrect for BOTH classes. Invalid/missing videos are incorrect
for outcome and revisit, regardless of any reported prediction. A LPIPS
aggregate is None if ANY scheduled value for that horizon is unavailable.

The per_clip records retain world IDs for world-cluster confidence intervals.
Bootstrap estimation and experiment execution intentionally live elsewhere.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from statistics import fmean
from typing import Any


DEFAULT_REUSE_PAIRS = ((1, 4), (4, 7), (7, 10))
DEFAULT_MODEL_SEEDS = (0, 1)


def _binary(value: Any, label: str) -> int:
    if type(value) not in (bool, int) or value not in (0, 1):
        raise ValueError(f"{label} must be a boolean or integer 0/1")
    return int(value)


def _identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a nonempty string")
    return value


def _lpips(value: Any, label: str) -> float | None:
    if value is None:
        return None
    if type(value) not in (int, float):
        raise ValueError(f"{label} must be a nonnegative finite number or None")
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{label} must be a nonnegative finite number or None")
    return float(value)


def policy_metrics(
    successes: Iterable[Sequence[bool | int]],
    reuse_pairs: Sequence[tuple[int, int]] = DEFAULT_REUSE_PAIRS,
) -> dict[str, Any]:
    """Reduce complete ten-round lifetimes using fixed denominators.

    Reuse pairs use ONE-BASED round numbers. A pair succeeds only when BOTH
    the anchor round and its later reuse round succeed. Earlier failure does
    not remove a pair from the denominator. All ten rounds contribute to
    Completed@10, including successful rounds after an earlier failure.
    """
    matrix = []
    for i, row in enumerate(successes):
        values = list(row)
        if len(values) != 10:
            raise ValueError(f"lifetime {i} must contain exactly 10 outcomes")
        matrix.append([_binary(v, f"lifetime {i}, round {j + 1}")
                       for j, v in enumerate(values)])
    if not matrix:
        raise ValueError("at least one complete lifetime is required")

    pairs = tuple(tuple(pair) for pair in reuse_pairs)
    if not pairs:
        raise ValueError("at least one reuse pair is required")
    for pair in pairs:
        if len(pair) != 2 or any(type(v) is not int for v in pair):
            raise ValueError("reuse pairs must contain two integer round numbers")
        if not 1 <= pair[0] < pair[1] <= 10:
            raise ValueError("reuse pairs must satisfy 1 <= anchor < reuse <= 10")
    if len(set(pairs)) != len(pairs):
        raise ValueError("duplicate reuse pairs are not permitted")

    n = len(matrix)
    csr5_n = sum(all(row[:5]) for row in matrix)
    csr10_n = sum(all(row) for row in matrix)
    completed_n = sum(sum(row) for row in matrix)
    reuse_n = sum(row[a - 1] * row[b - 1]
                  for row in matrix for a, b in pairs)
    reuse_d = n * len(pairs)
    return {
        "csr5_percent": 100.0 * csr5_n / n,
        "csr10_percent": 100.0 * csr10_n / n,
        "completed10_mean": completed_n / n,
        "delayed_reuse_percent": 100.0 * reuse_n / reuse_d,
        "n_lifetimes": n,
        "n_scheduled_tasks": 10 * n,
        "n_completed_tasks": completed_n,
        "csr5_numerator": csr5_n,
        "csr10_numerator": csr10_n,
        "delayed_reuse_numerator": reuse_n,
        "delayed_reuse_denominator": reuse_d,
        "reuse_pairs": [list(pair) for pair in pairs],
    }


def video_metrics(
    rows: Iterable[Mapping[str, Any]],
    expected_manifest: Iterable[Mapping[str, Any]],
    model_seeds: Sequence[int] = DEFAULT_MODEL_SEEDS,
) -> dict[str, Any]:
    """Score one model against a complete independently frozen clip schedule.

    Manifest entry (one per clip)::

        {"world_id": str, "clip_id": str, "ref_outcome": 0 | 1,
         "revisit_expected": bool}

    Output record (one per scheduled clip and seed)::

        {"world_id": str, "clip_id": str, "model_seed": int,
         "ref_outcome": 0 | 1, "revisit_expected": bool,
         "pred_outcome": "success" | "failure" | "unknown",
         "valid_video": bool,
         "revisit_correct": bool | None,
         "lpips5": float | None, "lpips30": float | None}

    The final three fields may be omitted, meaning unavailable. A missing
    revisit judgement is incorrect when the manifest requires a revisit.
    For non-revisit clips that field is ignored. Labels come from the
    manifest; copied row labels must agree and cannot change denominators.

    LPIPS5 and LPIPS30 have independent completeness checks. No unavailable
    value is replaced by zero or removed before averaging. Outcome BA is
    None if the manifest lacks either outcome class. Revisit accuracy is
    None if the manifest contains no revisit clips. Missing output records
    reduce accuracy and set coverage_complete=False; callers must not label
    that model's run complete until all scheduled records are accounted for.
    """
    seeds = tuple(model_seeds)
    if (not seeds or any(type(seed) is not int or seed < 0 for seed in seeds)
            or len(set(seeds)) != len(seeds)):
        raise ValueError("model_seeds must be distinct nonnegative integers")

    manifest: dict[tuple[str, str], dict[str, Any]] = {}
    for item in expected_manifest:
        world_id = _identifier(item.get("world_id"), "manifest world_id")
        clip_id = _identifier(item.get("clip_id"), "manifest clip_id")
        key = (world_id, clip_id)
        if key in manifest:
            raise ValueError(f"duplicate manifest clip: {key!r}")
        outcome = _binary(item.get("ref_outcome"), "manifest ref_outcome")
        revisit = item.get("revisit_expected")
        if type(revisit) is not bool:
            raise ValueError("manifest revisit_expected must be boolean")
        manifest[key] = {"ref_outcome": outcome, "revisit_expected": revisit}
    if not manifest:
        raise ValueError("expected_manifest must contain at least one clip")

    by_key: dict[tuple[str, str, int], dict[str, Any]] = {}
    for row in rows:
        world_id = _identifier(row.get("world_id"), "output world_id")
        clip_id = _identifier(row.get("clip_id"), "output clip_id")
        clip_key = (world_id, clip_id)
        if clip_key not in manifest:
            raise ValueError(f"unscheduled clip: {clip_key!r}")
        seed = row.get("model_seed")
        if type(seed) is not int or seed not in seeds:
            raise ValueError(f"unscheduled model_seed: {seed!r}")
        key = (world_id, clip_id, seed)
        if key in by_key:
            raise ValueError(f"duplicate output: {key!r}")
        reference = manifest[clip_key]
        outcome = _binary(row.get("ref_outcome"), "output ref_outcome")
        revisit = row.get("revisit_expected")
        if type(revisit) is not bool:
            raise ValueError("output revisit_expected must be boolean")
        if (outcome != reference["ref_outcome"]
                or revisit != reference["revisit_expected"]):
            raise ValueError(f"output reference metadata mismatch: {key!r}")
        prediction = row.get("pred_outcome")
        if prediction not in ("success", "failure", "unknown"):
            raise ValueError("pred_outcome must be success, failure, or unknown")
        valid = row.get("valid_video")
        if type(valid) is not bool:
            raise ValueError("valid_video must be boolean")
        revisit_correct = row.get("revisit_correct")
        if revisit_correct is not None and type(revisit_correct) is not bool:
            raise ValueError("revisit_correct must be boolean or None")
        by_key[key] = {
            "prediction": prediction,
            "valid": valid,
            "revisit_correct": revisit_correct,
            "lpips5": _lpips(row.get("lpips5"), "lpips5"),
            "lpips30": _lpips(row.get("lpips30"), "lpips30"),
        }

    missing_outputs = []
    invalid_outputs = []
    per_clip = []
    valid_count = 0
    for (world_id, clip_id), reference in manifest.items():
        outcome_scores = []
        revisit_scores = []
        lpips_values: dict[str, list[float | None]] = {"lpips5": [], "lpips30": []}
        missing_seeds = []
        clip_valid_count = 0
        expected_prediction = "success" if reference["ref_outcome"] else "failure"
        for seed in seeds:
            key = (world_id, clip_id, seed)
            output = by_key.get(key)
            valid = output is not None and output["valid"]
            if output is None:
                missing_outputs.append({"world_id": world_id, "clip_id": clip_id,
                                        "model_seed": seed})
                missing_seeds.append(seed)
            elif not valid:
                invalid_outputs.append({"world_id": world_id, "clip_id": clip_id,
                                        "model_seed": seed})
            clip_valid_count += int(valid)
            outcome_scores.append(int(valid and output["prediction"] == expected_prediction))
            if reference["revisit_expected"]:
                revisit_scores.append(int(valid and output["revisit_correct"] is True))
            for horizon in lpips_values:
                lpips_values[horizon].append(output[horizon] if valid else None)

        valid_count += clip_valid_count
        clip_result = {
            "world_id": world_id,
            "clip_id": clip_id,
            "ref_outcome": reference["ref_outcome"],
            "revisit_expected": reference["revisit_expected"],
            "outcome_correct_fraction": fmean(outcome_scores),
            "revisit_correct_fraction": fmean(revisit_scores) if revisit_scores else None,
            "n_scheduled_seeds": len(seeds),
            "n_present_outputs": len(seeds) - len(missing_seeds),
            "n_valid_videos": clip_valid_count,
            "missing_model_seeds": missing_seeds,
        }
        for horizon, values in lpips_values.items():
            clip_result[f"{horizon}_mean"] = (
                fmean(values) if all(value is not None for value in values) else None
            )
        per_clip.append(clip_result)

    class_scores = {
        label: [clip["outcome_correct_fraction"] for clip in per_clip
                if clip["ref_outcome"] == label]
        for label in (0, 1)
    }
    class_rates = {label: fmean(scores) if scores else None
                   for label, scores in class_scores.items()}
    revisit_scores = [clip["revisit_correct_fraction"] for clip in per_clip
                      if clip["revisit_expected"]]
    scheduled = len(manifest) * len(seeds)
    result = {
        "outcome_ba_percent": (
            50.0 * (class_rates[0] + class_rates[1])
            if class_rates[0] is not None and class_rates[1] is not None else None
        ),
        "outcome_positive_accuracy_percent": (
            100.0 * class_rates[1] if class_rates[1] is not None else None
        ),
        "outcome_negative_accuracy_percent": (
            100.0 * class_rates[0] if class_rates[0] is not None else None
        ),
        "revisit_accuracy_percent": 100.0 * fmean(revisit_scores) if revisit_scores else None,
        "n_clips": len(manifest),
        "n_positive_clips": len(class_scores[1]),
        "n_negative_clips": len(class_scores[0]),
        "n_revisit_clips": len(revisit_scores),
        "n_scheduled_outputs": scheduled,
        "n_present_outputs": len(by_key),
        "n_valid_videos": valid_count,
        "output_coverage_percent": 100.0 * len(by_key) / scheduled,
        "valid_video_percent": 100.0 * valid_count / scheduled,
        "coverage_complete": not missing_outputs,
        "all_videos_valid": valid_count == scheduled,
        "model_seeds": list(seeds),
        "missing_outputs": missing_outputs,
        "invalid_outputs": invalid_outputs,
        "per_clip": per_clip,
    }
    for horizon in ("lpips5", "lpips30"):
        values = [clip[f"{horizon}_mean"] for clip in per_clip]
        complete = all(value is not None for value in values)
        result[f"{horizon}_mean"] = fmean(values) if complete else None
        result[f"{horizon}_complete"] = complete
    return result
