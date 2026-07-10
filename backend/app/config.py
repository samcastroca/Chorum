"""Configuración de la aplicación, leída desde el entorno (`.env`).

Los valores sensibles (API keys) se leen desde variables de entorno y **nunca** se loguean
ni se persisten en la base de datos de grafos (invariante 5 de CLAUDE.md).
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración global de la aplicación.

    Los campos se pueblan desde variables de entorno (o un archivo `.env`). Los defaults
    apuntan a un entorno de desarrollo local.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # Orígenes CORS como cadena separada por comas (ej. "http://localhost:5173,http://x").
    # Se expone ya parseada en `cors_origins_list`.
    cors_origins: str = "http://localhost:5173"

    # SQLite por defecto en desarrollo local; docker compose inyecta la URL de Postgres.
    database_url: str = "sqlite:///./chorum.db"

    @property
    def cors_origins_list(self) -> list[str]:
        """`cors_origins` normalizada a lista, descartando entradas vacías."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Devuelve la configuración (cacheada) de la aplicación."""
    return Settings()
