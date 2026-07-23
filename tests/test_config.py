from app.core.config import get_settings


def test_settings_defaults():
    settings = get_settings()
    assert settings.app_name == "Research Alignment Agent"
    assert settings.app_version == "1.0.0"
    assert settings.port == 8000


def test_settings_env_override(monkeypatch):
    monkeypatch.setenv("APP_NAME", "Test Agent")
    monkeypatch.setenv("PORT", "9090")
    monkeypatch.setenv("CORS_ORIGINS", '["*"]')
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.app_name == "Test Agent"
    assert settings.port == 9090
    assert settings.cors_origins == ["*"]
    get_settings.cache_clear()
