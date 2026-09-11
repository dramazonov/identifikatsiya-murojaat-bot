"""Mock-only preparation tests; run with unittest, without pytest DB fixtures."""
import asyncio
import contextlib
import io
import logging
import os
import sys
import types
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from scripts import prepare_neon as runner
from app.database_url import database_options

URL = "postgresql://privateuser:privatepassword@privatehost.neon.tech/privatedb?sslmode=require"
SECRET = URL + " privateuser privatepassword privatehost.neon.tech token-secret"


class PreparationTests(unittest.IsolatedAsyncioTestCase):
    async def exercise(self, failure=None, occupied=False):
        output = io.StringIO()
        calls = []
        cleanup = AsyncMock()

        def hit(number):
            calls.append(number)
            print(SECRET)
            print(SECRET, file=sys.stderr)
            logging.error(SECRET)
            if failure == number:
                raise RuntimeError(SECRET)

        async def sql(query):
            result = MagicMock()
            if query == "SELECT 1":
                hit(1)
                value = 1
            elif "pg_stat_ssl" in query:
                value = False  # Proxy backend status must not be used as client TLS proof.
            elif "current_schema" in query:
                hit(2)
                value = "public"
            elif "SELECT EXISTS" in query:
                value = occupied
            elif "alembic_version" in query:
                value = "d7c2f4189a6e"
            elif "SHOW timezone" in query:
                value = "UTC"
            else:
                self.fail("Unexpected SQL")
            result.scalar_one.return_value = value
            return result

        async def migrate():
            hit(3)

        async def verify():
            hit(4)

        async def inspect(callback):
            hit(5)

        async def services(*, cleanup_tasks):
            hit(6)
            cleanup_tasks.append(cleanup)

        async def clean():
            hit(7)

        cleanup.side_effect = clean
        conn = MagicMock()
        conn.exec_driver_sql = AsyncMock(side_effect=sql)
        conn.run_sync = AsyncMock(side_effect=inspect)
        engine = MagicMock()
        engine.url = database_options(URL)[0]
        engine.dialect.name = "postgresql"
        engine.connect.return_value.__aenter__ = AsyncMock(return_value=conn)
        engine.connect.return_value.__aexit__ = AsyncMock(return_value=False)
        engine.dispose = AsyncMock()
        scripts = MagicMock()
        scripts.from_config.return_value.get_heads.return_value = ["d7c2f4189a6e"]
        modules = {
            "app.database": types.SimpleNamespace(engine=engine, verify_schema=verify),
            "app.migrate": types.SimpleNamespace(migrate=migrate),
            "alembic.config": types.SimpleNamespace(Config=MagicMock()),
            "alembic.script": types.SimpleNamespace(ScriptDirectory=scripts),
            "scripts.validate_postgres": types.SimpleNamespace(inspect_schema=object(), validate_services=services),
        }
        with patch.dict(sys.modules, modules), patch.dict(os.environ, {"DATABASE_URL": URL}), \
                contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            if failure or occupied:
                with self.assertRaises(runner.StageFailure):
                    await runner.run()
            else:
                await runner.run()
        text = output.getvalue()
        for secret in (URL, "privateuser", "privatepassword", "privatehost", "privatedb", "token-secret"):
            self.assertNotIn(secret, text)
        engine.dispose.assert_awaited_once()
        return text, calls, cleanup

    async def test_all_seven_stages_in_exact_order(self):
        text, calls, cleanup = await self.exercise()
        expected = [f"[{i}] {name}: {status}" for i, name in enumerate(runner.STAGES, 1)
                    for status in ("START", "OK")]
        self.assertEqual(text.splitlines(), expected)
        self.assertEqual(calls, list(range(1, 8)))
        cleanup.assert_awaited_once()

    async def test_each_failure_stops_immediately_and_is_redacted(self):
        for number in range(1, 8):
            with self.subTest(stage=number):
                text, calls, cleanup = await self.exercise(failure=number)
                self.assertEqual(calls, list(range(1, number + 1)))
                self.assertIn(f"[{number}] {runner.STAGES[number - 1]}: FAIL", text)
                self.assertNotIn(f"[{number}] {runner.STAGES[number - 1]}: OK", text)
                self.assertIn("Exception CLASS: RuntimeError", text)
                self.assertIn("Sanitized error message:", text)
                self.assertNotIn("Traceback", text)
                self.assertEqual(len(text.splitlines()), 2 * number + 3)
                if number < 7:
                    cleanup.assert_not_awaited()

    async def test_occupied_database_blocks_migration(self):
        text, calls, _ = await self.exercise(occupied=True)
        self.assertEqual(calls, [1, 2])
        self.assertIn("Database is not empty; bootstrap refused", text)

    async def test_missing_url_fails_stage_one_before_application_imports(self):
        output = io.StringIO()
        with patch.dict(os.environ, {}, clear=True), contextlib.redirect_stdout(output):
            with self.assertRaises(runner.StageFailure):
                await runner.run()
        self.assertIn("[1] PostgreSQL connection: FAIL", output.getvalue())
        self.assertNotIn("[2]", output.getvalue())


