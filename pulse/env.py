from __future__ import annotations

from pulse.config import find_project_root


def load_dotenv() -> None:
    """Load environment variables from project-root ``.env`` if present."""
    try:
        from dotenv import load_dotenv as _load
    except ImportError:
        return
    env_path = find_project_root() / ".env"
    if env_path.is_file():
        _load(env_path)
