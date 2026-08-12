import pytest

from app.core.config import Settings


def test_refuses_dev_secret_in_production():
    with pytest.raises(ValueError):
        Settings(env="production", jwt_secret="dev-only-secret-change-in-production")


def test_accepts_real_secret_in_production():
    Settings(env="production", jwt_secret="a-real-generated-secret")


def test_dev_secret_allowed_outside_production():
    Settings(env="development", jwt_secret="dev-only-secret-change-in-production")


def test_cors_origins_splits_and_strips_comma_separated_list():
    settings = Settings(frontend_origin="https://tawla.tn, https://www.tawla.tn ,")
    assert settings.cors_origins == ["https://tawla.tn", "https://www.tawla.tn"]


def test_cors_origins_defaults_to_local_frontend():
    settings = Settings(frontend_origin="http://localhost:3000")
    assert settings.cors_origins == ["http://localhost:3000"]
