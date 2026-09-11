"""Run with unittest to avoid application/database pytest fixtures."""
import asyncio
import contextlib
import io
import socket
import ssl
import sys
import unittest
from unittest.mock import AsyncMock, patch

from scripts.prepare_neon import diagnose, main


URL = "postgresql://privateuser:privatepassword@privatehost.neon.tech/privatedb?sslmode=require"


class DiagnosticsTests(unittest.IsolatedAsyncioTestCase):
    async def check(self, raw=URL, dns_error=None, tcp_error=None, connection_error=None):
        output = io.StringIO()
        loop = asyncio.get_running_loop()
        connection = AsyncMock()
        connection.execute = AsyncMock()
        connection.fetchval = AsyncMock(return_value="UTC")
        connect = AsyncMock(return_value=connection, side_effect=connection_error)
        with patch.object(loop, "getaddrinfo", AsyncMock(
            return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 5432))],
            side_effect=dns_error,
        )) as dns, patch.object(loop, "sock_connect", AsyncMock(side_effect=tcp_error)) as tcp, \
                patch("asyncpg.connect", connect), contextlib.redirect_stdout(output):
            result = await diagnose(raw)
        text = output.getvalue()
        self.assertEqual(len(text.splitlines()), 10)
        for secret in ("privateuser", "privatepassword", "privatehost", "privatedb", "127.0.0.1"):
            self.assertNotIn(secret, text)
        return result, text, dns, tcp, connect, connection

    async def test_success_connects_with_verified_tls_and_no_queries(self):
        result, text, _, _, connect, conn = await self.check()
        self.assertTrue(result)
        self.assertIn("TLS/asyncpg connection: OK", text)
        self.assertEqual(connect.call_args.kwargs["ssl"].verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(connect.call_args.kwargs["ssl"].check_hostname)
        self.assertEqual([c[0] for c in conn.mock_calls], ["execute", "fetchval", "close"])
        conn.execute.assert_awaited_once_with("SET SESSION TIME ZONE 'UTC'")
        conn.fetchval.assert_awaited_once_with("SHOW timezone")
        conn.close.assert_awaited_once_with(timeout=5)

    async def test_bad_url_does_not_connect(self):
        result, text, dns, tcp, connect, _ = await self.check("privatepassword")
        self.assertFalse(result)
        self.assertIn("Failure category: URL parsing", text)
        dns.assert_not_called()
        tcp.assert_not_called()
        connect.assert_not_called()

    async def test_binding_requirement_reported_before_network(self):
        _, text, dns, _, _, _ = await self.check(URL + "&channel_binding=require")
        self.assertIn("channel_binding present: YES", text)
        self.assertIn("Failure category: TLS", text)
        dns.assert_not_called()

    async def test_unknown_ssl_value_redacted(self):
        _, text, _, _, _, _ = await self.check(URL.replace("require", "privatepassword"))
        self.assertIn("sslmode detected: present (redacted)", text)

    async def test_failure_categories_and_redaction(self):
        import asyncpg
        for field, error, category in [
            ("dns_error", socket.gaierror("privatehost"), "DNS"),
            ("tcp_error", ConnectionRefusedError("privatehost"), "network"),
            ("connection_error", ssl.SSLCertVerificationError("privatehost"), "TLS"),
            ("connection_error", asyncpg.InvalidPasswordError("privatepassword"), "authentication"),
            ("connection_error", asyncpg.InvalidCatalogNameError("privatedb"), "database"),
        ]:
            with self.subTest(category=category):
                result, text, _, _, connect, _ = await self.check(**{field: error})
                self.assertFalse(result)
                self.assertIn("Failure category: " + category, text)
                self.assertIn("Exception CLASS only: " + type(error).__name__, text)
                if field != "connection_error":
                    connect.assert_not_called()

    async def test_diagnostics_does_not_import_mutating_modules(self):
        import builtins
        original = builtins.__import__

        def guarded(name, *args, **kwargs):
            if name in {"app.database", "app.config", "app.migrate", "dotenv", "scripts.validate_postgres"} or name.startswith("alembic"):
                self.fail("Diagnostic attempted an application or migration import")
            return original(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=guarded):
            await self.check()


class CommandTests(unittest.TestCase):
    def test_diagnose_dispatch_never_bootstraps(self):
        with patch.object(sys, "argv", ["prepare_neon", "--diagnose"]), \
                patch("scripts.prepare_neon.diagnose", AsyncMock(return_value=True)), \
                patch("scripts.prepare_neon.run") as bootstrap, \
                patch("scripts.prepare_neon.logging.disable"):
            with self.assertRaises(SystemExit) as exc:
                main()
            self.assertEqual(exc.exception.code, 0)
            bootstrap.assert_not_called()


if __name__ == "__main__":
    unittest.main()
