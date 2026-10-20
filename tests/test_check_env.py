"""Tests for the step 0 helpers (no network)."""

from scripts.check_env import asyncpg_args


def test_asyncpg_args_neon_url_keeps_ssl_require():
    dsn, ssl = asyncpg_args(
        "postgresql+asyncpg://u:p@ep-x.neon.tech/neondb?ssl=require"
    )
    assert dsn == "postgresql://u:p@ep-x.neon.tech/neondb"
    assert ssl == "require"


def test_asyncpg_args_local_url_has_no_ssl():
    dsn, ssl = asyncpg_args("postgresql+asyncpg://u:p@localhost:5432/studymate")
    assert dsn == "postgresql://u:p@localhost:5432/studymate"
    assert ssl is None
