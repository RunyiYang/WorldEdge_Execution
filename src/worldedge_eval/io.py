"""Small JSON/JSONL readers and explicit output writers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_json(path: str | Path) -> Any:
    def reject_constant(value: str) -> None:
        raise ValueError(f"Non-finite JSON constant is not permitted: {value}")

    return json.loads(Path(path).read_text(encoding="utf-8"), parse_constant=reject_constant)


def read_records(path: str | Path, *, allow_empty: bool = False) -> list[dict]:
    """Read a JSON object, JSON array of objects, or JSONL file.

    Empty outcome files may represent missing scheduled outputs. An empty
    manifest must never establish a complete evaluation.
    """
    path = Path(path)
    if path.suffix.lower() in {".jsonl", ".ndjson"}:
        records = []
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                item = json.loads(line, parse_constant=lambda value: _reject_constant(value))
            except ValueError as exc:
                raise ValueError(f"{path}, line {number}: {exc}") from exc
            records.append(item)
    else:
        payload = read_json(path)
        records = payload if isinstance(payload, list) else [payload]
    if not records and not allow_empty:
        raise ValueError(f"{path}: expected at least one record")
    if any(not isinstance(item, dict) for item in records):
        raise ValueError(f"{path}: every record must be a JSON object")
    return records


def _reject_constant(value: str) -> None:
    raise ValueError(f"Non-finite JSON constant is not permitted: {value}")


def write_json(path: str | Path, value: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
