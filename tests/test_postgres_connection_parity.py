"""No network, dotenv imports, or migration execution."""
import ast
import asyncio
import contextlib
import io
import os
from pathlib import Path
import socket
import ssl
import sys
import types
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.database_url import create_database_engine
from scripts import prepare_neon
from sqlalchemy.dialects.postgresql.asyncpg import dialect


URL = "postgresql://example:encoded%25%40@ep-example.neon.tech/example?sslmode=require"


class ConnectionParityTests(unittest.IsolatedAsyncioTestCase):
    async def test_same_url_diagnose_and_stage_one_use_identical_verified_tls(self):
        tls = ssl.create_default_context()
        driver = AsyncMock()
        driver.execute = AsyncMock()
        driver.fetchval = AsyncMock(return_value="UTC")
        connect = AsyncMock(return_value=driver)
        engine = MagicMock()
        engine.dialect.name = "postgresql"
        engine.dispose = AsyncMock()
        connection = MagicMock()
        queries = []

        async def execute(query):
            queries.append(query)
            # Models the observed case: client TLS works, backend reports false.
            value = False if "pg_stat_ssl" in query else (
                "public" if "current_schema" in query else 1
            )
            result = MagicMock()
            result.scalar_one.return_value = value
            return result

        connection.exec_driver_sql = AsyncMock(side_effect=execute)

        def construct(url, **options):
            engine.url = url
            positional, keywords = dialect().create_connect_args(url)
            keywords.update(options["connect_args"])

            async def enter():
                await connect(*positional, **keywords)
                return connection

            engine.connect.return_value.__aenter__ = AsyncMock(side_effect=enter)
            engine.connect.return_value.__aexit__ = AsyncMock(return_value=False)
            return engine

        loop = asyncio.get_running_loop()
        output = io.StringIO()
        with patch("app.database_url.ssl.create_default_context", return_value=tls), \
                patch("sqlalchemy.ext.asyncio.create_async_engine", side_effect=construct), \
                patch("sqlalchemy.event.listen"), \
                patch("asyncpg.connect", connect), \
                patch.object(loop, "getaddrinfo", AsyncMock(return_value=[
                    (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 5432))
                ])), patch.object(loop, "sock_connect", AsyncMock()), \
                patch.dict(os.environ, {"DATABASE_URL": URL}), \
                contextlib.redirect_stdout(output):
            application_engine = create_database_engine(URL)
            with patch.dict(sys.modules, {"app.database": types.SimpleNamespace(engine=application_engine)}):
                self.assertTrue(await prepare_neon.diagnose(URL))
                # Stop at the empty-database gate, before importing Alembic.
                with self.assertRaises(prepare_neon.StageFailure):
                    await prepare_neon.run()

        self.assertIn("TLS/asyncpg connection: OK", output.getvalue())
        self.assertIn("[1] PostgreSQL connection: OK", output.getvalue())
        self.assertIn("[2] Empty database check: FAIL", output.getvalue())
        self.assertFalse(any("pg_stat_ssl" in query for query in queries))
        diagnostic_options = dict(connect.call_args_list[0].kwargs)
        self.assertEqual(diagnostic_options.pop("timeout"), 10)
        self.assertEqual(diagnostic_options, connect.call_args_list[1].kwargs)
        self.assertEqual(engine.url.drivername, "postgresql+asyncpg")
        self.assertIs(diagnostic_options["ssl"], tls)
        self.assertEqual(tls.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(tls.check_hostname)
        self.assertEqual(diagnostic_options["password"], "encoded%@")
        self.assertNotIn(URL, output.getvalue())

    async def test_alembic_online_uses_shared_factory_without_running_migrations(self):
        tree = ast.parse(Path("alembic/env.py").read_text())
        function = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef)
                        and n.name == "run_async_migrations")
        engine = MagicMock()
        connection = AsyncMock()
        engine.connect.return_value.__aenter__ = AsyncMock(return_value=connection)
        engine.connect.return_value.__aexit__ = AsyncMock(return_value=False)
        engine.dispose = AsyncMock()
        factory = MagicMock(return_value=engine)
        callback = MagicMock()
        namespace = dict(os=os, create_database_engine=factory,
                         pool=types.SimpleNamespace(NullPool=object()),
                         do_run_migrations=callback)
        exec(compile(ast.Module(body=[function], type_ignores=[]), "alembic_env", "exec"), namespace)
        with patch.dict(os.environ, {"DATABASE_URL": URL}):
            await namespace["run_async_migrations"]()
        self.assertEqual(factory.call_args.args, (URL,))
        callback.assert_not_called()
        engine.dispose.assert_awaited_once()

    async def test_certificate_failure_remains_fail_closed(self):
        from app.database_url import connect_postgres
        with patch("asyncpg.connect", AsyncMock(side_effect=ssl.SSLCertVerificationError())):
            with self.assertRaises(ssl.SSLCertVerificationError):
                await connect_postgres(URL)
