from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .analyzer import analyze_form, save_schema, save_schema_markdown
from .config import load_config
from .exporter import export_csv, export_json, export_xlsx
from .generator import generate_responses
from .submitter import submit_rows


DEFAULT_GOOGLE_SCHEMA_OUT = "output/google_form_schema.json"
DEFAULT_GOOGLE_SUMMARY_OUT = "output/google_form_schema.md"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Dynamic form testing agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser("analyze", help="Analyze a form and print its schema")
    analyze.add_argument("--url", required=True)
    analyze.add_argument("--schema-out")
    analyze.add_argument("--headed", action="store_true")

    google = subparsers.add_parser("analyze-google", help="Read-only schema extraction for Google Forms")
    google.add_argument("--url", required=True)
    google.add_argument("--schema-out", default=DEFAULT_GOOGLE_SCHEMA_OUT)
    google.add_argument("--summary-out", default=DEFAULT_GOOGLE_SUMMARY_OUT)
    google.add_argument("--headed", action="store_true")

    run = subparsers.add_parser("run", help="Generate responses and optionally submit them")
    run.add_argument("--url", required=True)
    run.add_argument("--count", type=int, default=10)
    run.add_argument("--strategy", choices=["random", "weighted", "ai"], default="random")
    run.add_argument("--config")
    run.add_argument("--schema-out")
    run.add_argument("--submit", action="store_true")
    run.add_argument("--confirm-owned-form", action="store_true")
    run.add_argument("--headed", action="store_true")
    run.add_argument("--json-out")
    run.add_argument("--csv-out")
    run.add_argument("--xlsx-out")
    return parser


def _print_schema(schema) -> None:
    payload = asdict(schema)
    print(json.dumps(payload, indent=2))


def _export(rows: list[dict], args, config) -> None:
    json_path = args.json_out or config.exports.get("json")
    csv_path = args.csv_out or config.exports.get("csv")
    xlsx_path = args.xlsx_out or config.exports.get("xlsx")

    if json_path:
        export_json(rows, json_path)
    if csv_path:
        export_csv(rows, csv_path)
    if xlsx_path:
        export_xlsx(rows, xlsx_path)


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "analyze":
        schema = analyze_form(args.url, headless=not args.headed)
        if args.schema_out:
            save_schema(schema, args.schema_out)
        _print_schema(schema)
        return

    if args.command == "analyze-google":
        schema = analyze_form(args.url, headless=not args.headed)
        save_schema(schema, args.schema_out)
        save_schema_markdown(schema, args.summary_out)
        print(f"Saved JSON schema to {Path(args.schema_out)}")
        print(f"Saved Markdown summary to {Path(args.summary_out)}")
        _print_schema(schema)
        return

    config = load_config(args.config)
    schema = analyze_form(args.url, headless=not args.headed)
    if args.schema_out:
        save_schema(schema, args.schema_out)

    rows = generate_responses(schema, config, args.strategy, args.count)
    _export(rows, args, config)

    print(f"Generated {len(rows)} synthetic response(s).")

    if args.submit:
        if not args.confirm_owned_form:
            raise SystemExit(
                "Submission is blocked until you pass --confirm-owned-form to confirm you own "
                "the target form or are explicitly authorized to test it."
            )
        submitted, failed, errors = submit_rows(
            args.url,
            schema,
            rows,
            headless=not args.headed,
        )
        print(f"Submitted: {submitted}")
        print(f"Failed: {failed}")
        if errors:
            error_path = Path("output") / "submission_errors.json"
            error_path.parent.mkdir(parents=True, exist_ok=True)
            error_path.write_text(json.dumps(errors, indent=2), encoding="utf-8")
            print(f"Errors saved to {error_path}")


if __name__ == "__main__":
    main()
