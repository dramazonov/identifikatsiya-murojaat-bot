"""Runtime configuration; constructing settings never contacts Telegram."""
import os
import re
from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Settings:
    mode: str = "polling"
    redis_url: str = ""
    base_url: str = ""
    path: str = "/telegram/webhook"
    secret: str = ""
    host: str = "0.0.0.0"
    port: int = 8080

    @classmethod
    def from_env(cls):
        return cls(
            mode=os.getenv("BOT_MODE", "polling"),
            redis_url=os.getenv("REDIS_URL", ""),
            base_url=os.getenv("WEBHOOK_BASE_URL", ""),
            path=os.getenv("WEBHOOK_PATH", "/telegram/webhook"),
            secret=os.getenv("WEBHOOK_SECRET", ""),
            host=os.getenv("WEB_SERVER_HOST", "0.0.0.0"),
            port=int(os.getenv("WEB_SERVER_PORT", "8080")),
        )

    def validate(self, database_url):
        if self.mode not in {"polling", "webhook"}:
            raise ValueError("BOT_MODE must be polling or webhook")
        if self.mode == "webhook":
            if not database_url.startswith("postgresql+asyncpg://"):
                raise ValueError("Webhook production requires PostgreSQL + asyncpg")
            if not self.redis_url.startswith(("redis://", "rediss://")):
                raise ValueError("Webhook production requires REDIS_URL")
            url = urlsplit(self.base_url)
            if (url.scheme != "https" or not url.hostname or url.username or url.password
                    or url.path not in {"", "/"} or url.query or url.fragment):
                raise ValueError("WEBHOOK_BASE_URL must be an HTTPS origin")
            if not re.fullmatch(r"/[A-Za-z0-9_/-]+", self.path) or self.path == "/health":
                raise ValueError("WEBHOOK_PATH must be a distinct absolute URL path")
            if not re.fullmatch(r"[A-Za-z0-9_-]{32,256}", self.secret):
                raise ValueError("WEBHOOK_SECRET must contain 32-256 URL-safe characters")
            if not 1 <= self.port <= 65535:
                raise ValueError("Invalid WEB_SERVER_PORT")
