from __future__ import annotations

import random
import time
from typing import Any

from playwright.sync_api import Page, TimeoutError, sync_playwright

from .models import FormSchema


def _safe_delay(base: float = 0.4, spread: float = 0.6) -> None:
    time.sleep(base + random.random() * spread)


def _fill_text(page: Page, label: str, value: str) -> bool:
    text_targets = [
        page.get_by_label(label, exact=False),
        page.get_by_role("textbox", name=label, exact=False),
        page.locator(f"input[aria-label*='{label}'], textarea[aria-label*='{label}']"),
    ]
    for target in text_targets:
        try:
            if target.count() > 0:
                target.first.fill(str(value))
                return True
        except Exception:
            continue
    return False


def _fill_dropdown(page: Page, label: str, value: str) -> bool:
    select_targets = [
        page.get_by_label(label, exact=False),
        page.locator(f"select[aria-label*='{label}']"),
    ]
    for target in select_targets:
        try:
            if target.count() > 0:
                target.first.select_option(label=str(value))
                return True
        except Exception:
            try:
                if target.count() > 0:
                    target.first.select_option(str(value))
                    return True
            except Exception:
                continue

    try:
        option_target = page.get_by_role("option", name=str(value), exact=False)
        if option_target.count() > 0:
            option_target.first.click()
            return True
    except Exception:
        pass

    return False


def _fill_choice(page: Page, label: str, value: str | list[str], multi: bool = False) -> bool:
    values = value if isinstance(value, list) else [value]
    success = False
    for item in values:
        targets = [
            page.get_by_label(item, exact=False),
            page.get_by_role("radio", name=item, exact=False),
            page.get_by_role("checkbox", name=item, exact=False),
            page.get_by_role("option", name=item, exact=False),
        ]
        for target in targets:
            try:
                if target.count() > 0:
                    target.first.click()
                    success = True
                    break
            except Exception:
                continue
        if not multi and success:
            return True
    return success


def _submit(page: Page) -> None:
    submit_targets = [
        page.get_by_role("button", name="Submit", exact=False),
        page.get_by_role("button", name="Send", exact=False),
        page.locator("button[type='submit'], input[type='submit']"),
    ]
    for target in submit_targets:
        try:
            if target.count() > 0:
                target.first.click()
                return
        except Exception:
            continue
    raise RuntimeError("Could not find a submit button.")


def submit_rows(
    url: str,
    schema: FormSchema,
    rows: list[dict[str, Any]],
    retries: int = 2,
    headless: bool = True,
) -> tuple[int, int, list[str]]:
    submitted = 0
    failed = 0
    errors: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        for index, row in enumerate(rows, start=1):
            attempt = 0
            while attempt <= retries:
                page = browser.new_page()
                try:
                    page.goto(url, wait_until="networkidle", timeout=45000)
                    for field in schema.fields:
                        if field.label not in row:
                            continue
                        value = row[field.label]
                        _safe_delay()
                        if field.field_type in {"short_answer", "paragraph", "text", "email", "tel", "number"}:
                            if not _fill_text(page, field.label, value):
                                raise RuntimeError(f"Could not fill text field: {field.label}")
                        elif field.field_type == "dropdown":
                            if not _fill_dropdown(page, field.label, value):
                                raise RuntimeError(f"Could not select dropdown option for: {field.label}")
                        elif field.field_type in {"multiple_choice", "radio"}:
                            if not _fill_choice(page, field.label, value):
                                raise RuntimeError(f"Could not select option for: {field.label}")
                        elif field.field_type == "checkbox":
                            if not _fill_choice(page, field.label, value, multi=True):
                                raise RuntimeError(f"Could not select checkbox for: {field.label}")
                    _safe_delay(0.8, 0.8)
                    _submit(page)
                    page.wait_for_load_state("networkidle", timeout=20000)
                    submitted += 1
                    page.close()
                    break
                except (RuntimeError, TimeoutError) as exc:
                    page.close()
                    attempt += 1
                    if attempt > retries:
                        failed += 1
                        errors.append(f"Row {index}: {exc}")
                except Exception as exc:
                    page.close()
                    failed += 1
                    errors.append(f"Row {index}: {exc}")
                    break
        browser.close()

    return submitted, failed, errors
