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
        await bot.send_message(
            chat_id=chat_id,
            text=f"<b>#{topic.upper()}</b>",
            parse_mode=ParseMode.HTML,
        )
        for a in topic_articles:
            # Telegram caption limit is 1024 chars
            caption = f'<a href="{a["link"]}">{a["title"]}</a>\n<i>{a["author"]}</i>'
            if a.get("summary"):
                caption += f'\n\n{a["summary"]}...'

            if a.get("image"):
                try:
                    await bot.send_photo(
                        chat_id=chat_id,
                        photo=a["image"],
                        caption=caption[:1024],
                        parse_mode=ParseMode.HTML,
                    )
                    continue
                except Exception:
                    pass  # Fall through to text if image fails

            await bot.send_message(
                chat_id=chat_id,
                text=caption,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=False,
            )
