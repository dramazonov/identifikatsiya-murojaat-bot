"""Manual empty-Neon bootstrap. Never imports bot startup or reads SQLite."""
import asyncio
import logging
import os
import sys
import socket
import ssl
from contextlib import contextmanager, redirect_stdout, redirect_stderr, suppress
from pathlib import Path


async def diagnose(raw):
    """Connect only: no dotenv, application engine, SQL, or migrations.

    Error messages are allowlisted summaries, never interpolated exception text.
    FAIL also covers checks not reached after an earlier failure.
    """
    report = {
        "URL parsed successfully": "NO",
        "Driver normalized to postgresql+asyncpg": "NO",
        "sslmode detected": "absent",
        "channel_binding present": "NO",
        "DNS resolution": "FAIL",
        "TCP connection to port 5432": "FAIL",
        "TLS/asyncpg connection": "FAIL",
        "Exception CLASS only": "None",
        "Sanitized exception message": "None",
        "Failure category": "none",
    }
    stage = "URL parsing"
    message = "Invalid or unsupported connection URL; details redacted."
    try:
        from sqlalchemy.engine import make_url
        from app.database_url import database_options

        url = make_url(raw or "")
        report["URL parsed successfully"] = "YES"
        mode = url.query.get("sslmode")
        report["sslmode detected"] = (
            mode if isinstance(mode, str) and mode in {
                "disable", "allow", "prefer", "require", "verify-ca", "verify-full"
            } else "present (redacted)" if mode is not None else "absent"
        )
        report["channel_binding present"] = "YES" if "channel_binding" in url.query else "NO"
        if url.drivername not in {"postgres", "postgresql", "postgresql+asyncpg"}:
            raise ValueError()
        url = url.set(drivername="postgresql+asyncpg")
        report["Driver normalized to postgresql+asyncpg"] = "YES"
        if not url.host or not url.host.endswith(".neon.tech") or url.port not in (None, 5432):
            message = "A Neon endpoint on port 5432 is required; endpoint redacted."
            raise ValueError()
        stage = "TLS"
        message = "Unsupported TLS configuration; check SSL options and channel_binding (require is unsupported)."
        url, args = database_options(raw)
        # Reject extras instead of allowing DSN options to override endpoint/security.
        if url.query:
            stage = "URL parsing"
            message = "Unsupported URL query options; values redacted."
            raise ValueError()
        stage = "DNS"
        message = "DNS lookup failed; endpoint and original error redacted. Later checks were not run."
        loop = asyncio.get_running_loop()
        addresses = await asyncio.wait_for(
            loop.getaddrinfo(url.host, 5432, type=socket.SOCK_STREAM), 10
        )
        if not addresses:
            raise socket.gaierror()
        report["DNS resolution"] = "OK"
        stage = "network"
        message = "TCP connection failed; endpoint and original error redacted. TLS check was not run."

        async def probe():
            last_error = None
            for family, kind, proto, _, address in addresses:
                with socket.socket(family, kind, proto) as sock:
                    sock.setblocking(False)
                    try:
                        await asyncio.wait_for(loop.sock_connect(sock, address), 3)
                        return
                    except OSError as exc:
                        last_error = exc
            raise last_error or OSError()

        await asyncio.wait_for(probe(), 10)
        report["TCP connection to port 5432"] = "OK"
        stage = "database"
        message = "Database connection failed; server details and original error redacted."
        from app.database_url import connect_postgres

        conn = await connect_postgres(raw)
        try:
            report["TLS/asyncpg connection"] = "OK"
        finally:
            await conn.close(timeout=5)
    except Exception as exc:
        sqlstate = getattr(exc, "sqlstate", "") or ""
        if isinstance(exc, ssl.SSLError):
            stage = "TLS"
            message = "TLS handshake or certificate verification failed; details redacted."
        elif sqlstate.startswith("28"):
            stage = "authentication"
            message = "Authentication rejected; credentials and server details redacted."
        elif isinstance(exc, socket.gaierror):
            stage = "DNS"
        elif stage == "database" and isinstance(exc, (OSError, TimeoutError)):
            stage = "network"
            message = "Connection interrupted or timed out; endpoint and original error redacted."
        # Class names are identifiers, but allowlist modules as defense in depth.
        cls = type(exc)
        report["Exception CLASS only"] = (
            cls.__name__ if cls.__module__.split(".")[0] in {
                "builtins", "socket", "ssl", "asyncpg", "sqlalchemy"
            } and cls.__name__.isascii() and cls.__name__.isidentifier() else "Exception"
        )
        report["Sanitized exception message"] = message
        report["Failure category"] = stage
    for key, value in report.items():
        print(f"{key}: {value}")
    return report["Failure category"] == "none"


