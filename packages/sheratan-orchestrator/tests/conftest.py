"""Pytest configuration and fixtures for orchestrator tests"""
import pytest
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Ensure test database is configured
if not os.getenv("DATABASE_URL"):
    os.environ["DATABASE_URL"] = "postgresql://sheratan:sheratan@localhost:5432/sheratan_test"


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def setup_database():
    """Setup and teardown database for each test"""
    from sheratan_store.database import init_db, close_db
    
    # Initialize database tables
    try:
        await init_db()
    except Exception as e:
        print(f"Warning: Could not initialize database: {e}")
    
    yield
    
    # Cleanup
    try:
        await close_db()
    except Exception as e:
        print(f"Warning: Could not close database: {e}")
