"""Credential-safe, shared SQLAlchemy/asyncpg connection configuration."""
import ssl
from urllib.parse import parse_qsl

from sqlalchemy.engine import make_url


def database_options(raw):
    try:
        url = make_url(raw)
    except Exception:
        raise ValueError("Invalid database URL (details omitted)") from None
    if url.drivername not in {"postgres", "postgresql", "postgresql+asyncpg"}:
        return url, {}
    # SQLAlchemy drops blank query values; do not silently accept blank security
    # directives as though they had not been supplied.
    if isinstance(raw, str) and any(
        key in {"sslmode", "ssl", "channel_binding"} and not value
        for key, value in parse_qsl(raw.partition("?")[2], keep_blank_values=True)
    ):
        raise ValueError("Empty security URL option")
    url = url.set(drivername="postgresql+asyncpg")
    query = dict(url.query)
    binding = query.pop("channel_binding", None)
    if binding is not None:
        raise ValueError("channel_binding is unsupported by asyncpg; use verified TLS without this parameter")
    mode = query.pop("sslmode", None)
    ssl_option = query.pop("ssl", None)
    if mode is not None and ssl_option is not None:
        raise ValueError("Specify only one SSL option")
    mode = mode if mode is not None else ssl_option
    neon = bool(url.host and url.host.endswith(".neon.tech"))
    args = {"server_settings": {"timezone": "UTC"}}
    if neon or mode is not None:
        if mode not in (None, "require", "verify-ca", "verify-full"):
            raise ValueError("SSL configuration must require verified TLS")
        # Stronger than require: system CA verification AND hostname verification.
        args["ssl"] = ssl.create_default_context()
    if any(key.startswith("ssl") for key in query):
        raise ValueError("Unsupported SSL URL option; system CA trust is used")
    return url.set(query=query), args


def create_database_engine(raw, **options):
    """Application and Alembic engines share the same security policy."""
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import event

    url, args = database_options(raw)
    engine = create_async_engine(
        url, echo=False, hide_parameters=True, connect_args=args, **options
    )
    if url.drivername == "postgresql+asyncpg":
        # Run outside a SQLAlchemy transaction so pool rollback cannot undo SET.
        # Startup settings alone are not proof of the effective backend setting.
        def initialize(dbapi_connection, connection_record):
            dbapi_connection.run_async(initialize_postgres_session)

        event.listen(engine.sync_engine, "connect", initialize)
    return engine


async def initialize_postgres_session(connection):
    """Enforce and verify UTC on each newly opened physical connection."""
    await connection.execute("SET SESSION TIME ZONE 'UTC'")
    if await connection.fetchval("SHOW timezone") != "UTC":
        raise RuntimeError("Non-UTC session")


async def connect_postgres(raw):
    """Diagnostic connection using exactly SQLAlchemy's asyncpg arguments.

    An SSLContext with CERT_REQUIRED and check_hostname makes a successful
    asyncpg handshake proof of verified client TLS. pg_stat_ssl describes the
    backend connection, which may be behind a TLS-terminating proxy.
    """
    import asyncpg
    from sqlalchemy.dialects.postgresql.asyncpg import dialect

    url, args = database_options(raw)
    if url.drivername != "postgresql+asyncpg":
        raise ValueError("PostgreSQL connection required")
    positional, keywords = dialect().create_connect_args(url)
    keywords.update(args)
    connection = await asyncpg.connect(*positional, **keywords, timeout=10)
    try:
        await initialize_postgres_session(connection)
    except BaseException:
        # Release a failed connection without replacing the useful first error.
        from contextlib import suppress
        with suppress(Exception):
            await connection.close(timeout=5)
        raise
    return connection
