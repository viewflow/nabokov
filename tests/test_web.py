"""Tests for the live-demo API (web/nabokov_web). Skipped when Django is absent."""

import json
import os
import sys
from pathlib import Path

import pytest

django = pytest.importorskip("django")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "web"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nabokov_web.settings")
django.setup()

from django.test import Client

SLOP = (
    "In today's fast-paced digital landscape, the rollout was quietly delayed "
    "by the team in order to fully polish the launch."
)


def _post(payload: dict) -> tuple[int, dict]:
    response = Client().post("/api/lint", json.dumps(payload), content_type="application/json")
    return response.status_code, json.loads(response.content)


def test_lint_finds_issues():
    status, body = _post({"text": SLOP})
    assert status == 200
    assert body["summary"]["words"] > 10
    codes = {d["code"] for d in body["diagnostics"]}
    assert "NB302" in codes  # passive voice
    assert "NB401" in codes  # wordy: in order to
    assert any(c.startswith("NB5") for c in codes)  # AI checks are on


def test_lint_respects_target():
    status, body = _post({"text": SLOP, "target": "essay"})
    assert status == 200
    assert "diagnostics" in body


def test_rejects_bad_target():
    status, body = _post({"text": SLOP, "target": "SHAKESPEARE"})
    assert status == 400
    assert "target" in body["error"]


def test_rejects_missing_text():
    status, body = _post({"text": "   "})
    assert status == 400
    assert "text" in body["error"]


def test_rejects_oversized_text():
    status, body = _post({"text": "word " * 5000})
    assert status == 413
    assert "too long" in body["error"]


def test_rejects_non_json():
    response = Client().post("/api/lint", "not json", content_type="application/json")
    assert response.status_code == 400


def test_get_not_allowed():
    assert Client().get("/api/lint").status_code == 405


def test_health():
    response = Client().get("/api/health")
    assert response.status_code == 200
    assert json.loads(response.content) == {"status": "ok"}