class FailureTests(unittest.TestCase):
    def test_wrapped_authentication_is_useful_and_safe(self):
        import asyncpg
        from sqlalchemy.exc import OperationalError
        exc = OperationalError(SECRET, {"password": SECRET}, asyncpg.InvalidPasswordError(SECRET))
        name, category, message = runner.safe_failure(exc, 1)
        self.assertEqual(name, "OperationalError")
        self.assertEqual(category, "authentication")
        self.assertNotIn(SECRET, message)

    def test_safe_categories(self):
        import socket
        import ssl
        import asyncpg
        for exc, expected in [
            (socket.gaierror(SECRET), "DNS"),
            (ssl.SSLError(SECRET), "TLS"),
            (TimeoutError(SECRET), "network"),
            (ModuleNotFoundError(SECRET), "dependency"),
            (asyncpg.InsufficientPrivilegeError(SECRET), "permissions"),
            (asyncpg.InvalidCatalogNameError(SECRET), "database"),
        ]:
            self.assertEqual(runner.safe_failure(exc, 3)[1], expected)

    def test_import_and_system_exit_output_cannot_escape(self):
        for exc in (ImportError(SECRET), SystemExit(SECRET)):
            output = io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                with self.assertRaises(runner.StageFailure):
                    with runner.stage(3):
                        print(SECRET)
                        raise exc
            self.assertNotIn(SECRET, output.getvalue())
            self.assertIn("[3] Alembic upgrade head: FAIL", output.getvalue())

    def test_cli_failure_exits_nonzero_without_generic_message(self):
        with patch.object(sys, "argv", ["prepare_neon", "--confirm-empty-neon-and-test-records"]), \
                patch.object(runner, "run", AsyncMock(side_effect=runner.StageFailure)), \
                patch.object(runner.logging, "disable"):
            with self.assertRaises(SystemExit) as caught:
                runner.main()
            self.assertEqual(caught.exception.code, 1)


class CleanupTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_validation_cleanup_can_be_deferred_without_database_imports(self):
        # Execute the actual function with fake dependencies. Importing the module
        # normally would load the application database and dotenv.
        import ast
        import secrets
        import uuid
        from pathlib import Path

        tree = ast.parse(Path("scripts/validate_postgres.py").read_text())
        function = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef)
                        and n.name == "validate_services")
        for deferred in (False, True):
            with self.subTest(deferred=deferred):
                result = MagicMock()
                result.all.return_value = []
                session = MagicMock()
                session.execute = AsyncMock(return_value=result)
                session.begin.return_value.__aenter__ = AsyncMock()
                session.begin.return_value.__aexit__ = AsyncMock(return_value=False)
                factory = MagicMock()
                factory.return_value.__aenter__ = AsyncMock(return_value=session)
                factory.return_value.__aexit__ = AsyncMock(return_value=False)
                event = MagicMock()
                event.contains.return_value = False
                namespace = dict(
                    secrets=secrets, uuid=uuid, async_session=factory,
                    Appeal=MagicMock(), Suggestion=MagicMock(), AdminContact=MagicMock(),
                    User=MagicMock(), event=event, select=MagicMock(), delete=MagicMock(),
                    require=lambda condition, message: self.assertTrue(condition, message),
                    PHONE_VERIFICATION_SOURCE_TELEGRAM="TELEGRAM_CONTACT",
                    save_user=AsyncMock(side_effect=RuntimeError("Injected failure")),
                )
                exec(compile(ast.Module(body=[function], type_ignores=[]), "validate_services", "exec"), namespace)
                tasks = [] if deferred else None
                with contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaisesRegex(RuntimeError, "Injected failure"):
                        await namespace["validate_services"](cleanup_tasks=tasks)
                    if deferred:
                        self.assertEqual(session.execute.await_count, 1)
                        self.assertEqual(len(tasks), 1)
                        await tasks[0]()
                # Collision check, four scoped deletes, and cleanup verification.
                self.assertEqual(session.execute.await_count, 6)
