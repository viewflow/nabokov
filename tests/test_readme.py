"""NB801 — a README that never says what the project is.

The only README-structure rule the evidence supports, so these tests also pin
why its siblings do not exist.
"""

from __future__ import annotations

from nabokov.issue import Applicability, Severity

BADGES = "![build](https://img.shields.io/badge/build-passing-green)\n"


def _found(result, code="NB801"):
    return [i for i in result.issues if i.code == code]


def _readme(analyze, text, name="README.md"):
    return analyze(text, is_markdown=True, name=name)


def test_badges_then_straight_to_a_section_is_flagged(analyze):
    """The real failure: a title, a wall of badges, then ## Installation."""
    text = f"# widgetron\n\n{BADGES}\n## Installation\n\nRun the installer.\n\n## Usage\n\nGo.\n"
    assert _found(_readme(analyze, text))


def test_a_description_satisfies_it(analyze):
    text = (
        f"# widgetron\n\n{BADGES}\n"
        "A command-line tool that renders widget definitions to SVG.\n\n"
        "## Installation\n\nRun it.\n"
    )
    assert not _found(_readme(analyze, text))


def test_a_long_title_is_not_a_description(analyze):
    """Heading text survives blanking, so it has to be masked out explicitly.

    A title is a label. "# A tool for rendering widget definitions" names the
    project; it is not the sentence a reader needs.
    """
    text = (
        "# A tool for rendering widget definitions to SVG\n\n## Install\n\nRun.\n\n## Use\n\nGo.\n"
    )
    assert _found(_readme(analyze, text))


def test_badges_alone_do_not_count(analyze):
    """Badges say a project has CI. They never say what it does."""
    text = f"# widgetron\n\n{BADGES}{BADGES}{BADGES}\n## Install\n\nRun.\n\n## Use\n\nGo.\n"
    assert _found(_readme(analyze, text))


def test_a_code_fence_is_not_a_description(analyze):
    text = "# widgetron\n\n```sh\npip install widgetron --upgrade --user\n```\n\n## Use\n\nGo.\n\n## X\n\nY.\n"
    assert _found(_readme(analyze, text))


def test_description_below_the_opening_region_does_not_count(analyze):
    """The point is what a reader meets before scrolling."""
    text = (
        "# widgetron\n\n## Install\n\nRun it.\n\n## Usage\n\nGo.\n\n"
        "## About\n\nA command-line tool that renders widget definitions to SVG.\n"
    )
    assert _found(_readme(analyze, text))


# --- scope --------------------------------------------------------------------


def test_only_applies_to_readmes(analyze):
    """This asks about one document's job, not about prose in general."""
    text = f"# widgetron\n\n{BADGES}\n## Install\n\nRun.\n\n## Use\n\nGo.\n"
    assert not _found(_readme(analyze, text, name="docs/GUIDE.md"))
    assert not _found(_readme(analyze, text, name="CHANGELOG.md"))


def test_matches_readme_in_a_subdirectory(analyze):
    text = f"# widgetron\n\n{BADGES}\n## Install\n\nRun.\n\n## Use\n\nGo.\n"
    assert _found(_readme(analyze, text, name="packages/core/README.md"))


def test_plain_text_never_fires(analyze):
    text = f"# widgetron\n\n{BADGES}\n## Install\n\nRun.\n\n## Use\n\nGo.\n"
    assert not _found(analyze(text, name="README.txt"))


def test_stdin_never_fires(analyze):
    text = f"# widgetron\n\n{BADGES}\n## Install\n\nRun.\n\n## Use\n\nGo.\n"
    assert not _found(_readme(analyze, text, name="-"))


# --- shape --------------------------------------------------------------------


def test_is_a_warning_and_a_rewrite(analyze):
    text = f"# widgetron\n\n{BADGES}\n## Install\n\nRun.\n\n## Use\n\nGo.\n"
    issue = _found(_readme(analyze, text))[0]
    assert issue.severity is Severity.WARNING
    assert issue.applicability is Applicability.REWRITE
    assert issue.line == 1


def test_reported_once(analyze):
    text = f"# widgetron\n\n{BADGES}\n## Install\n\nRun.\n\n## Use\n\nGo.\n"
    assert len(_found(_readme(analyze, text))) == 1


# --- the siblings that must not exist -----------------------------------------


def test_no_rule_demands_a_contributing_section():
    """Contribution appears in 27.8% of real READMEs (Prana et al., 393 repos).

    A "missing Contributing" check would fire on 72% of them — not a defect rate,
    the norm. Same for Why (25.7%) and When (21.4%). Popular checklist advice,
    contradicted by the only measurement of it. See docs/rule-research.md.
    """
    from nabokov.checks import RULE_META

    names = " ".join(name for name, _ in RULE_META.values())
    for absent in ("contributing", "license-section", "missing-why", "missing-when"):
        assert absent not in names
