"""NB309 — acronym used before anything expands it.

The allowlist is the rule, so the must-not-fire cases are the real test. The
failure this guards against is a Kubernetes doc lighting up on CRD and RBAC,
which would teach the user to switch the rule off rather than extend the list.
"""

from __future__ import annotations

import pytest

from nabokov.config import Config
from nabokov.issue import Applicability, Severity


def _found(result, code="NB309"):
    return [i for i in result.issues if i.code == code]


# --- fires --------------------------------------------------------------------


def test_unexpanded_acronym_flagged(analyze):
    result = analyze("Configure the FQDN in the settings before you deploy.")
    assert [i.text for i in _found(result)] == ["FQDN"]


def test_reported_once_per_document(analyze):
    """A doc leaning on one unknown acronym costs the reader a line, not a screen."""
    result = analyze("The RBAC policy blocks it, and the RBAC cache is stale. RBAC again.")
    assert len(_found(result)) == 1


def test_each_distinct_acronym_reported(analyze):
    result = analyze("The FQDN and the RBAC policy both matter here.")
    assert {i.text for i in _found(result)} == {"FQDN", "RBAC"}


# --- must not fire ------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        # on the shipped allowlist
        "The API returns JSON over HTTPS, and the CLI reads a YAML config.",
        # plural and possessive forms of an allowlisted entry
        "Our APIs and URLs are stable.",
        # expanded before use, forward order
        "A Fully Qualified Domain Name (FQDN) is required, so set the FQDN now.",
        # expanded before use, reverse order
        "The CRD (custom resource definition) is applied first. The CRD then syncs.",
        # shouted emphasis, not an acronym — the word also appears in lower case
        "This is the CLIENT side; every client must retry.",
        # too long to be an acronym
        "This step is IMPORTANT before you continue with the upgrade.",
        # single letters are variables or initials
        "Set X and Y to the same value.",
    ],
)
def test_not_flagged(analyze, text):
    assert not _found(analyze(text)), text


def test_code_spans_are_invisible(analyze):
    """Markup blanking already hides identifiers, so constants never reach the rule."""
    result = analyze("Set `LOG_LEVEL` and `MAX_RETRIES` in the env.", is_markdown=True)
    assert not _found(result)


# --- config extension ---------------------------------------------------------


def test_known_acronyms_config_silences_it(analyze):
    """Growing the list is the intended response to a noisy run."""
    text = "The RBAC policy and the CRD both apply."
    assert _found(analyze(text))
    quiet = analyze(text, config=Config(known_acronyms=("RBAC", "CRD")))
    assert not _found(quiet)


def test_known_acronyms_is_case_insensitive(analyze):
    quiet = analyze("The RBAC policy applies.", config=Config(known_acronyms=("rbac",)))
    assert not _found(quiet)


def test_known_acronyms_parsed_from_config_file(tmp_path):
    from nabokov.config import build_config

    (tmp_path / ".nabokov.toml").write_text(
        '[nabokov]\nknown_acronyms = ["RBAC", "CRD"]\n', encoding="utf-8"
    )
    config = build_config({}, start=tmp_path)
    assert config.known_acronyms == ("RBAC", "CRD")


# --- shape --------------------------------------------------------------------


def test_is_advisory_and_info(analyze):
    """The linter cannot know the expansion, and cannot know the audience either."""
    issue = _found(analyze("Configure the FQDN first."))[0]
    assert issue.applicability is Applicability.ADVISORY
    assert issue.suggestion is None
    assert issue.severity is Severity.INFO


def test_off_for_social(analyze):
    """Nobody expands an acronym in a 200-character post."""
    result = analyze("Configure the FQDN first.", config=Config(target="SOCIAL"))
    assert not _found(result)


# --- gloss forms found by running the rule on this repo's own docs -------------
# Each of these was a false positive before the case below was handled.


def test_dash_gloss_counts(analyze):
    """Glossaries define with a dash, not parentheses: "**PAS** — Problem, Agitate"."""
    text = "Use PAS for a short ad.\n\n**PAS** — Problem, Agitate, Solution.\n"
    assert not _found(analyze(text, is_markdown=True))


def test_gloss_inside_a_larger_parenthetical(analyze):
    """"diversity (vocabulary variety, MATTR)" explains it without being alone."""
    text = "It prints diversity (vocabulary variety, MATTR). Read MATTR before and after."
    assert not _found(analyze(text))


def test_gloss_wrapped_across_a_line_break(analyze):
    """Hard-wrapped prose puts the gloss on two lines; the paren still counts."""
    text = "It prints diversity (vocabulary\nvariety, MATTR). Compare the MATTR after.\n"
    assert not _found(analyze(text))


def test_gloss_counts_even_when_it_comes_after_first_use(analyze):
    """A glossary at the foot of a page is structure, not a defect."""
    text = "Set the FQDN first.\n\nGlossary\n\nFQDN — fully qualified domain name.\n"
    assert not _found(analyze(text, is_markdown=True))


@pytest.mark.parametrize("word", ["SOCIAL", "NORMAL", "EMAIL", "QUEST", "POST", "HEAD"])
def test_all_caps_english_words_are_identifiers_not_acronyms(analyze, word):
    """Config values and HTTP methods are not abbreviations of anything."""
    assert not _found(analyze(f"Set the target to {word} and rerun the check."))


def test_a_real_acronym_is_still_caught_beside_them(analyze):
    """The English-word guard must not swallow the genuine case."""
    result = analyze("Set the target to SOCIAL and check the FQDN.")
    assert [i.text for i in _found(result)] == ["FQDN"]


def test_readme_is_on_the_allowlist(analyze):
    """Found by running NB309 over this repo's own skill files.

    "README" is as universally known as any entry on the list, and its absence
    is the kind of miss that gets a rule disabled rather than reported.
    """
    assert not _found(analyze("Add the badge to the README first."))


@pytest.mark.parametrize("acronym", ["FIXME", "WIP", "TBD", "STDIN", "STDERR", "EOF"])
def test_everyday_developer_shorthand_allowed(analyze, acronym):
    assert not _found(analyze(f"Leave a {acronym} marker in the file."))
