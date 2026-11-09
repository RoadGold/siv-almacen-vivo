"""Configuración de la aplicación, leída de variables de entorno (archivo .env)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR / ".env", ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "SIV · Almacén Vivo"
    app_version: str = "0.1.0"
    api_prefix: str = "/api/v1"

    # --- Base de datos -------------------------------------------------
    database_url: str = "postgresql+psycopg://siv:siv@localhost:5432/siv_almacen_vivo"
    db_echo: bool = False
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # --- Autenticación -------------------------------------------------
    secret_key: str = "cambia-esta-clave-en-produccion-local"
    access_token_expire_minutes: int = 480
    cookie_secure: bool = False
    cookie_samesite: str = "lax"

    # --- Aplicación ----------------------------------------------------
    environment: str = "local"
    timezone: str = "America/Lima"
    moneda: str = "S/"
    nombre_negocio: str = "Almacén Vivo"
    warehouse_name: str = "Almacén principal"

    # --- CORS / red local ----------------------------------------------
    allowed_origins: str = "http://localhost:8080,http://127.0.0.1:8080,http://localhost:5173,http://127.0.0.1:5173"

    @property
    def allowed_origin_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def is_testing(self) -> bool:
        return self.environment == "test"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