STAGES = (
    "PostgreSQL connection",
    "Empty database check",
    "Alembic upgrade head",
    "Alembic revision verification",
    "Schema/index/FK/unique verification",
    "PostgreSQL integration validation",
    "Test-record cleanup",
)


class StageFailure(Exception):
    """Already reported safely; the CLI must exit without a traceback."""


class _DiscardOutput:
    def write(self, text):
        return len(text)

    def flush(self):
        pass


@contextmanager
def quiet_output():
    # Do not retain raw library output, SQL, or connection details in a buffer.
    previous = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        with redirect_stdout(_DiscardOutput()), redirect_stderr(_DiscardOutput()):
            yield
    finally:
        logging.disable(previous)


# Exact, application-owned messages only. Never output arbitrary exception text.
_SAFE_MESSAGES = frozenset({
    "Temporary DATABASE_URL is required",
    "Use the direct Neon PostgreSQL endpoint",
    "Engine does not match the explicit PostgreSQL URL",
    "Local migration head differs from e13f7a2c9b41",
    "Connection check failed", "TLS is required", "Expected public schema",
    "Database is not empty; bootstrap refused", "Unexpected baseline revision",
    "Missing tables", "Missing unique constraint", "Missing or incorrect unique index",
    "Missing FK", "Schema drift", "Non-UTC session", "Cleanup incomplete",
    "Invalid temporary number", "Test identity collision; rerun validation",
    "User update failed", "Location lost", "Profile lost", "Missing INSERT coverage",
    "Duplicate public number", "Wrong public format", "Claim race",
    "Duplicate/missing user", "Constraint did not reject invalid record",
    "Rollback injection did not run", "Insert not rolled back",
    "Minimal contact user not rolled back",
    "Database revision mismatch; run the explicit migration job",
    "Invalid database URL (details omitted)",
    "channel_binding is unsupported by asyncpg; use verified TLS without this parameter",
    "Specify only one SSL option", "SSL configuration must require verified TLS",
    "Unsupported SSL URL option; system CA trust is used",
    "Empty security URL option",
})


def safe_failure(exc, number):
    category = ("connection", "database", "migration", "revision",
                "schema", "integration", "cleanup")[number - 1]
    message = "Stage operation failed; untrusted error details redacted."
    # SQLAlchemy frequently wraps the useful driver error in .orig or a cause.
    chain, seen = [], set()
    current = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        chain.append(current)
        current = getattr(current, "orig", None) or current.__cause__
    for error in chain:
        state = getattr(error, "sqlstate", None) or getattr(error, "pgcode", None) or ""
        if isinstance(error, ssl.SSLError):
            category, message = "TLS", "TLS handshake or certificate verification failed; details redacted."
        elif isinstance(error, socket.gaierror):
            category, message = "DNS", "DNS resolution failed; endpoint redacted."
        elif isinstance(error, (TimeoutError, ConnectionError, OSError)):
            category, message = "network", "Network connection or local I/O failed; details redacted."
        elif isinstance(error, ImportError):
            category, message = "dependency", "Required module or import is unavailable; paths and details redacted."
        elif isinstance(state, str) and state.startswith("28"):
            category, message = "authentication", "PostgreSQL authentication rejected; credentials and endpoint redacted."
        elif state == "3D000":
            category, message = "database", "Requested database does not exist; database name redacted."
        elif state == "42501":
            category, message = "permissions", "PostgreSQL denied permission for the stage operation; details redacted."
        elif isinstance(state, str) and state.startswith("23"):
            category, message = "database", "Database constraint violation; record and constraint details redacted."
        elif (type(error) in (RuntimeError, ValueError) and error.args
              and isinstance(error.args[0], str) and error.args[0] in _SAFE_MESSAGES):
            message = error.args[0]
            if type(error) is ValueError:
                category = "configuration"
    cls = type(exc)
    name = cls.__name__ if (
        cls.__module__.split(".")[0] in {"builtins", "ssl", "socket", "sqlalchemy", "asyncpg", "alembic"}
        and cls.__name__.isascii() and cls.__name__.isidentifier()
    ) else "Exception"
    return name, category, message


