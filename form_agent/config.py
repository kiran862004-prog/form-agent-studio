from __future__ import annotations

import json
from pathlib import Path

from .models import RunConfig


def load_config(path: str | None) -> RunConfig:
    if not path:
        return RunConfig()

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return RunConfig(
        fixed_answers=payload.get("fixed_answers", {}),
        weights=payload.get("weights", {}),
        demographic_profile=payload.get("demographic_profile", {}),
        randomization_level=float(payload.get("randomization_level", 0.5)),
        exports=payload.get("exports", {}),
    )
