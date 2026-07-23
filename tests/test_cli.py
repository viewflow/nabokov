"""End-to-end CLI tests via main(argv)."""

from __future__ import annotations

import io

import pytest

from nabokov.cli import main


def _write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_findings_exit_code(tmp_path, capsys):
    path = _write(tmp_path, "a.txt", "He quickly ran away.\n")
    rc = main([path, "--format=flake8"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "NB301" in out


def test_clean_file_exit_zero(tmp_path, capsys):
    path = _write(tmp_path, "a.txt", "The cat sat.\n")
    rc = main([path, "--format=flake8"])
    assert rc == 0


def test_exit_zero_flag(tmp_path):
    path = _write(tmp_path, "a.txt", "He quickly ran away.\n")
    rc = main([path, "--format=flake8", "--exit-zero"])
    assert rc == 0


def test_select_only(tmp_path, capsys):
    path = _write(tmp_path, "a.txt", "The cake was quickly eaten in order to celebrate.\n")
    main([path, "--format=flake8", "--select", "NB302"])
    out = capsys.readouterr().out
    assert "NB302" in out
    assert "NB301" not in out
    assert "NB401" not in out


def test_list_rules(capsys):
    rc = main(["--list-rules"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "NB302" in out and "passive-voice" in out


def test_stdin(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO("He quickly ran away.\n"))
    rc = main(["-", "--format=flake8"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "NB301" in out


def test_max_grade_gate(tmp_path, capsys):
    text = (
        "The comprehensive quarterly organizational restructuring initiative "
        "necessitated substantial reallocation of departmental resources across "
        "numerous interdependent operational divisions worldwide.\n"
    )
    path = _write(tmp_path, "a.txt", text)
    rc = main([path, "--format=flake8", "--max-grade", "5"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "NB101" in out


def test_missing_path_errors(capsys):
    with pytest.raises(SystemExit):
        main([])


def test_ai_only_flag(tmp_path, capsys):
    path = _write(tmp_path, "a.txt", "We delve into the rich tapestry of options here.\n")
    main([path, "--format=flake8", "--ai-only"])
    out = capsys.readouterr().out
    assert "NB502" in out  # puffery caught by AI checks


def test_ai_off_by_default(tmp_path, capsys):
    path = _write(tmp_path, "a.txt", "We delve into the rich tapestry of options here.\n")
    main([path, "--format=flake8"])
    out = capsys.readouterr().out
    assert "NB5" not in out  # AI checks off unless --ai / --ai-only


def test_missing_path_exits_2(capsys):
    rc = main(["definitely_not_a_real_file.md", "--format=flake8"])
    assert rc == 2


def test_ignore_nb101_via_cli(tmp_path, capsys):
    text = (
        "The comprehensive quarterly organizational restructuring initiative "
        "necessitated substantial reallocation of departmental resources across divisions.\n"
    )
    path = _write(tmp_path, "a.txt", text)
    main([path, "--format=flake8", "--max-grade", "1", "--ignore", "NB101"])
    out = capsys.readouterr().out
    assert "NB101" not in out


def test_html_file(tmp_path, capsys):
    path = _write(tmp_path, "a.html", "<p>He <b>quickly</b> ran away today.</p>\n")
    rc = main([path, "--format=flake8"])
    out = capsys.readouterr().out
    assert "NB301" in out  # prose inside tags is analyzed
    assert "<" not in out  # tags themselves are not
    assert rc == 1


def test_bad_config_exits_2(tmp_path, capsys, monkeypatch):
    (tmp_path / ".nabokov.toml").write_text('fmt = "yaml"\n', encoding="utf-8")
    (tmp_path / "a.txt").write_text("Fine prose here.\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    rc = main(["a.txt"])
    assert rc == 2
    assert "config error" in capsys.readouterr().err


def test_score_flag(tmp_path, capsys):
    slop = (
        "In today's fast-paced world, our platform plays a crucial role. "
        "It offers a seamless and robust experience for every user. "
        "Moreover, it helps teams navigate the evolving landscape with ease. "
        "Ultimately, the future looks bright for this transformative journey. "
    ) * 3
    path = _write(tmp_path, "slop.txt", slop)
    rc = main([path, "--score"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "AI-likeness" in out
    assert "not a detector verdict" in out


def test_score_too_short(tmp_path, capsys):
    path = _write(tmp_path, "tiny.txt", "The cat sat on the mat.\n")
    rc = main([path, "--score"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "too short to score" in out


def test_score_ranks_slop_above_human_prose(tmp_path, capsys):
    slop = (
        "In today's fast-paced world, our platform plays a crucial role. "
        "It offers a seamless and robust experience for every user. "
        "Moreover, it helps teams navigate the evolving landscape with ease. "
        "Ultimately, the future looks bright for this transformative journey. "
    ) * 3
    human = (
        "We shipped late. The onboarding flow confused the first ten testers, "
        "so Dana rewrote it over a weekend and we pushed the launch to March. "
        "Was that the right call? Probably. Nobody asked for a refund, and the "
        "support queue stayed quiet for the first time since the beta opened. "
        "Next quarter we will hire one more engineer and fix the billing page. "
    ) * 2
    slop_path = _write(tmp_path, "slop.txt", slop)
    human_path = _write(tmp_path, "human.txt", human)
    main([slop_path, "--score"])
    slop_out = capsys.readouterr().out
    main([human_path, "--score"])
    human_out = capsys.readouterr().out

    def score_of(out):
        import re

        return int(re.search(r"AI-likeness (\d+)/100", out).group(1))

    assert score_of(slop_out) > score_of(human_out)


def test_score_punct_component_separates_gap_pair(analyze):
    # Pangram gap regression: metronome punctuation (a comma every clause, all
    # segments the same length) must carry more seg risk than loose human
    # punctuation (run-ons beside two-word asides), even when word-level tells
    # are absent from both.
    from nabokov.score import compute

    metronome = analyze(
        "The launch went well, the team felt proud, the users stayed happy. "
        "The docs were clear, the tests were green, the demo was ready. "
        "The queue stayed quiet, the beta held up, the refunds never came."
    )
    loose = analyze(
        "We wanted the launch to go well and it mostly did even though nobody had slept. "
        "Fine, we thought. "
        "The queue stayed quiet and the beta held up and the refunds never came at all."
    )
    assert compute(loose)["seg_risk"] < compute(metronome)["seg_risk"]
