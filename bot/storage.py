import json
import os

CONFIG_FILE = "config.json"
SEEN_FILE = "seen_articles.json"

DEFAULT_CONFIG = {
    "topics": ["python", "artificial-intelligence", "data-science"],
    "custom_sources": [],
    "max_articles_per_topic": 3,
}


def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return DEFAULT_CONFIG.copy()


def save_config(config: dict):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def load_seen() -> list[str]:
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return json.load(f)
    return []


def save_seen(seen: list[str]):
    # Cap at 500 to avoid repo bloat
    with open(SEEN_FILE, "w") as f:
        json.dump(list(set(seen))[-500:], f, indent=2)


def mark_seen(article_ids: list[str]):
    seen = load_seen()
    seen.extend(article_ids)
    save_seen(seen)
