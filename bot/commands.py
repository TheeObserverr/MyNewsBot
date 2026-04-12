import asyncio
import os

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from .fetcher import fetch_articles
from .sender import send_articles
from .storage import load_config, load_seen, mark_seen, save_config


# ── Command handlers ──────────────────────────────────────────────────────────

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "<b>Available commands:</b>\n\n"
        "/topics — List current topics\n"
        "/settopics python, AI, finance — Replace all topics\n"
        "/addtopic topic — Add a single topic\n"
        "/removetopic topic — Remove a topic\n"
        "/addsource url — Add a custom RSS feed\n"
        "/removesource url — Remove a custom RSS feed\n"
        "/sources — List custom RSS feeds\n"
        "/fetch — Manually pull articles now\n"
        "/setmax 5 — Max articles per topic (default 3)\n"
        "/settime 8 — Set daily send hour in UTC (0–23)\n"
        "/help — Show this message"
    )
    await update.message.reply_html(text)


async def cmd_topics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = load_config()
    topics = config["topics"]
    if topics:
        body = "\n".join(f"• {t}" for t in topics)
        await update.message.reply_text(f"Current topics:\n{body}")
    else:
        await update.message.reply_text("No topics set. Use /addtopic to add some.")


async def cmd_settopics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /settopics python, AI, finance")
        return
    topics = [t.strip() for t in " ".join(context.args).split(",") if t.strip()]
    config = load_config()
    config["topics"] = topics
    save_config(config)
    body = "\n".join(f"• {t}" for t in topics)
    await update.message.reply_text(f"Topics updated:\n{body}")


async def cmd_addtopic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /addtopic machine-learning")
        return
    topic = " ".join(context.args).strip()
    config = load_config()
    if topic in config["topics"]:
        await update.message.reply_text(f'"{topic}" is already in your topics.')
    else:
        config["topics"].append(topic)
        save_config(config)
        await update.message.reply_text(f'Added topic: "{topic}"')


async def cmd_removetopic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /removetopic machine-learning")
        return
    topic = " ".join(context.args).strip()
    config = load_config()
    if topic not in config["topics"]:
        await update.message.reply_text(f'Topic "{topic}" not found.')
    else:
        config["topics"].remove(topic)
        save_config(config)
        await update.message.reply_text(f'Removed topic: "{topic}"')


async def cmd_addsource(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /addsource https://example.com/rss")
        return
    url = context.args[0].strip()
    config = load_config()
    sources = config.setdefault("custom_sources", [])
    if url in sources:
        await update.message.reply_text("That source is already added.")
    else:
        sources.append(url)
        save_config(config)
        await update.message.reply_text(f"Added source:\n{url}")


async def cmd_removesource(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /removesource https://example.com/rss")
        return
    url = context.args[0].strip()
    config = load_config()
    sources = config.get("custom_sources", [])
    if url not in sources:
        await update.message.reply_text("Source not found.")
    else:
        sources.remove(url)
        save_config(config)
        await update.message.reply_text(f"Removed source:\n{url}")


async def cmd_sources(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = load_config()
    sources = config.get("custom_sources", [])
    if sources:
        body = "\n".join(f"• {s}" for s in sources)
        await update.message.reply_text(f"Custom RSS sources:\n{body}")
    else:
        await update.message.reply_text(
            "No custom sources yet. Use /addsource <url> to add one."
        )


async def cmd_setmax(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /setmax 5")
        return
    val = int(context.args[0])
    if val < 1 or val > 20:
        await update.message.reply_text("Please choose a number between 1 and 20.")
        return
    config = load_config()
    config["max_articles_per_topic"] = val
    save_config(config)
    await update.message.reply_text(f"Max articles per topic set to {val}.")


async def cmd_settime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /settime 8\nProvide the hour in UTC (0–23).")
        return
    hour = int(context.args[0])
    if hour < 0 or hour > 23:
        await update.message.reply_text("Hour must be between 0 and 23 (UTC).")
        return
    config = load_config()
    config["send_hour_utc"] = hour
    save_config(config)
    await update.message.reply_text(
        f"Send time set to {hour:02d}:00 UTC.\n"
        f"Tip: UTC+2 → subtract 2 from your local time to get UTC."
    )


async def cmd_fetch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Fetching articles...")
    config = load_config()
    seen = load_seen()
    articles = fetch_articles(
        topics=config["topics"],
        custom_sources=config.get("custom_sources", []),
        seen_ids=seen,
        max_per_topic=config.get("max_articles_per_topic", 3),
    )
    if articles:
        await send_articles(articles, chat_id=str(update.effective_chat.id))
        mark_seen([a["id"] for a in articles])
    else:
        await update.message.reply_text("No new articles found.")


# ── Polling runner ────────────────────────────────────────────────────────────

async def handle_commands(duration: int = 120):
    """Poll Telegram for commands for `duration` seconds, then exit."""
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = Application.builder().token(token).build()

    for name, handler in [
        ("help", cmd_help),
        ("topics", cmd_topics),
        ("settopics", cmd_settopics),
        ("addtopic", cmd_addtopic),
        ("removetopic", cmd_removetopic),
        ("addsource", cmd_addsource),
        ("removesource", cmd_removesource),
        ("sources", cmd_sources),
        ("setmax", cmd_setmax),
        ("settime", cmd_settime),
        ("fetch", cmd_fetch),
    ]:
        app.add_handler(CommandHandler(name, handler))

    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=False)

    print(f"[commands] Listening for {duration}s...")
    await asyncio.sleep(duration)

    await app.updater.stop()
    await app.stop()
    await app.shutdown()
    print("[commands] Done.")
