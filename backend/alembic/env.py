"""Entorno de Alembic para Chorum (Fase 2).

La URL de la base se toma de ``Settings.database_url`` (única fuente de config, así compose y
``.env`` inyectan Postgres sin editar archivos). El metadata objetivo es el de SQLModel, con los
modelos de ``app/db/models.py`` importados para que autogenerate los descubra.
``render_as_batch`` habilita ALTERs seguros en SQLite para migraciones futuras.
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

from alembic import context
from app.config import get_settings
from app.db import models  # noqa: F401 - importa los modelos para poblar SQLModel.metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# La URL viene de settings, no del .ini (que queda con un placeholder inerte).
config.set_main_option("sqlalchemy.url", get_settings().database_url)

target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """Migraciones en modo offline: emite SQL a partir de la URL, sin abrir conexión."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Migraciones en modo online: abre conexión y corre las migraciones contra la DB."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
