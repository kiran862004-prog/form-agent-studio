from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FieldOption:
    label: str
    value: str | None = None


@dataclass
class FormField:
    name: str
    label: str
    field_type: str
    required: bool = False
    options: list[FieldOption] = field(default_factory=list)
    placeholder: str | None = None
    description: str | None = None
    selector: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class FormSchema:
    title: str
    url: str
    fields: list[FormField]


@dataclass
class RunConfig:
    fixed_answers: dict[str, Any] = field(default_factory=dict)
    weights: dict[str, dict[str, float]] = field(default_factory=dict)
    demographic_profile: dict[str, Any] = field(default_factory=dict)
    randomization_level: float = 0.5
    exports: dict[str, str] = field(default_factory=dict)


@dataclass
class RunResult:
    generated: list[dict[str, Any]]
    submitted: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)
