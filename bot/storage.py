import json
import os

CONFIG_FILE = "config.json"
SEEN_FILE = "seen_articles.json"

DEFAULT_USER = {
    "topics": ["python", "artificial-intelligence", "data-science"],
    "custom_sources": [],
    "max_articles_per_topic": 3,
    "send_hour_utc": 7,
}


# ── Config ────────────────────────────────────────────────────────────────────

def _load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {"owner_id": "", "users": {}}


def _save_config(config: dict):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


# ── User management ───────────────────────────────────────────────────────────

def get_owner_id() -> str:
    return _load_config().get("owner_id", "")


def set_owner_id(chat_id: str):
    config = _load_config()
    config["owner_id"] = str(chat_id)
    _save_config(config)


def is_owner(chat_id: str) -> bool:
    return str(chat_id) == get_owner_id()


def is_allowed(chat_id: str) -> bool:
    return str(chat_id) in _load_config().get("users", {})


def get_all_user_ids() -> list[str]:
    return list(_load_config().get("users", {}).keys())


def add_user(chat_id: str):
    config = _load_config()
    config["users"][str(chat_id)] = DEFAULT_USER.copy()
    _save_config(config)


def remove_user(chat_id: str):
    config = _load_config()
    config["users"].pop(str(chat_id), None)
    _save_config(config)
    # Also clear their seen history
    seen = _load_seen_all()
    seen.pop(str(chat_id), None)
    _save_seen_all(seen)


# ── Per-user config ───────────────────────────────────────────────────────────

def get_user_config(chat_id: str) -> dict:
    users = _load_config().get("users", {})
    return users.get(str(chat_id), DEFAULT_USER.copy())


def save_user_config(chat_id: str, user_config: dict):
    config = _load_config()
    config["users"][str(chat_id)] = user_config
    _save_config(config)


# ── Seen articles (per-user) ──────────────────────────────────────────────────

def _load_seen_all() -> dict:
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return json.load(f)
    return {}


def _save_seen_all(seen: dict):
    with open(SEEN_FILE, "w") as f:
        json.dump(seen, f, indent=2)


def load_seen(chat_id: str) -> list[str]:
    return _load_seen_all().get(str(chat_id), [])


def mark_seen(chat_id: str, article_ids: list[str]):
    seen = _load_seen_all()
    uid = str(chat_id)
    existing = set(seen.get(uid, []))
    existing.update(article_ids)
    seen[uid] = list(existing)[-500:]  # cap at 500
    _save_seen_all(seen)
