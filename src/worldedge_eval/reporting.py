"""Export point estimates without inventing unrun or incomplete results."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from .config import plan
from .io import write_json
from .population import audit_populations


POLICY_LABELS = {
    "pi05_robodojo": r"$\pi_{0.5}$",
    "groot_n17_robodojo": "GR00T N1.7",
    "internvla_a1_robodojo": "InternVLA-A1",
    "openwam_alpha_robodojo": r"OpenWAM-$\alpha$",
    "internw0_delta_robodojo": r"InternW0-$\Delta$",
    "pi05_ebench": r"$\pi_{0.5}$",
    "pi0_ebench": r"$\pi_0$",
    "internvla_a1_ebench": "InternVLA-A1",
    "openwam_alpha_ebench": r"OpenWAM-$\alpha$",
}
VIDEO_LABELS = {
    "cosmos_predict25_2b_action_cond": "Cosmos-Predict2.5",
    "dreamdojo_2b": "DreamDojo-2B",
    "dreamdojo_14b": "DreamDojo-14B",
}
SETTING_LABELS = {
    "manipulation": "Manipulation",
    "mobile_manipulation": "Mobile Manipulation",
}
POLICY_KEYS = [
    "csr5_percent", "csr10_percent", "completed10_mean", "delayed_reuse_percent",
]
VIDEO_KEYS = [
    "lpips5_mean", "lpips30_mean", "outcome_ba_percent", "revisit_accuracy_percent",
]


def _indexed(scores: list[dict], suite: str, allowed: set[str]) -> dict[str, dict]:
    result = {}
    for score in scores:
        if not isinstance(score, dict) or score.get("suite") != suite:
            raise ValueError(f"Expected a {suite} scoring output")
        model = score.get("model_id")
        if model not in allowed:
            raise ValueError(f"Unconfigured or disabled {suite} model: {model!r}")
        if model in result:
            raise ValueError(f"Duplicate score for {suite} model: {model}")
        result[model] = score
    return result


def _row(model: str, score: dict | None, keys: list[str], issues: list[str]) -> dict:
    if score is None:
        return {"model_id": model, "status": "not_run", "issues": [],
                **{key: None for key in keys}}
    if not score.get("reportable"):
        issues.append("Scorer reports incomplete or unavailable evidence")
    metrics = score.get("metrics")
    if not isinstance(metrics, dict):
        issues.append("No metric reduction is available")
        metrics = {}
    import math

    for key in keys:
        value = metrics.get(key)
        if type(value) not in (float, int) or not math.isfinite(value):
            issues.append(f"{key} is unavailable or non-finite")
        elif value < 0:
            issues.append(f"{key} cannot be negative")
        elif (key.endswith("_percent") and value > 100) or (
            key == "completed10_mean" and value > 10
        ):
            issues.append(f"{key} exceeds its declared scale")
    status = "complete" if not issues else "incomplete"
    return {"model_id": model, "status": status, "issues": issues,
            **{key: metrics.get(key) if status == "complete" else None for key in keys}}


def _cell(row: dict, key: str) -> str:
    if row["status"] == "not_run":
        return "--"
    if row["status"] != "complete":
        return "NR"
    return f'{row[key]:.3f}' if key.startswith("lpips") else f'{row[key]:.1f}'


def _safe_label(value: str) -> str:
    translation = {
        "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$",
        "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
        "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
    }
    return "".join(translation.get(char, char) for char in value)


def _write_csv(path: Path, rows: list[dict], keys: list[str], policy: bool) -> None:
    headers = (["setting"] if policy else []) + ["model_id", "status"] + keys
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def export_tables(
    config: dict,
    policy_scores: list[dict],
    video_scores: list[dict],
    output_dir: str | Path,
    *,
    require_complete: bool = False,
) -> dict[str, Any]:
    """Write CSVs/LaTeX and coverage, with strict configured count checks.

    This checks score-file accounting. It does not certify checkpoint
    adaptation, physical validity, annotation audit or statistical inference.
    """
    plan(config)  # Validate scientific/count consistency before exporting.
    p_cfg = config["policy"]
    w_cfg = config["video_world_models"]
    policy_ids = {
        model for item in p_cfg["settings"].values() for model in item["model_ids"]
    }
    video_ids = list(w_cfg["primary_models"])
    if w_cfg["optional_models_enabled"]:
        video_ids += w_cfg["optional_models"]
    policies = _indexed(policy_scores, "policy", policy_ids)
    videos = _indexed(video_scores, "video", set(video_ids))
    population_issues = audit_populations(config, policy_scores, video_scores)
    p_rows = []
    for setting, spec in p_cfg["settings"].items():
        expected = spec["test_worlds"] * len(p_cfg["rollout_seeds"])
        for model in spec["model_ids"]:
            score = policies.get(model)
            issues = list(population_issues.get(model, []))
            if score is not None:
                if score.get("setting") != setting:
                    issues.append("Setting differs from the configured policy block")
                metrics = score.get("metrics") or {}
                if metrics.get("n_lifetimes") != expected:
                    issues.append(f"Expected {expected} lifetimes for this configured row")
            row = _row(model, score, POLICY_KEYS, issues)
            row["setting"] = setting
            p_rows.append(row)
    v_rows = []
    expected_clips = config["splits"]["wm_test_worlds"] * w_cfg["dataset"]["clips_per_world"]
    expected_revisit = (
        config["splits"]["wm_test_worlds"]
        * w_cfg["dataset"]["pair_counts_per_world"]["delayed_revisit"] * 2
    )
    for model in video_ids:
        score = videos.get(model)
        issues = list(population_issues.get(model, []))
        if score is not None:
            metrics = score.get("metrics") or {}
            for key, expected in [
                ("n_clips", expected_clips),
                ("n_positive_clips", expected_clips // 2),
                ("n_negative_clips", expected_clips // 2),
                ("n_revisit_clips", expected_revisit),
                ("n_scheduled_outputs", expected_clips * len(w_cfg["generation_seeds"])),
            ]:
                if metrics.get(key) != expected:
                    issues.append(f"{key}: expected {expected} in the configured test population")
            if metrics.get("model_seeds") != w_cfg["generation_seeds"]:
                issues.append("Prediction seeds differ from the frozen configuration")
        v_rows.append(_row(model, score, VIDEO_KEYS, issues))
    complete = all(row["status"] == "complete" for row in p_rows + v_rows)
    if require_complete and not complete:
        bad = [row["model_id"] for row in p_rows + v_rows if row["status"] != "complete"]
        raise ValueError("Cannot export final tables; unrun/incomplete rows: " + ", ".join(bad))

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    _write_csv(out / "table4.csv", p_rows, POLICY_KEYS, True)
    _write_csv(out / "table5.csv", v_rows, VIDEO_KEYS, False)
    p_tex = [
        "% Generated from declared scores. -- = not run; NR = incomplete.",
        r"\begin{table}[t]", r"\centering",
        r"\caption{\textbf{Robot policy evaluation.} SR@\(K\) requires all first "
        r"\(K\) tasks. Tasks counts all successes out of ten. Reuse uses fixed "
        r"anchor/reuse pairs. Percentages except Tasks.}",
        r"\label{tab:worldedge_robot_policies}",
        r"\begingroup\small\setlength{\tabcolsep}{2pt}\renewcommand{\arraystretch}{1.12}",
        r"\begin{tabular*}{\columnwidth}{@{\extracolsep{\fill}}lrrrr@{}}",
        r"\toprule",
        r"Policy & SR@5 $\uparrow$ & SR@10 $\uparrow$ & Tasks /10 $\uparrow$ & Reuse $\uparrow$ \\",
    ]
    for setting in p_cfg["settings"]:
        p_tex += [r"\midrule", r"\multicolumn{5}{@{}l}{\textit{"
                  + SETTING_LABELS.get(setting, _safe_label(setting)) + r"}} \\"]
        for row in [item for item in p_rows if item["setting"] == setting]:
            label = POLICY_LABELS.get(row["model_id"], _safe_label(row["model_id"]))
            p_tex.append(label + " & " + " & ".join(_cell(row, key) for key in POLICY_KEYS) + r" \\")
    p_tex += [r"\bottomrule", r"\end{tabular*}\endgroup", r"\end{table}"]
    v_tex = [
        "% Generated from declared scores. -- = not run; NR = incomplete.",
        r"\begin{table}[t]", r"\centering",
        r"\caption{\textbf{Video world model evaluation.} Target-adapted manipulation "
        r"models predict from initial RGB and issued controls. LPIPS is measured "
        r"at each endpoint. Outcome is balanced stage-outcome accuracy. Revisit "
        r"measures visible identity and actual state accuracy.}",
        r"\label{tab:worldedge_world_models}",
        r"\label{tab:worldedge_world_action_policies}",
        r"\begingroup\small\setlength{\tabcolsep}{2pt}\renewcommand{\arraystretch}{1.12}",
        r"\begin{tabular*}{\columnwidth}{@{\extracolsep{\fill}}lrrrr@{}}",
        r"\toprule",
        r"& \multicolumn{2}{c}{LPIPS $\downarrow$} & \multicolumn{2}{c}{Accuracy (\%) $\uparrow$} \\",
        r"\cmidrule(lr){2-3}\cmidrule(lr){4-5}",
        r"Model & 5 s & 30 s & Outcome & Revisit \\", r"\midrule",
    ]
    for row in v_rows:
        label = VIDEO_LABELS.get(row["model_id"], _safe_label(row["model_id"]))
        v_tex.append(label + " & " + " & ".join(_cell(row, key) for key in VIDEO_KEYS) + r" \\")
    v_tex += [r"\bottomrule", r"\end{tabular*}\endgroup", r"\end{table}"]
    (out / "table4.tex").write_text("\n".join(p_tex) + "\n", encoding="utf-8")
    (out / "table5.tex").write_text("\n".join(v_tex) + "\n", encoding="utf-8")
    coverage = {
        "protocol_id": config["protocol"]["id"],
        "all_configured_rows_complete": complete,
        "policy_rows": p_rows, "video_rows": v_rows,
        "note": (
            "Point estimates only. Physical execution, annotation audits and "
            "world-cluster confidence intervals require their independent evidence."
        ),
    }
    write_json(out / "coverage.json", coverage)
    return {
        "output_dir": str(out),
        "all_configured_rows_complete": complete,
        "files": ["table4.csv", "table5.csv", "table4.tex", "table5.tex", "coverage.json"],
    }