@contextmanager
def stage(number):
    label = f"[{number}] {STAGES[number - 1]}"
    print(f"{label}: START", flush=True)
    try:
        with quiet_output():
            yield
    except (Exception, SystemExit, KeyboardInterrupt, asyncio.CancelledError) as exc:
        name, category, message = safe_failure(exc, number)
        print(f"{label}: FAIL", flush=True)
        print(f"Exception CLASS: {name}", flush=True)
        print(f"Safe failure category: {category}", flush=True)
        print(f"Sanitized error message: {message}", flush=True)
        raise StageFailure() from None
    else:
        print(f"{label}: OK", flush=True)


async def run(*, resume_validation=False):
    engine = None
    cleanup_tasks = []
    try:
        with stage(1):
            # Validate before any module can load dotenv or create an engine.
            raw = os.environ.get("DATABASE_URL")
            if not raw:
                raise RuntimeError("Temporary DATABASE_URL is required")
            from app.database_url import database_options
            url, args = database_options(raw)
            if (url.drivername != "postgresql+asyncpg" or not url.host
                    or not url.host.endswith(".neon.tech") or "-pooler" in url.host):
                raise RuntimeError("Use the direct Neon PostgreSQL endpoint")
            from app.database import engine
            if engine.url != url or engine.dialect.name != "postgresql":
                raise RuntimeError("Engine does not match the explicit PostgreSQL URL")
            async with engine.connect() as conn:
                if (await conn.exec_driver_sql("SELECT 1")).scalar_one() != 1:
                    raise RuntimeError("Connection check failed")
                # The shared factory requires verified TLS for Neon. A successful
                # handshake proves client TLS; pg_stat_ssl sees only the backend
                # side of a proxy and cannot verify our client transport.
        if not resume_validation:
            with stage(2):
                async with engine.connect() as conn:
                    if (await conn.exec_driver_sql("SELECT current_schema()")).scalar_one() != "public":
                        raise RuntimeError("Expected public schema")
                    occupied = (await conn.exec_driver_sql("""
                        SELECT EXISTS (
                            SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                            WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
                              AND n.nspname NOT LIKE 'pg_toast%'
                              AND c.relkind IN ('r', 'p', 'v', 'm', 'S', 'f')
                        )
                    """)).scalar_one()
                    if occupied:
                        raise RuntimeError("Database is not empty; bootstrap refused")
            with stage(3):
                from alembic.config import Config
                from alembic.script import ScriptDirectory
                from app.migrate import migrate
                cfg = Config(str(Path(__file__).resolve().parent.parent / "alembic.ini"))
                if ScriptDirectory.from_config(cfg).get_heads() != ["e13f7a2c9b41"]:
                    raise RuntimeError("Local migration head differs from e13f7a2c9b41")
                await migrate()
        with stage(4):
            from app.database import verify_schema
            await verify_schema()
            async with engine.connect() as conn:
                if (await conn.exec_driver_sql("SELECT version_num FROM alembic_version")).scalar_one() != "e13f7a2c9b41":
                    raise RuntimeError("Unexpected baseline revision")
        with stage(5):
            from scripts.validate_postgres import inspect_schema
            async with engine.connect() as conn:
                await conn.run_sync(inspect_schema)
                if (await conn.exec_driver_sql("SHOW timezone")).scalar_one() != "UTC":
                    raise RuntimeError("Non-UTC session")
        with stage(6):
            from scripts.validate_postgres import validate_services
            await validate_services(cleanup_tasks=cleanup_tasks)
        with stage(7):
            for cleanup in cleanup_tasks:
                await cleanup()
            await engine.dispose()
            engine = None
    finally:
        if engine is not None:
            # Resource release only. Never continue to another stage after failure,
            # and never mask the original stage failure with a disposal exception.
            with quiet_output(), suppress(Exception):
                await engine.dispose()


def main():
    if sys.argv[1:] == ["--diagnose"]:
        logging.disable(logging.CRITICAL)
        raise SystemExit(0 if asyncio.run(diagnose(os.environ.get("DATABASE_URL"))) else 1)
    resume_validation = sys.argv[1:] == ["--resume-validation"]
    if not resume_validation and sys.argv[1:] != ["--confirm-empty-neon-and-test-records"]:
        raise SystemExit("Explicit empty-Neon and test-record confirmation required")
    # Suppress library logs and raw exception text, including import failures.
    logging.disable(logging.CRITICAL)
    try:
        asyncio.run(run(resume_validation=resume_validation))
    except StageFailure:
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
