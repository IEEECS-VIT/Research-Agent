import os
import pytest
from dotenv import load_dotenv

load_dotenv(override=True)

os.environ["GEMINI_API_KEY"] = os.environ.get("GEMINI_API_KEY", "test-key")
os.environ["DATABASE_URL"] = "sqlite:///./test.db"


@pytest.fixture(autouse=True)
def reset_env():
    yield
