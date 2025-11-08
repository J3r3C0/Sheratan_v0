"""Setup configuration for sheratan-cli"""
from setuptools import setup, find_packages

setup(
    name="sheratan-cli",
    version="0.1.0",
    description="CLI tools for Sheratan administration and maintenance",
    packages=find_packages(),
    install_requires=[
        "click>=8.1.7",
        "python-dotenv>=1.0.0",
        "httpx>=0.27.0",
        "alembic>=1.13.1",
        "sqlalchemy>=2.0.25",
        "asyncpg>=0.29.0",
    ],
    entry_points={
        "console_scripts": [
            "sheratan=sheratan_cli.cli:cli",
        ],
    },
    python_requires=">=3.9",
)
