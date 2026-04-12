import argparse
import asyncio
from datetime import datetime, timezone

from bot.commands import handle_commands
from bot.fetcher import fetch_articles
from bot.sender import send_articles
from bot.storage import get_all_user_ids, get_user_config, load_seen, mark_seen


async def run_fetch_for_user(chat_id: str, force: bool = False):
    cfg = get_user_config(chat_id)
    send_hour = cfg.get("send_hour_utc", 7)

    if not force and datetime.now(timezone.utc).hour != send_hour:
        print(f"[fetch] Skipping {chat_id} — not their send time (send_hour_utc={send_hour})")
        return

    seen = load_seen(chat_id)
    articles = fetch_articles(
        topics=cfg["topics"],
        custom_sources=cfg.get("custom_sources", []),
        seen_ids=seen,
        max_per_topic=cfg.get("max_articles_per_topic", 3),
    )

    if articles:
        print(f"[fetch] Sending {len(articles)} articles to {chat_id}...")
        await send_articles(articles, chat_id=chat_id)
        mark_seen(chat_id, [a["id"] for a in articles])
    else:
        print(f"[fetch] No new articles for {chat_id}.")


async def run_fetch(force: bool = False):
    user_ids = get_all_user_ids()
    if not user_ids:
        print("[fetch] No users registered yet.")
        return
    for chat_id in user_ids:
        await run_fetch_for_user(chat_id, force=force)


async def main():
    parser = argparse.ArgumentParser(description="News Telegram Bot")
    parser.add_argument(
        "--mode",
        choices=["fetch", "listen", "both"],
        default="both",
        help="fetch = send news | listen = handle commands | both = fetch then listen",
    )
    parser.add_argument(
        "--listen-duration",
        type=int,
        default=120,
        help="Seconds to poll for commands (default: 120)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force fetch regardless of send_hour_utc",
    )
    args = parser.parse_args()

    if args.mode in ("fetch", "both"):
        await run_fetch(force=args.force)

    if args.mode in ("listen", "both"):
        await handle_commands(duration=args.listen_duration)


if __name__ == "__main__":
    asyncio.run(main())
