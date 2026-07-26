"""NB315 — exclusionary terms with a settled replacement (opt-in)."""

from __future__ import annotations

import pytest

from nabokov.config import Config
from nabokov.issue import Applicability

ON = Config(extend_select=("NB315",))


def _found(result, code="NB315"):
    return [i for i in result.issues if i.code == code]


def test_off_by_default(analyze):
    """A project policy, not a defect — nabokov waits to be asked."""
    assert not _found(analyze("Add the IP to the whitelist."))


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Add the IP to the whitelist.", "allowlist"),
        ("Check the blacklist too.", "denylist, blocklist"),
        ("The master/slave lag is high.", "primary/replica"),
        ("Run a sanity check first.", "quick check, confidence check"),
        ("This took forty man hours.", "person hours"),
        ("The account is grandfathered.", "legacy, exempt"),
    ],
)
def test_flagged_with_the_replacement(analyze, text, expected):
    issue = _found(analyze(text, config=ON))[0]
    assert issue.suggestion == expected
    assert issue.applicability is Applicability.REPLACE


def test_inflected_forms_are_listed_not_stemmed(analyze):
    """A substitution that guesses at morphology is not a substitution."""
    issue = _found(analyze("Whitelisting is handled by the proxy.", config=ON))[0]
    assert issue.suggestion == "Allowlisting"


def test_replacement_matches_the_case(analyze):
    issue = _found(analyze("Whitelist the address first.", config=ON))[0]
    assert issue.suggestion == "Allowlist"


def test_replace_actually_substitutes(analyze):
    text = "Add the IP to the whitelist now."
    result = analyze(text, config=ON)
    issue = _found(result)[0]
    start = result.source.offset(issue.line, issue.col)
    end = result.source.offset(issue.end_line, issue.end_col)
    assert text[:start] + issue.suggestion + text[end:] == "Add the IP to the allowlist now."


# --- "master" alone is deliberately absent ------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "She is mastering the API.",
        "He has a master of science degree.",
        "Check out the master branch.",
        "The master copy lives in S3.",
    ],
)
def test_bare_master_never_fires(analyze, text):
    """Only the slave-paired sense is unambiguous; the rest is ordinary English."""
    assert not _found(analyze(text, config=ON)), text


# --- the data file's own criterion --------------------------------------------


def test_contested_terms_are_absent():
    """An entry needs an AGREED replacement, not an objection.

    'crazy', 'insane' and 'blind spot' were drafted and cut: no settled
    alternative, and entries like them are what get a whole rule disabled.
    """
    from nabokov.data_loader import terminology

    terms = terminology()
    assert "crazy" not in terms
    assert "insane" not in terms
    assert "blind spot" not in terms


def test_every_term_carries_at_least_one_replacement():
    from nabokov.data_loader import terminology

    assert all(alternatives for alternatives in terminology().values())
