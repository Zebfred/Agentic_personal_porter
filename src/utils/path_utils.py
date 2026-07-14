from src.utils.logging_config import setup_logger
logger = setup_logger(__name__)
import os
import platform
from pathlib import Path
from dotenv import load_dotenv


def is_windows() -> bool:
    """Detects whether the current platform is Windows."""
    return platform.system() == "Windows"


def get_project_root() -> Path:
    """
    Returns the absolute path to the project root directory.
    Assumes this file is located at project_root/src/utils/path_utils.py

    Works identically on Windows and Unix — pathlib handles separator
    normalization automatically.
    """
    # .parent of utils is src, .parent of src is project_root
    return Path(__file__).resolve().parent.parent.parent


def _get_fallback_env_paths() -> list[Path]:
    """
    Returns platform-specific fallback paths for the .auth/.env file.

    On Windows:  Checks %USERPROFILE%\\.auth\\.env
    On Unix:     Checks /etc/porter/.env and /.auth/.env (container root)

    Why: The old code hardcoded Unix-absolute paths (Path("/.auth/.env"))
    which resolve to C:\\.auth\\.env on Windows — always dead code.
    """
    if is_windows():
        user_home = Path(os.environ.get("USERPROFILE", "C:\\Users\\Default"))
        return [
            user_home / ".auth" / ".env",
            user_home / ".auth" / "Porter_auth_env",
        ]
    else:
        return [
            Path("/etc/porter/.env"),
            Path("/.auth/.env"),
            Path("/.auth/Porter_auth_env"),
        ]


def load_env_vars():
    """
    Locates the .auth/.env file and loads it into the environment.

    Search order:
      1. <project_root>/.auth/.env   (cross-platform, always checked first)
      2. Platform-specific fallback paths (see _get_fallback_env_paths)
    """
    root = get_project_root()
    possible_paths = [
        root / ".auth" / ".env",
        *_get_fallback_env_paths(),
    ]

    loaded = False
    for env_path in possible_paths:
        if env_path.exists():
            load_dotenv(dotenv_path=env_path)
            logger.info(f"Loaded environment variables from: {env_path}")
            loaded = True
            break

    if not loaded:
        # We'll use a warning here instead of a raise so we don't
        # crash scripts that don't actually need the .env
        logger.warning(
            "⚠️ .env file not found at any expected path. Searched: %s",
            [str(p) for p in possible_paths],
        )


def get_auth_file(filename: str) -> str:
    """
    Returns the absolute path to a specific file in the .auth folder.
    Uses pathlib for cross-platform path construction.
    """
    root = get_project_root()
    return str(root / ".auth" / filename)