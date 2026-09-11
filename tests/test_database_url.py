import ssl

import pytest

from app.database_url import database_options


def test_neon_verified_tls_and_password_preserved():
    url, args = database_options(
        "postgresql://example:encoded%25%40@ep-example.neon.tech/example?sslmode=require"
    )
    assert url.drivername == "postgresql+asyncpg"
    assert url.password == "encoded%@"
    assert "sslmode" not in url.query
    assert args["ssl"].verify_mode == ssl.CERT_REQUIRED
    assert args["ssl"].check_hostname
    assert args["server_settings"] == {"timezone": "UTC"}


@pytest.mark.parametrize("query", ["sslmode=disable", "sslmode=", "channel_binding=require", "channel_binding=prefer", "channel_binding=disable", "sslmode=require&ssl=disable"])
def test_neon_rejects_unsupported_security_settings(query):
    with pytest.raises(ValueError):
        database_options("postgresql://example@ep-example.neon.tech/example?" + query)


def test_sqlite_unchanged():
    url, args = database_options("sqlite+aiosqlite:///:memory:")
    assert url.drivername == "sqlite+aiosqlite"
    assert args == {}
