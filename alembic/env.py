"""Alembic 환경 설정"""
from logging.config import fileConfig
from sqlmodel import SQLModel
from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context
from app.core.config import get_settings

# Alembic Config 객체
config = context.config

# Python 로깅을 위한 Alembic 설정 파일 해석
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 애플리케이션 설정에서 데이터베이스 URL 가져오기
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)

# 모델의 MetaData 객체
target_metadata = SQLModel.metadata

def run_migrations_offline() -> None:
    """오프라인 모드에서 마이그레이션 실행"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """온라인 모드에서 마이그레이션 실행"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()