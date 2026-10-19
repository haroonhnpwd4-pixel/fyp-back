from pathlib import Path

from app.core.config import BACKEND_ENV_FILE


def test_backend_env_file_is_independent_of_working_directory():
    assert BACKEND_ENV_FILE == Path(__file__).resolve().parents[1] / ".env"
