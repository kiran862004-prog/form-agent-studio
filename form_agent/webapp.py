from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Any

from flask import Flask, Response, abort, jsonify, render_template, request, send_file, url_for

from .analyzer import analyze_form, save_schema, save_schema_markdown
from .config import load_config
from .exporter import export_csv, export_json, export_xlsx
from .generator import generate_responses
from .submitter import submit_rows


APP_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = APP_ROOT / "form_agent" / "web" / "templates"
STATIC_DIR = APP_ROOT / "form_agent" / "web" / "static"
DEFAULT_CONFIG = APP_ROOT / "config.example.json"
DEMO_FORM = APP_ROOT / "demo" / "demo_form.html"
DEFAULT_DEMO_URL = DEMO_FORM.resolve().as_uri()
OUTPUT_DIR = APP_ROOT / "output"
ACTIVITY_LOG_PATH = OUTPUT_DIR / "activity_log.jsonl"
DEFAULT_GOOGLE_SCHEMA_OUT = OUTPUT_DIR / "google_form_schema.json"
DEFAULT_GOOGLE_SUMMARY_OUT = OUTPUT_DIR / "google_form_schema.md"
DEFAULT_HOST = os.getenv("FORM_AGENT_HOST", "0.0.0.0")
DEFAULT_PORT = int(os.getenv("PORT", os.getenv("FORM_AGENT_PORT", "8000")))
BASIC_AUTH_USERNAME = os.getenv("FORM_AGENT_USERNAME", "")
BASIC_AUTH_PASSWORD = os.getenv("FORM_AGENT_PASSWORD", "")

DOWNLOAD_FILES = {
    "ui_schema_json": OUTPUT_DIR / "ui_schema.json",
    "ui_responses_json": OUTPUT_DIR / "ui_responses.json",
    "ui_responses_csv": OUTPUT_DIR / "ui_responses.csv",
    "ui_responses_xlsx": OUTPUT_DIR / "ui_responses.xlsx",
    "submission_errors_json": OUTPUT_DIR / "submission_errors.json",
    "google_schema_json": DEFAULT_GOOGLE_SCHEMA_OUT,
    "google_schema_md": DEFAULT_GOOGLE_SUMMARY_OUT,
    "activity_log_jsonl": ACTIVITY_LOG_PATH,
}


app = Flask(__name__, template_folder=str(TEMPLATE_DIR), static_folder=str(STATIC_DIR))


@app.after_request
def add_security_headers(response: Response) -> Response:
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Cache-Control"] = "no-store"
    if request.is_secure or request.headers.get("X-Forwarded-Proto", "").lower() == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


def _requires_auth() -> bool:
    return bool(BASIC_AUTH_USERNAME and BASIC_AUTH_PASSWORD)


def _unauthorized() -> Response:
    return Response(
        "Authentication required.",
        401,
        {"WWW-Authenticate": 'Basic realm="Form Agent Studio"'},
    )


def _authorized() -> bool:
    if not _requires_auth():
        return True
    auth = request.authorization
    return bool(auth and auth.username == BASIC_AUTH_USERNAME and auth.password == BASIC_AUTH_PASSWORD)


def require_auth(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not _authorized():
            return _unauthorized()
        return func(*args, **kwargs)

    return wrapper


def _client_identity() -> dict[str, str]:
    forwarded_for = request.headers.get("CF-Connecting-IP") or request.headers.get("X-Forwarded-For") or request.remote_addr or "unknown"
    if "," in forwarded_for:
        forwarded_for = forwarded_for.split(",", 1)[0].strip()
    user_agent = request.headers.get("User-Agent", "unknown")
    username = request.authorization.username if request.authorization else "anonymous"
    return {
        "ip": forwarded_for,
        "user_agent": user_agent,
        "username": username,
    }


def _log_activity(action: str, details: dict[str, Any] | None = None) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        **_client_identity(),
        "details": details or {},
    }
    with ACTIVITY_LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload) + "\n")


