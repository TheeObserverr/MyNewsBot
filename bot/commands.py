import asyncio
import os

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from .fetcher import fetch_articles
from .sender import send_articles
from .storage import (
    add_user, get_owner_id, get_user_config, is_allowed, is_owner,
    load_seen, mark_seen, remove_user, save_user_config, set_owner_id,
)


# ── Auth helpers ──────────────────────────────────────────────────────────────

async def _reject(update: Update):
    await update.message.reply_text("Unauthorized.")


# ── Commands ──────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)

    # First ever user becomes the owner
    if not get_owner_id():
        set_owner_id(chat_id)
        add_user(chat_id)
        await update.message.reply_html(
            f"Welcome! You are the <b>owner</b> of this bot.\n"
            f"Your chat ID is <code>{chat_id}</code>\n\n"
            f"Use /help to see available commands."
        )
        return

    if is_allowed(chat_id):
        await update.message.reply_text("You already have access. Use /help.")
        return

    await update.message.reply_html(
        f"Hi! This bot is private.\n"
        f"Ask the owner to run:\n<code>/adduser {chat_id}</code>"
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if not is_allowed(chat_id):
        return await _reject(update)

    owner_commands = ""
    if is_owner(chat_id):
        owner_commands = (
            "\n<b>Owner only:</b>\n"
            "/adduser 123456789 — Grant a friend access\n"
            "/removeuser 123456789 — Revoke access\n"
        )

    text = (
        "<b>Available commands:</b>\n\n"
        "/topics — List your topics\n"
        "/settopics python, AI, finance — Replace all topics\n"
        "/addtopic topic — Add a topic\n"
        "/removetopic topic — Remove a topic\n"
        "/addsource url — Add a custom RSS feed\n"
        "/removesource url — Remove a custom RSS feed\n"
        "/sources — List custom RSS feeds\n"
        "/fetch — Manually pull articles now\n"
        "/setmax 5 — Max articles per topic (default 3)\n"
        "/settime 8 — Set daily send hour in UTC (0–23)\n"
        + owner_commands +
        "/help — Show this message"
    )
    await update.message.reply_html(text)


async def cmd_topics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if not is_allowed(chat_id):
        return await _reject(update)
    topics = get_user_config(chat_id)["topics"]
    body = "\n".join(f"• {t}" for t in topics) if topics else "None set."
    await update.message.reply_text(f"Your topics:\n{body}")


async def cmd_settopics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if not is_allowed(chat_id):
        return await _reject(update)
    if not context.args:
        await update.message.reply_text("Usage: /settopics python, AI, finance")
        return
    topics = [t.strip() for t in " ".join(context.args).split(",") if t.strip()]
    cfg = get_user_config(chat_id)
    cfg["topics"] = topics
    save_user_config(chat_id, cfg)
    await update.message.reply_text("Topics updated:\n" + "\n".join(f"• {t}" for t in topics))


async def cmd_addtopic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if not is_allowed(chat_id):
        return await _reject(update)
    if not context.args:
        await update.message.reply_text("Usage: /addtopic machine-learning")
        return
    topic = " ".join(context.args).strip()
    cfg = get_user_config(chat_id)
    if topic in cfg["topics"]:
        await update.message.reply_text(f'"{topic}" is already in your topics.')
    else:
        cfg["topics"].append(topic)
        save_user_config(chat_id, cfg)
        await update.message.reply_text(f'Added: "{topic}"')


async def cmd_removetopic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if not is_allowed(chat_id):
        return await _reject(update)
    if not context.args:
        await update.message.reply_text("Usage: /removetopic machine-learning")
        return
    topic = " ".join(context.args).strip()
    cfg = get_user_config(chat_id)
    if topic not in cfg["topics"]:
        await update.message.reply_text(f'Topic "{topic}" not found.')
    else:
        cfg["topics"].remove(topic)
        save_user_config(chat_id, cfg)
        await update.message.reply_text(f'Removed: "{topic}"')


async def cmd_addsource(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if not is_allowed(chat_id):
        return await _reject(update)
    if not context.args:
        await update.message.reply_text("Usage: /addsource https://example.com/rss")
        return
    url = context.args[0].strip()
    cfg = get_user_config(chat_id)
    sources = cfg.setdefault("custom_sources", [])
    if url in sources:
        await update.message.reply_text("That source is already added.")
    else:
        sources.append(url)
        save_user_config(chat_id, cfg)
        await update.message.reply_text(f"Added source:\n{url}")


async def cmd_removesource(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if not is_allowed(chat_id):
        return await _reject(update)
    if not context.args:
        await update.message.reply_text("Usage: /removesource https://example.com/rss")
        return
    url = context.args[0].strip()
    cfg = get_user_config(chat_id)
    sources = cfg.get("custom_sources", [])
    if url not in sources:
        await update.message.reply_text("Source not found.")
    else:
        sources.remove(url)
        save_user_config(chat_id, cfg)
        await update.message.reply_text(f"Removed source:\n{url}")


async def cmd_sources(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if not is_allowed(chat_id):
        return await _reject(update)
    sources = get_user_config(chat_id).get("custom_sources", [])
    if sources:
        await update.message.reply_text("Custom sources:\n" + "\n".join(f"• {s}" for s in sources))
    else:
        await update.message.reply_text("No custom sources. Use /addsource <url>.")


async def cmd_setmax(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if not is_allowed(chat_id):
        return await _reject(update)
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /setmax 5")
        return
    val = int(context.args[0])
    if val < 1 or val > 20:
        await update.message.reply_text("Please choose between 1 and 20.")
        return
    cfg = get_user_config(chat_id)
    cfg["max_articles_per_topic"] = val
    save_user_config(chat_id, cfg)
    await update.message.reply_text(f"Max articles per topic set to {val}.")


async def cmd_settime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if not is_allowed(chat_id):
        return await _reject(update)
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /settime 8  (UTC hour, 0–23)")
        return
    hour = int(context.args[0])
    if hour < 0 or hour > 23:
        await update.message.reply_text("Hour must be between 0 and 23 (UTC).")
        return
    cfg = get_user_config(chat_id)
    cfg["send_hour_utc"] = hour
    save_user_config(chat_id, cfg)
    await update.message.reply_text(f"Your digest will be sent at {hour:02d}:00 UTC.")


async def cmd_fetch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if not is_allowed(chat_id):
        return await _reject(update)
    await update.message.reply_text("Fetching your articles...")
    cfg = get_user_config(chat_id)
    seen = load_seen(chat_id)
    articles = fetch_articles(
        topics=cfg["topics"],
        custom_sources=cfg.get("custom_sources", []),
        seen_ids=seen,
        max_per_topic=cfg.get("max_articles_per_topic", 3),
    )
    if articles:
        await send_articles(articles, chat_id=chat_id)
        mark_seen(chat_id, [a["id"] for a in articles])
    else:
        await update.message.reply_text("No new articles found.")


# ── Owner-only: user management ───────────────────────────────────────────────

async def cmd_adduser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if not is_owner(chat_id):
        return await _reject(update)
    if not context.args:
        await update.message.reply_text("Usage: /adduser 123456789")
        return
    new_id = context.args[0].strip()
    if is_allowed(new_id):
        await update.message.reply_text(f"{new_id} already has access.")
    else:
        add_user(new_id)
        await update.message.reply_text(f"Access granted to {new_id}.")


async def cmd_removeuser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if not is_owner(chat_id):
        return await _reject(update)
    if not context.args:
        await update.message.reply_text("Usage: /removeuser 123456789")
        return
    target = context.args[0].strip()
    if target == chat_id:
        await update.message.reply_text("You can't remove yourself.")
        return
    remove_user(target)
    await update.message.reply_text(f"Access removed for {target}.")


# ── Polling runner ────────────────────────────────────────────────────────────

async def handle_commands(duration: int = 120):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = Application.builder().token(token).build()

    for name, handler in [
        ("start", cmd_start),
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
        ("adduser", cmd_adduser),
        ("removeuser", cmd_removeuser),
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
