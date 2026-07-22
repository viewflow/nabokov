"""Tests for rule selection and config discovery."""

from __future__ import annotations

import pytest

from nabokov.checks import DEFAULT_CODES
from nabokov.config import Config, ConfigError, build_config, find_config


def test_default_enabled_codes():
    assert Config().enabled_codes() == set(DEFAULT_CODES)


def test_select_prefix():
    cfg = Config(select=("NB3",))
    assert cfg.enabled_codes() == {"NB301", "NB302", "NB303", "NB304", "NB305"}


def test_select_exact_code():
    cfg = Config(select=("NB302",))
    assert cfg.enabled_codes() == {"NB302"}


def test_ignore_removes():
    cfg = Config(ignore=("NB301",))
    assert "NB301" not in cfg.enabled_codes()
    assert "NB302" in cfg.enabled_codes()


def test_extend_select_adds_nb101():
    cfg = Config(extend_select=("NB101",))
    assert "NB101" in cfg.enabled_codes()


def test_find_config_dotfile(tmp_path):
    (tmp_path / ".nabokov.toml").write_text(
        'target = "TECHNICAL"\nignore = ["NB301"]\n', encoding="utf-8"
    )
    data = find_config(tmp_path)
    assert data["target"] == "TECHNICAL"
    assert data["ignore"] == ("NB301",)


def test_find_config_pyproject(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[tool.nabokov]\ntarget = "accessible"\n', encoding="utf-8"
    )
    data = find_config(tmp_path)
    assert data["target"] == "ACCESSIBLE"


def test_build_config_cli_overrides_file(tmp_path):
    (tmp_path / ".nabokov.toml").write_text('target = "TECHNICAL"\n', encoding="utf-8")
    cfg = build_config({"target": "NORMAL"}, start=tmp_path)
    assert cfg.target == "NORMAL"


def test_build_config_falls_back_to_file(tmp_path):
    (tmp_path / ".nabokov.toml").write_text('target = "TECHNICAL"\n', encoding="utf-8")
    cfg = build_config({"target": None}, start=tmp_path)
    assert cfg.target == "TECHNICAL"


def test_invalid_target_in_file_raises(tmp_path):
    (tmp_path / ".nabokov.toml").write_text('target = "SILLY"\n', encoding="utf-8")
    with pytest.raises(ConfigError):
        find_config(tmp_path)


def test_invalid_format_in_file_raises(tmp_path):
    (tmp_path / ".nabokov.toml").write_text('fmt = "yaml"\n', encoding="utf-8")
    with pytest.raises(ConfigError):
        find_config(tmp_path)


def test_extend_ignore_merges_across_layers(tmp_path):
    (tmp_path / ".nabokov.toml").write_text('extend_ignore = ["NB301"]\n', encoding="utf-8")
    cfg = build_config({"extend_ignore": ("NB502",)}, start=tmp_path)
    assert "NB301" in cfg.extend_ignore
    assert "NB502" in cfg.extend_ignore


def test_is_ignored():
    cfg = Config(ignore=("NB101",))
    assert cfg.is_ignored("NB101")
    assert not cfg.is_ignored("NB201")
