import hashlib
import re
from datetime import datetime, timedelta

import feedparser


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


def _medium_url(topic: str) -> str:
    return f"https://medium.com/feed/tag/{topic.lower().replace(' ', '-')}"


def fetch_articles(
    topics: list[str],
    custom_sources: list[str] = None,
    seen_ids: list[str] = None,
    max_per_topic: int = 3,
) -> list[dict]:
    seen_set = set(seen_ids or [])
    cutoff = datetime.now() - timedelta(days=7)
    articles = []

    # Build (url, label) pairs — Medium tags + custom RSS feeds
    sources = [(_medium_url(t), t) for t in topics]
    for url in (custom_sources or []):
        sources.append((url, "custom"))

    for url, topic in sources:
        try:
            feed = feedparser.parse(url)
            count = 0
            for entry in feed.entries:
                if count >= max_per_topic:
                    break

                link = getattr(entry, "link", "")
                article_id = hashlib.md5(link.encode()).hexdigest()

                if article_id in seen_set:
                    continue

                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6])
                    if pub_date < cutoff:
                        continue

                summary = _strip_html(getattr(entry, "summary", ""))[:300]

                articles.append(
                    {
                        "id": article_id,
                        "title": getattr(entry, "title", "No title"),
                        "link": link,
                        "summary": summary,
                        "topic": topic,
                        "author": getattr(entry, "author", "Unknown"),
                    }
                )
                seen_set.add(article_id)
                count += 1
        except Exception as e:
            print(f"[fetcher] Error fetching {url}: {e}")

    return articles
