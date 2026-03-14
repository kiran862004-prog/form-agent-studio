from __future__ import annotations

import os
import random
from typing import Any

from openai import OpenAI

from .models import FormField, FormSchema, RunConfig


def _pick_weighted(options: list[str], weights: dict[str, float]) -> str:
    values = [max(weights.get(option, 0.0), 0.0) for option in options]
    if not any(values):
        return random.choice(options)
    return random.choices(options, weights=values, k=1)[0]


def _default_text(field: FormField, config: RunConfig) -> str:
    label = field.label.lower()
    if "email" in label:
        suffix = random.randint(1000, 9999)
        return f"qa.user{suffix}@example.com"
    if "name" in label:
        first = random.choice(["Aarav", "Maya", "Isha", "Arjun", "Noah", "Emma"])
        last = random.choice(["Shah", "Patel", "Brown", "Singh", "Taylor", "Garcia"])
        return f"{first} {last}"
    if "phone" in label or "mobile" in label:
        return f"9{random.randint(100000000, 999999999)}"
    if field.field_type == "paragraph":
        region = config.demographic_profile.get("region", "urban area")
        return f"I had a generally positive experience and would like to see more improvements for users in the {region}."
    return f"Sample response {random.randint(100, 999)}"


def _ai_text(field: FormField, config: RunConfig) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _default_text(field, config)

    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    client = OpenAI(api_key=api_key)
    demographic_hint = ", ".join(f"{k}: {v}" for k, v in config.demographic_profile.items()) or "none"
    prompt = (
        "Generate a concise, realistic synthetic answer for this form question. "
        "Do not include explanations.\n"
        f"Question: {field.label}\n"
        f"Field type: {field.field_type}\n"
        f"Demographic hint: {demographic_hint}\n"
    )
    response = client.responses.create(
        model=model,
        input=prompt,
        max_output_tokens=120,
    )
    text = getattr(response, "output_text", "").strip()
    return text or _default_text(field, config)


def generate_answer(field: FormField, config: RunConfig, strategy: str) -> Any:
    if field.label in config.fixed_answers:
        return config.fixed_answers[field.label]
    if field.name in config.fixed_answers:
        return config.fixed_answers[field.name]

    options = [option.label for option in field.options]
    weights = config.weights.get(field.label) or config.weights.get(field.name) or {}

    if field.field_type in {"multiple_choice", "radio", "dropdown"} and options:
        if strategy == "weighted":
            return _pick_weighted(options, weights)
        return random.choice(options)

    if field.field_type == "checkbox" and options:
        selected = []
        for option in options:
            score = weights.get(option, random.uniform(0.15, 0.55))
            if random.random() < score:
                selected.append(option)
        if not selected:
            selected.append(random.choice(options))
        return selected

    if field.field_type in {"short_answer", "paragraph", "text"}:
        if strategy == "ai":
            return _ai_text(field, config)
        return _default_text(field, config)

    if field.field_type in {"email", "tel", "number"}:
        return _default_text(field, config)

    return _default_text(field, config)


def generate_responses(schema: FormSchema, config: RunConfig, strategy: str, count: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for _ in range(count):
        row: dict[str, Any] = {}
        for field in schema.fields:
            if not field.required and random.random() > config.randomization_level:
                continue
            row[field.label] = generate_answer(field, config, strategy)
        rows.append(row)
    return rows
