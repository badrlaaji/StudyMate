"""Tests for .env parsing and loading."""

import os

import pytest

from config import get_env, load_env, parse_env


def test_parse_env_skips_comments_blanks_and_bad_lines():
    text = '# comment\n\nA=1\nB = two \nC="quoted"\nnot a pair\n'
    assert parse_env(text) == {"A": "1", "B": "two", "C": "quoted"}


def test_parse_env_keeps_equals_signs_in_value():
    url = "postgresql+asyncpg://u:p@h/db?ssl=require"
    assert parse_env(f"DATABASE_URL={url}") == {"DATABASE_URL": url}


def test_load_env_never_overrides_existing_variables(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("SM_SHELL=file\nSM_NEW=file\n", encoding="utf-8")
    monkeypatch.setenv("SM_SHELL", "shell")
    monkeypatch.setenv("SM_NEW", "tmp")
    monkeypatch.delenv("SM_NEW")  # restored (removed) after the test
    load_env(env_file)
    assert os.environ["SM_SHELL"] == "shell"
    assert os.environ["SM_NEW"] == "file"


def test_get_env_missing_variable_raises_clear_error():
    with pytest.raises(RuntimeError, match="SM_DOES_NOT_EXIST"):
        get_env("SM_DOES_NOT_EXIST")