def _default_values() -> dict[str, Any]:
    return {
        "url": DEFAULT_DEMO_URL,
        "count": 5,
        "strategy": "weighted",
        "config_path": str(DEFAULT_CONFIG),
        "submit": False,
        "confirm_owned_form": False,
        "headed": False,
        "export_json": True,
        "export_csv": True,
        "export_xlsx": False,
        "google_url": "",
        "google_headed": False,
    }


def _download_links() -> dict[str, str]:
    links: dict[str, str] = {}
    for key, path in DOWNLOAD_FILES.items():
        if path.exists():
            links[key] = url_for("download_file", file_key=key)
    return links


def _recent_activity(limit: int = 20) -> list[dict[str, Any]]:
    if not ACTIVITY_LOG_PATH.exists():
        return []
    lines = ACTIVITY_LOG_PATH.read_text(encoding="utf-8").splitlines()
    rows: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return list(reversed(rows))


def _base_context() -> dict[str, Any]:
    return {
        "values": _default_values(),
        "message": "",
        "error": "",
        "google_message": "",
        "google_error": "",
        "schema_json": "",
        "rows_json": "",
        "errors_json": "",
        "google_schema_json": "",
        "google_summary_text": "",
        "stats": [],
        "google_stats": [],
        "demo_url": DEFAULT_DEMO_URL,
        "output_dir": str(OUTPUT_DIR),
        "download_links": _download_links(),
        "network_host": DEFAULT_HOST,
        "network_port": DEFAULT_PORT,
        "auth_enabled": _requires_auth(),
        "recent_activity": _recent_activity(),
    }


@app.route("/health", methods=["GET"])
def health() -> Response:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "ok",
        "service": "form-agent-studio",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "auth_enabled": _requires_auth(),
        "output_dir": str(OUTPUT_DIR),
    }
    return jsonify(payload)


@app.route("/", methods=["GET", "POST"])
@require_auth
def index() -> str:
    context = _base_context()

    if request.method == "GET":
        _log_activity("view_dashboard")

    if request.method == "POST":
        action = request.form.get("action", "analyze")
        values = context["values"]
        values.update(
            {
                "url": request.form.get("url", values["url"]),
                "count": request.form.get("count", values["count"]),
                "strategy": request.form.get("strategy", values["strategy"]),
                "config_path": request.form.get("config_path", values["config_path"]),
                "submit": bool(request.form.get("submit")),
                "confirm_owned_form": bool(request.form.get("confirm_owned_form")),
                "headed": bool(request.form.get("headed")),
                "export_json": bool(request.form.get("export_json")),
                "export_csv": bool(request.form.get("export_csv")),
                "export_xlsx": bool(request.form.get("export_xlsx")),
                "google_url": request.form.get("google_url", values["google_url"]),
                "google_headed": bool(request.form.get("google_headed")),
            }
        )

        if action in {"analyze", "generate"}:
            _handle_main_form(context)
        elif action == "analyze_google":
            _handle_google_analysis(context)

        context["download_links"] = _download_links()
        context["recent_activity"] = _recent_activity()

    return render_template("index.html", **context)


@app.route("/downloads/<file_key>")
@require_auth
def download_file(file_key: str):
    path = DOWNLOAD_FILES.get(file_key)
    if not path:
        abort(404)
    if not path.exists() or not path.is_file():
        abort(404)
    _log_activity("download_file", {"file_key": file_key, "filename": path.name})
    return send_file(path, as_attachment=True, download_name=path.name)


