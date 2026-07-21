"""Shared fixtures. The spaCy pipeline is loaded once for the whole session."""

from __future__ import annotations

import pytest

from nabokov.analyzer import Engine, load_nlp
from nabokov.config import Config
from nabokov.source import SourceFile


@pytest.fixture(scope="session", autouse=True)
def _prime_nlp():
    load_nlp()


@pytest.fixture
def analyze():
    def _analyze(text, *, config=None, is_markdown=False, is_html=False, name="test.txt"):
        engine = Engine(config or Config())
        source = SourceFile.from_text(text, name, is_markdown=is_markdown, is_html=is_html)
        return engine.analyze(source)

    return _analyze


@pytest.fixture
def codes(analyze):
    def _codes(text, **kwargs):
        return [i.code for i in analyze(text, **kwargs).issues]

    return _codes
