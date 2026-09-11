from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent


def test_compose_exposes_only_caddy_and_gates_migration():
    compose = yaml.safe_load((ROOT / "docker-compose.production.yml").read_text())
    services = compose["services"]
    assert services["postgres"]["image"].startswith("postgres:16-")
    for name in ("bot", "postgres", "redis", "migrate"):
        assert not services[name].get("ports")
    assert services["caddy"]["ports"] == ["80:80", "443:443"]
    assert compose["networks"]["backend"]["internal"] is True
    assert services["postgres"]["networks"] == services["redis"]["networks"] == ["backend"]
    assert services["bot"]["depends_on"]["migrate"]["condition"] == "service_completed_successfully"
    assert services["migrate"]["command"] == ["python", "-m", "app.migrate"]
    for name in ("bot", "postgres", "redis", "caddy"):
        assert services[name]["healthcheck"]
        assert services[name]["restart"] == "unless-stopped"


def test_image_excludes_local_secrets_and_template_is_empty():
    dockerfile = (ROOT / "Dockerfile").read_text()
    assert "COPY . " not in dockerfile
    assert "USER bot" in dockerfile
    assert (ROOT / ".dockerignore").read_text().startswith("*\n")
    values = dict(line.split("=", 1) for line in (ROOT / ".env.production.example").read_text().splitlines()
                  if line and not line.startswith("#"))
    for key in ("BOT_TOKEN", "POSTGRES_PASSWORD", "DATABASE_URL", "WEBHOOK_SECRET", "ADMIN_IDS"):
        assert values[key] == ""