def _handle_main_form(context: dict[str, Any]) -> None:
    values = context["values"]
    try:
        url = str(values["url"]).strip()
        count = max(int(values["count"]), 1)
        strategy = str(values["strategy"])
        config_path = str(values["config_path"]).strip()
        headless = not bool(values["headed"])
        action = request.form.get("action", "analyze")

        config = load_config(config_path if config_path else None)
        schema = analyze_form(url, headless=headless)
        context["schema_json"] = json.dumps(asdict(schema), indent=2)
        context["stats"].append({"label": "Fields found", "value": len(schema.fields)})

        schema_path = OUTPUT_DIR / "ui_schema.json"
        save_schema(schema, str(schema_path))
        context["message"] = f"Schema saved to {schema_path}"
        _log_activity("analyze_form", {"url": url, "field_count": len(schema.fields)})

        if action == "generate":
            rows = generate_responses(schema, config, strategy, count)
            context["rows_json"] = json.dumps(rows, indent=2)
            context["stats"].append({"label": "Rows generated", "value": len(rows)})

            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            if values["export_json"]:
                export_json(rows, str(OUTPUT_DIR / "ui_responses.json"))
            if values["export_csv"]:
                export_csv(rows, str(OUTPUT_DIR / "ui_responses.csv"))
            if values["export_xlsx"]:
                export_xlsx(rows, str(OUTPUT_DIR / "ui_responses.xlsx"))

            _log_activity(
                "generate_responses",
                {
                    "url": url,
                    "strategy": strategy,
                    "count": len(rows),
                    "exports": {
                        "json": bool(values["export_json"]),
                        "csv": bool(values["export_csv"]),
                        "xlsx": bool(values["export_xlsx"]),
                    },
                },
            )

            if values["submit"]:
                if not values["confirm_owned_form"]:
                    raise ValueError(
                        "Submission requires confirming that you own the form or are explicitly authorized to test it."
                    )
                submitted, failed, errors = submit_rows(url, schema, rows, headless=headless)
                context["stats"].append({"label": "Submitted", "value": submitted})
                context["stats"].append({"label": "Failed", "value": failed})
                if errors:
                    context["errors_json"] = json.dumps(errors, indent=2)
                    error_path = OUTPUT_DIR / "submission_errors.json"
                    error_path.write_text(json.dumps(errors, indent=2), encoding="utf-8")
                context["message"] = "Synthetic responses generated and the authorized submission workflow completed."
                _log_activity("submit_rows", {"url": url, "submitted": submitted, "failed": failed})
            else:
                context["message"] = "Schema analyzed and synthetic responses generated. Exports were written to the output folder."
    except Exception as exc:
        context["error"] = str(exc)
        _log_activity("main_form_error", {"error": str(exc)})


def _handle_google_analysis(context: dict[str, Any]) -> None:
    values = context["values"]
    try:
        url = str(values["google_url"] or values["url"]).strip()
        if not url:
            raise ValueError("Enter a Google Form URL to analyze.")

        schema = analyze_form(url, headless=not bool(values["google_headed"]))
        save_schema(schema, str(DEFAULT_GOOGLE_SCHEMA_OUT))
        save_schema_markdown(schema, str(DEFAULT_GOOGLE_SUMMARY_OUT))

        context["google_schema_json"] = json.dumps(asdict(schema), indent=2)
        context["google_summary_text"] = DEFAULT_GOOGLE_SUMMARY_OUT.read_text(encoding="utf-8")
        context["google_stats"].append({"label": "Fields found", "value": len(schema.fields)})
        context["google_stats"].append({"label": "Required", "value": sum(1 for field in schema.fields if field.required)})
        context["google_message"] = (
            f"Read-only Google Form schema saved to {DEFAULT_GOOGLE_SCHEMA_OUT} and {DEFAULT_GOOGLE_SUMMARY_OUT}."
        )
        _log_activity("analyze_google_form", {"url": url, "field_count": len(schema.fields)})
    except Exception as exc:
        context["google_error"] = str(exc)
        _log_activity("google_analysis_error", {"error": str(exc)})


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Form Agent Studio web app")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    return parser


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    args = _build_parser().parse_args()
    app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
