"""CPU commands that are implemented, rather than stub GPU launch commands."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from .config import load_config, plan, preflight
from .io import read_json, read_records, write_json
from .scoring import score_policy, score_video


def _emit(value: dict, output: str | None) -> None:
    if output:
        write_json(output, value)
        print(f"Wrote {output}")
    else:
        print(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False))


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="worldedge-eval",
        description="Validate WorldEdge protocols and score scheduled evidence.",
        epilog=(
            "Native collection, policy deployment, WM adaptation and forecasting "
            "are integration milestones documented in docs/ROADMAP.md."
        ),
    )
    sub = root.add_subparsers(dest="command", required=True)
    for name, help_text in [
        ("plan", "Derive the run matrix and simulation budget without executing jobs."),
        ("preflight", "Check configuration structure and list unresolved manifests."),
    ]:
        child = sub.add_parser(name, help=help_text)
        child.add_argument("--config", default="configs/experiment.yaml")
        child.add_argument("--output")

    child = sub.add_parser("validate", help="Validate JSON/JSONL records against a per-record schema.")
    child.add_argument("--schema", required=True)
    child.add_argument("--input", required=True)
    child.add_argument("--output")

    for name, help_text in [
        ("score-policy", "Reconcile scheduled lifetimes and reduce Table 4 metrics."),
        ("score-video", "Reconcile forecast samples and reduce Table 5 metrics."),
    ]:
        child = sub.add_parser(name, help=help_text)
        child.add_argument("--manifest", required=True)
        child.add_argument("--records", required=True)
        child.add_argument("--model", required=True)
        child.add_argument("--output")
        if name == "score-video":
            child.add_argument("--model-seeds", nargs="+", type=int, default=[0, 1])

    child = sub.add_parser("tables", help="Export clean CSV/LaTeX tables and a coverage report.")
    child.add_argument("--config", default="configs/experiment.yaml")
    child.add_argument("--policy-scores", nargs="*", default=[])
    child.add_argument("--video-scores", nargs="*", default=[])
    child.add_argument("--output-dir", required=True)
    child.add_argument("--require-complete", action="store_true")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "plan":
            result = plan(load_config(args.config))
            _emit(result, args.output)
            return 0
        if args.command == "preflight":
            result = preflight(load_config(args.config))
            _emit(result, args.output)
            return 0 if result["configuration_complete"] else 2
        if args.command == "validate":
            schema = read_json(args.schema)
            Draft202012Validator.check_schema(schema)
            validator = Draft202012Validator(schema)
            records = read_records(args.input)
            errors = []
            for index, record in enumerate(records):
                for error in validator.iter_errors(record):
                    errors.append({
                        "record_index": index,
                        "path": list(error.absolute_path),
                        "message": error.message,
                    })
            result = {
                "schema": str(Path(args.schema)),
                "records": len(records),
                "valid": not errors,
                "errors": errors,
                "note": "Structural validation does not verify physics or artifact contents.",
            }
            _emit(result, args.output)
            return 0 if not errors else 2
        if args.command in {"score-policy", "score-video"}:
            manifest = read_records(args.manifest)
            records = read_records(args.records, allow_empty=True)
            if args.command == "score-policy":
                result = score_policy(records, manifest, args.model)
            else:
                result = score_video(records, manifest, args.model, model_seeds=tuple(args.model_seeds))
            _emit(result, args.output)
            return 0 if result["reportable"] else 2
        if args.command == "tables":
            from .reporting import export_tables

            result = export_tables(
                load_config(args.config),
                [read_json(path) for path in args.policy_scores],
                [read_json(path) for path in args.video_scores],
                args.output_dir,
                require_complete=args.require_complete,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
            return 0
    except (ValueError, OSError, SchemaError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
