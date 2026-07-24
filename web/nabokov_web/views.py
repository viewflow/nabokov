"""POST /api/lint — run the nabokov engine on submitted text, return JSON.

The response body mirrors ``nabokov --format=json`` (one entry, not a list):
``{"summary": {...}, "diagnostics": [...]}``.
"""

from __future__ import annotations

import json
from functools import lru_cache

from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_POST

from nabokov.analyzer import Engine, load_nlp
from nabokov.config import VALID_TARGETS, Config
from nabokov.reporters.json_reporter import result_payload
from nabokov.source import SourceFile
from nabokov.styleprofile import available_profiles

# Hard cap on submitted text: spaCy on arbitrary input is a CPU amplifier, and
# this endpoint is public. ~20k chars is several pages of prose.
MAX_TEXT_CHARS = 20_000


@lru_cache(maxsize=1)
def get_nlp():
    """One spaCy pipeline per process, shared across requests and targets."""
    return load_nlp(auto_download=False)


def _engine(target: str, style: str | None = None) -> Engine:
    # The demo always runs the AI-writing checks too (CLI --ai).
    engine = Engine(Config(target=target, extend_select=("NB5",), style=style))
    engine._nlp = get_nlp()  # inject the shared pipeline
    return engine


def health(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "ok"})


def profiles(request: HttpRequest) -> JsonResponse:
    """Bundled author style profiles the demo can lint against."""
    return JsonResponse({"profiles": available_profiles()})


@require_POST
def lint(request: HttpRequest) -> JsonResponse:
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JsonResponse({"error": "request body must be JSON"}, status=400)

    text = payload.get("text") if isinstance(payload, dict) else None
    if not isinstance(text, str) or not text.strip():
        return JsonResponse({"error": "provide a non-empty 'text' string"}, status=400)
    if len(text) > MAX_TEXT_CHARS:
        return JsonResponse(
            {"error": f"text too long (max {MAX_TEXT_CHARS:,} characters)"}, status=413
        )

    target = str(payload.get("target", "NORMAL")).upper()
    if target not in VALID_TARGETS:
        return JsonResponse(
            {"error": f"invalid target (choose from {', '.join(sorted(VALID_TARGETS))})"},
            status=400,
        )

    # Bundled names only — never filesystem paths on a public endpoint.
    style = payload.get("style") or None
    if style is not None and style not in available_profiles():
        return JsonResponse(
            {"error": f"unknown style profile (choose from {', '.join(available_profiles())})"},
            status=400,
        )

    source = SourceFile.from_text(text, "input.md", is_markdown=True)
    result = _engine(target, style).analyze(source)
    body = result_payload(result)
    del body["path"]  # meaningless for pasted text
    return JsonResponse(body)
