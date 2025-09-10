import os
import io
import traceback
import gc

def _load_env(file_name: str = ".env") -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base_dir, file_name)
    if not os.path.isfile(path):
        return  # Silently ignore if no .env present
    try:
        with io.open(path, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith('#'):
                    continue
                # Support KEY=VALUE (VALUE may contain =, so split once)
                if '=' not in line:
                    continue
                key, value = line.split('=', 1)
                key = key.strip()
                # Strip optional surrounding quotes for common cases
                value = value.strip().strip('"').strip("'")
                # Do not overwrite existing environment variables
                if key and key not in os.environ:
                    os.environ[key] = value
    except Exception:
        # Keep failures silent to avoid breaking runtime; debugging via traceback.
        traceback.print_exc()

def _unload_env() -> None:
    # Remove all variables loaded from .env to avoid leaking into other parts of the app
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base_dir, ".env")
        if not os.path.isfile(path):
            return
        with io.open(path, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' not in line:
                    continue
                key, _ = line.split('=', 1)
                key = key.strip()
                if key and key in os.environ:
                    del os.environ[key]
        gc.collect()  # Force garbage collection to clean up any lingering references
    except Exception:
        traceback.print_exc()

def get_test_guild_id() -> int:
    _load_env()
    _test_guild_id = os.environ.get('TEST_GUILD_ID')
    if not _test_guild_id:
        raise RuntimeError("TEST_GUILD_ID not found in environment")
    try:
        return int(_test_guild_id)
    except ValueError:
        raise RuntimeError("TEST_GUILD_ID must be an integer")
    finally:
        _unload_env()
        
def get_greenlist() -> list[int]:
    _load_env()
    _greenlist_users = os.environ.get('GREENLIST')
    if _greenlist_users:
        try:
            return [int(uid.strip()) for uid in _greenlist_users.split(',') if uid.strip()]
        except ValueError:
            raise RuntimeError("GREENLIST must be a comma-separated list of integers")
        finally:
            _unload_env()
    return []

def get_bot_token() -> str:
    _load_env()
    _bot_token = os.environ.get('DISCORD_BOT_TOKEN')
    if not _bot_token:
        raise RuntimeError("DISCORD_BOT_TOKEN not found in environment")
    _unload_env()
    return _bot_token

def get_suno_token() -> str:
    _load_env()
    _suno_token = os.environ.get('SUNO_API_KEY')
    if not _suno_token:
        raise RuntimeError("SUNO_API_KEY not found in environment variables")
    _unload_env()
    return _suno_token

def get_webhook(key: str) -> str:
    _load_env()
    _webhook = os.environ.get(key)
    if not _webhook:
        raise RuntimeError(f"{key} not found in environment variables")
    _unload_env()
    return _webhook

