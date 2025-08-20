from setuptools import setup, find_packages

setup(
    name="saegim-backend",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi==0.104.1",
        "uvicorn==0.24.0",
        "sqlalchemy>=2.0,<2.1",
        "sqlmodel==0.0.14",
        "alembic==1.13.1",
        "asyncpg==0.29.0",
        "greenlet==3.0.3",
        "pydantic-settings==2.1.0",
        "python-dotenv==1.0.0",
    ],
)
