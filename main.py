import argparse
import asyncio

from bot.commands import handle_commands
from bot.fetcher import fetch_articles
from bot.sender import send_articles
from bot.storage import load_config, load_seen, mark_seen


async def run_fetch():
    config = load_config()
    seen = load_seen()

    print(f"[fetch] Topics: {config['topics']}")
    articles = fetch_articles(
        topics=config["topics"],
        custom_sources=config.get("custom_sources", []),
        seen_ids=seen,
        max_per_topic=config.get("max_articles_per_topic", 3),
    )

    if articles:
        print(f"[fetch] Sending {len(articles)} articles...")
        await send_articles(articles)
        mark_seen([a["id"] for a in articles])
        print("[fetch] Done.")
    else:
        print("[fetch] No new articles found.")


async def main():
    parser = argparse.ArgumentParser(description="News Telegram Bot")
    parser.add_argument(
        "--mode",
        choices=["fetch", "listen", "both"],
        default="both",
        help="fetch = send news only | listen = handle commands only | both = fetch then listen",
    )
    parser.add_argument(
        "--listen-duration",
        type=int,
        default=120,
        help="Seconds to poll for commands (default: 120)",
    )
    args = parser.parse_args()

    if args.mode in ("fetch", "both"):
        await run_fetch()

    if args.mode in ("listen", "both"):
        await handle_commands(duration=args.listen_duration)


if __name__ == "__main__":
    asyncio.run(main())
