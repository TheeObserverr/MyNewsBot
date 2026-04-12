import os

from telegram import Bot
from telegram.constants import ParseMode


async def send_articles(articles: list[dict], chat_id: str = None):
    bot = Bot(token=os.environ["TELEGRAM_BOT_TOKEN"])
    chat_id = chat_id or os.environ["TELEGRAM_CHAT_ID"]

    if not articles:
        await bot.send_message(chat_id=chat_id, text="No new articles found today.")
        return

    # Group by topic
    by_topic: dict[str, list] = {}
    for a in articles:
        by_topic.setdefault(a["topic"], []).append(a)

    header = (
        f"<b>Daily News Digest</b>\n"
        f"{len(articles)} new article{'s' if len(articles) != 1 else ''} "
        f"across {len(by_topic)} topic{'s' if len(by_topic) != 1 else ''}"
    )
    await bot.send_message(chat_id=chat_id, text=header, parse_mode=ParseMode.HTML)

    for topic, topic_articles in by_topic.items():
        lines = [f"<b>#{topic.upper()}</b>\n"]
        for a in topic_articles:
            lines.append(f'<a href="{a["link"]}">{a["title"]}</a>')
            lines.append(f'<i>{a["author"]}</i>')
            if a["summary"]:
                lines.append(a["summary"] + "...")
            lines.append("")

        await bot.send_message(
            chat_id=chat_id,
            text="\n".join(lines),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
