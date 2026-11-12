"""Reconcile compact result records with a frozen schedule before reduction.

These functions perform no simulator, model, file, or annotation work. They
cannot establish that the supplied outcomes came from physical execution.
The independent manifests, rather than the result files, define denominators.
Malformed or contradictory records raise ValueError; missing work remains
visible in the returned coverage and reportability fields.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from .metrics import (
    DEFAULT_MODEL_SEEDS,
    DEFAULT_REUSE_PAIRS,
    policy_metrics,
    video_metrics,
)


POLICY_METRIC_NAMES = (
    "csr5_percent", "csr10_percent", "completed10_mean", "delayed_reuse_percent",
)
VIDEO_METRIC_NAMES = (
    "lpips5_mean", "lpips30_mean", "outcome_ba_percent", "revisit_accuracy_percent",
)
_POLICY_IDENTIFIERS = (
    "run_id", "model_id", "setting", "world_id", "source_group_id",
)
_OPTIONAL_SCOPE = ("split", "embodiment_id", "pool")
_STATUSES = ("completed", "terminated_policy", "incomplete_infrastructure")


def _rows(values: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(values, list):
        raise ValueError(f"{label} must be a list of records")
    result = []
    for index, row in enumerate(values):
        if not isinstance(row, Mapping):
            raise ValueError(f"{label}[{index}] must be a mapping")
        result.append(dict(row))
    return result


def _identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a nonempty string")
    return value


def _seed(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} must be a nonnegative integer")
    return value


def _binary(value: Any, label: str) -> int:
    if type(value) not in (bool, int) or value not in (0, 1):
        raise ValueError(f"{label} must be a boolean or integer 0/1")
    return int(value)


def _uniform_scope(rows: list[dict[str, Any]], fields: Sequence[str]) -> dict[str, str]:
    """Scope fields must be absent everywhere or declared uniformly."""
    result = {}
    for field in fields:
        present = [field in row for row in rows]
        if any(present):
            if not all(present):
                raise ValueError(f"manifest must declare {field} on every selected entry")
            values = {_identifier(row[field], f"manifest {field}") for row in rows}
            if len(values) != 1:
                raise ValueError(f"cannot score mixed {field} values in one row")
            result[field] = values.pop()
    return result


def _match_optional_scope(
    row: dict[str, Any], expected: dict[str, Any], fields: Sequence[str],
) -> None:
    for field in fields:
        if field in row or field in expected:
            # The manifest supplies metadata when the compact result omits it;
            # result-only metadata cannot silently override an unfrozen scope.
            if field not in expected:
                raise ValueError(f"output {field} is not declared in its manifest entry")
            _identifier(expected[field], f"manifest {field}")
            if field in row:
                _identifier(row[field], f"output {field}")
                if row[field] != expected[field]:
                    raise ValueError(f"output {field} metadata mismatch")


def _world_groups(manifest: list[dict[str, Any]], *, required: bool) -> dict[str, str]:
    """Preserve declared source clusters; use world ID only when unspecified."""
    groups = {}
    for item in manifest:
        world = _identifier(item.get("world_id"), "manifest world_id")
        if "source_group_id" in item or required:
            group = _identifier(item.get("source_group_id"), "manifest source_group_id")
            if world in groups and groups[world] != group:
                raise ValueError(f"inconsistent source_group_id for world {world!r}")
            groups[world] = group
    for item in manifest:
        groups.setdefault(item["world_id"], item["world_id"])
    return groups


def _successes(row: dict[str, Any]) -> list[int] | None:
    values = row.get("successes")
    incomplete = row["status"] == "incomplete_infrastructure"
    if values is None and incomplete:
        return None
    if not isinstance(values, (list, tuple)):
        raise ValueError("successes must contain exactly 10 outcomes for completed runs")
    if (not incomplete and len(values) != 10) or (incomplete and len(values) > 10):
        raise ValueError("successes must contain exactly 10 outcomes (at most 10 for infrastructure failures)")
    return [_binary(value, f"successes[{i}]") for i, value in enumerate(values)]


def score_policy(
    records: list,
    manifest: list,
    model_id: str,
    reuse_pairs: Sequence[tuple[int, int]] = DEFAULT_REUSE_PAIRS,
) -> dict[str, Any]:
    """Score one model and one setting against every scheduled policy run.

    Manifest entries contain run_id, model_id, setting, world_id,
    source_group_id, and a nonnegative integer seed. Results copy these fields
    and add status plus ten binary successes. Optional split, embodiment_id,
    and pool metadata must be uniform for the selected model; supplied result
    metadata must agree with its manifest. Results for known other models are
    validated then excluded. Unknown IDs, duplicates, and disagreements raise.

    A completed or terminated_policy run must already supply all ten outcomes.
    No failure padding is inferred. An incomplete_infrastructure run may have
    omitted or partial outcomes. Any such run or absent scheduled run makes
    metrics=None for the entire selected row; neither is silently discarded.
    """
    model_id = _identifier(model_id, "model_id")
    schedule = _rows(manifest, "manifest")
    outputs = _rows(records, "records")
    by_id = {}
    lifetime_keys = set()
    for item in schedule:
        for field in _POLICY_IDENTIFIERS:
            _identifier(item.get(field), f"manifest {field}")
        _seed(item.get("seed"), "manifest seed")
        for field in _OPTIONAL_SCOPE:
            if field in item:
                _identifier(item[field], f"manifest {field}")
        run_id = item["run_id"]
        if run_id in by_id:
            raise ValueError(f"duplicate manifest run_id: {run_id!r}")
        lifetime_key = (item["model_id"], item["setting"], item["world_id"], item["seed"])
        if lifetime_key in lifetime_keys:
            raise ValueError(f"duplicate scheduled lifetime: {lifetime_key!r}")
        by_id[run_id] = item
        lifetime_keys.add(lifetime_key)
    selected = [row for row in schedule if row["model_id"] == model_id]
    if not selected:
        raise ValueError(f"manifest contains no scheduled runs for model {model_id!r}")
    scope = _uniform_scope(selected, ("setting", *_OPTIONAL_SCOPE))
    groups = _world_groups(schedule, required=True)

    by_run = {}
    for row in outputs:
        run_id = _identifier(row.get("run_id"), "output run_id")
        if run_id in by_run:
            raise ValueError(f"duplicate output run_id: {run_id!r}")
        if run_id not in by_id:
            raise ValueError(f"unscheduled run_id: {run_id!r}")
        expected = by_id[run_id]
        for field in _POLICY_IDENTIFIERS:
            value = _identifier(row.get(field), f"output {field}")
            if value != expected[field]:
                raise ValueError(f"output {field} metadata mismatch for {run_id!r}")
        if _seed(row.get("seed"), "output seed") != expected["seed"]:
            raise ValueError(f"output seed metadata mismatch for {run_id!r}")
        _match_optional_scope(row, expected, _OPTIONAL_SCOPE)
        if row.get("status") not in _STATUSES:
            raise ValueError(f"unsupported policy status: {row.get('status')!r}")
        by_run[run_id] = {**row, "successes": _successes(row)}

    missing = []
    infrastructure = []
    per_run = []
    counts = Counter({status: 0 for status in (*_STATUSES, "missing")})
    for expected in selected:
        row = by_run.get(expected["run_id"])
        status = row["status"] if row is not None else "missing"
        counts[status] += 1
        if status == "missing":
            missing.append(expected["run_id"])
        elif status == "incomplete_infrastructure":
            infrastructure.append(expected["run_id"])
        per_run.append({
            **{key: expected[key] for key in (*_POLICY_IDENTIFIERS, "seed")},
            **{key: expected[key] for key in _OPTIONAL_SCOPE if key in expected},
            "status": status,
            "successes": row["successes"] if row is not None else None,
        })

    # Validate reuse configuration even when no headline metric is reportable.
    pairs = policy_metrics([[0] * 10], reuse_pairs)["reuse_pairs"]
    reportable = not missing and not infrastructure
    metrics = policy_metrics([row["successes"] for row in per_run], pairs) if reportable else None
    worlds = sorted({row["world_id"] for row in selected})
    return {
        "suite": "policy", "model_id": model_id, **scope,
        "reportable": reportable, "metrics": metrics,
        "metric_reportability": {name: reportable for name in POLICY_METRIC_NAMES},
        "coverage_complete": not missing,
        "n_scheduled_runs": len(selected), "n_present_runs": len(selected) - len(missing),
        "n_scheduled_tasks": 10 * len(selected),
        "n_worlds": len(worlds),
        "n_source_groups": len({groups[world] for world in worlds}),
        "source_group_by_world": {world: groups[world] for world in worlds},
        "status_counts": dict(counts),
        "missing_run_ids": missing, "infrastructure_run_ids": infrastructure,
        "reuse_pairs": pairs, "per_run": per_run,
    }


def score_video(
    records: list,
    manifest: list,
    model_id: str,
    model_seeds: Sequence[int] = DEFAULT_MODEL_SEEDS,
) -> dict[str, Any]:
    """Score a video model against an independent clip/seed schedule.

    Shared manifest entries contain world_id, clip_id, ref_outcome, and
    revisit_expected. source_group_id is optional; without any declaration
    for a world it defaults to that world_id. Results add model_id to the
    video_metrics record contract. A shared manifest requires a single-model
    result file: it cannot distinguish a valid other model from a typo. To
    validate/filter a multi-model file, declare model_id on EVERY manifest
    entry, repeating each model's scheduled clips. Unknown models then raise.

    Optional setting, split, embodiment_id, and pool are checked when present.
    Metrics retain fixed denominators even for missing/invalid videos. The
    conservative row-level reportable flag additionally requires all expected
    outputs, valid videos, and all four headline cells. Per-cell flags expose
    independent LPIPS horizons. Unknown semantic predictions remain scored
    errors and do not by themselves make an otherwise complete row incomplete.
    """
    model_id = _identifier(model_id, "model_id")
    schedule = _rows(manifest, "manifest")
    outputs = _rows(records, "records")
    if not schedule:
        raise ValueError("manifest must contain at least one clip")
    seeds = tuple(model_seeds)
    if (not seeds or any(type(seed) is not int or seed < 0 for seed in seeds)
            or len(set(seeds)) != len(seeds)):
        raise ValueError("model_seeds must be distinct nonnegative integers")
    declared = ["model_id" in item for item in schedule]
    if any(declared) and not all(declared):
        raise ValueError("manifest must declare model_id on every entry or no entries")
    model_specific = all(declared)
    schedules: dict[str, list[dict[str, Any]]] = {}
    by_clip = {}
    common_reference = {}
    scope_fields = ("setting", *_OPTIONAL_SCOPE)
    groups = _world_groups(schedule, required=False)
    for item in schedule:
        owner = _identifier(item.get("model_id"), "manifest model_id") if model_specific else model_id
        world = _identifier(item.get("world_id"), "manifest world_id")
        clip = _identifier(item.get("clip_id"), "manifest clip_id")
        key = (owner, world, clip)
        if key in by_clip:
            raise ValueError(f"duplicate manifest clip: {key!r}")
        label = _binary(item.get("ref_outcome"), "manifest ref_outcome")
        revisit = item.get("revisit_expected")
        if type(revisit) is not bool:
            raise ValueError("manifest revisit_expected must be boolean")
        for field in scope_fields:
            if field in item:
                _identifier(item[field], f"manifest {field}")
        reference = (label, revisit, *(item.get(field) for field in scope_fields))
        clip_key = (world, clip)
        if clip_key in common_reference and common_reference[clip_key] != reference:
            raise ValueError(f"manifest reference metadata differs across models for {clip_key!r}")
        common_reference[clip_key] = reference
        by_clip[key] = item
        schedules.setdefault(owner, []).append(item)
    if model_id not in schedules:
        raise ValueError(f"manifest contains no scheduled clips for model {model_id!r}")
    selected = schedules[model_id]
    scope = _uniform_scope(selected, scope_fields)
    rows_by_model: dict[str, list[dict[str, Any]]] = {owner: [] for owner in schedules}
    seen = set()
    for row in outputs:
        owner = _identifier(row.get("model_id"), "output model_id")
        if owner not in schedules:
            raise ValueError(f"unknown output model_id: {owner!r}; shared manifests require selected-model-only records")
        world = _identifier(row.get("world_id"), "output world_id")
        clip = _identifier(row.get("clip_id"), "output clip_id")
        clip_key = (owner, world, clip)
        if clip_key not in by_clip:
            raise ValueError(f"unscheduled clip: {clip_key!r}")
        seed = _seed(row.get("model_seed"), "output model_seed")
        if seed not in seeds:
            raise ValueError(f"unscheduled model_seed: {seed!r}")
        key = (*clip_key, seed)
        if key in seen:
            raise ValueError(f"duplicate output: {key!r}")
        seen.add(key)
        expected = by_clip[clip_key]
        _match_optional_scope(row, expected, scope_fields)
        if "source_group_id" in row:
            source = _identifier(row["source_group_id"], "output source_group_id")
            if source != groups[world]:
                raise ValueError(f"output source_group_id metadata mismatch for {world!r}")
        rows_by_model[owner].append(row)

    # Validate known-other-model result content too, without using its metrics
    # or requiring its coverage to be complete for the requested model.
    for owner in schedules:
        if owner != model_id and rows_by_model[owner]:
            video_metrics(rows_by_model[owner], schedules[owner], seeds)
    metrics = video_metrics(rows_by_model[model_id], selected, seeds)
    for clip in metrics["per_clip"]:
        clip["source_group_id"] = groups[clip["world_id"]]
    complete = metrics["coverage_complete"] and metrics["all_videos_valid"]
    cell_reportability = {
        name: bool(complete and metrics[name] is not None) for name in VIDEO_METRIC_NAMES
    }
    worlds = sorted({item["world_id"] for item in selected})
    return {
        "suite": "video", "model_id": model_id, **scope,
        "reportable": all(cell_reportability.values()), "metrics": metrics,
        "metric_reportability": cell_reportability,
        "coverage_complete": metrics["coverage_complete"],
        "n_worlds": len(worlds),
        "n_source_groups": len({groups[world] for world in worlds}),
        "source_group_by_world": {world: groups[world] for world in worlds},
    }
