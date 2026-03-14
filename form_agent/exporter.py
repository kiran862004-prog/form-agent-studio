from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def _normalize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for row in rows:
        normalized.append(
            {
                key: ", ".join(value) if isinstance(value, list) else value
                for key, value in row.items()
            }
        )
    return normalized


def export_json(rows: list[dict[str, Any]], path: str) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def export_csv(rows: list[dict[str, Any]], path: str) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(_normalize_rows(rows)).to_csv(out, index=False)


def export_xlsx(rows: list[dict[str, Any]], path: str) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(_normalize_rows(rows)).to_excel(out, index=False)
