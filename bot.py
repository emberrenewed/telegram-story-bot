import os
import asyncio
import logging
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.tl.functions.stories import GetPeerStoriesRequest
from telethon.tl.functions.contacts import ResolveUsernameRequest
from telethon.errors import (
    UsernameNotOccupiedError,
    UsernameInvalidError,
    FloodWaitError,
)
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
PHONE_NUMBER = os.getenv("PHONE_NUMBER", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

# Max parallel downloads at once
MAX_CONCURRENT = 5

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

user_client = TelegramClient("story_session", API_ID, API_HASH)


async def init_user_client():
    await user_client.start(phone=PHONE_NUMBER)
    me = await user_client.get_me()
    logger.info(f"User client logged in as: {me.first_name} ({me.id})")


def is_admin(user_id: int) -> bool:
    return ADMIN_ID == 0 or user_id == ADMIN_ID


async def resolve_username(username: str):
    try:
        result = await user_client(ResolveUsernameRequest(username))
        entity = await user_client.get_entity(result.peer)
        return entity, None
    except (UsernameNotOccupiedError, UsernameInvalidError):
        return None, f"Username @{username} not found."
    except Exception as e:
        return None, f"Error resolving @{username}: {e}"


def get_display_name(entity):
    return getattr(entity, "first_name", "") or getattr(entity, "title", "") or "Unknown"


async def send_media_file(update, file_path: Path, caption: str):
    ext = file_path.suffix.lower()
    with open(file_path, "rb") as f:
        if ext in (".mp4", ".mov", ".avi", ".mkv"):
            await update.message.reply_video(
                video=f, caption=caption,
                read_timeout=120, write_timeout=120,
            )
        elif ext in (".jpg", ".jpeg", ".png", ".webp"):
            await update.message.reply_photo(photo=f, caption=caption)
        elif ext == ".gif":
            await update.message.reply_animation(animation=f, caption=caption)
        else:
            await update.message.reply_document(document=f, caption=caption)


async def download_one(semaphore, media, dest: str):
    """Download a single media file with concurrency control."""
    async with semaphore:
        path = await user_client.download_media(media, file=dest)
        return Path(path) if path else None


# ─── Stories (parallel download) ───────────────────────────

async def fetch_and_send_stories(update: Update, username: str):
    status_msg = await update.message.reply_text(f"🔍 Searching for @{username} ...")

    entity, err = await resolve_username(username)
    if err:
        await status_msg.edit_text(err)
        return

    display_name = get_display_name(entity)
    await status_msg.edit_text(f"📥 Fetching stories for {display_name} (@{username}) ...")

    try:
        stories_result = await user_client(GetPeerStoriesRequest(peer=entity))
    except FloodWaitError as e:
        await status_msg.edit_text(f"Rate limited. Wait {e.seconds}s.")
        return
    except Exception as e:
        await status_msg.edit_text(f"Error fetching stories: {e}")
        return

    stories = stories_result.stories
    if not stories or not stories.stories:
        await status_msg.edit_text(f"No stories found for @{username}.")
        return

    story_list = stories.stories
    total = len(story_list)
    await status_msg.edit_text(f"⬇️ Downloading {total} stories...")

    # Parallel download all stories
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    file_dir = DOWNLOAD_DIR / username
    file_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    tasks = []
    story_meta = []
    for i, story in enumerate(story_list):
        if story.media is None:
            continue
        dest = str(file_dir / f"story_{i}_{ts}")
        tasks.append(download_one(semaphore, story.media, dest))
        story_meta.append((i, story))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    await status_msg.edit_text(f"📤 Sending {total} stories...")

    # Send all downloaded files
    sent_count = 0
    for (i, story), result in zip(story_meta, results):
        if isinstance(result, Exception) or result is None:
            continue
        file_path = result
        try:
            caption = f"📖 Story {i + 1}/{total} — @{username}"
            if hasattr(story, "date") and story.date:
                caption += f"\n📅 {story.date.strftime('%Y-%m-%d %H:%M UTC')}"

            await send_media_file(update, file_path, caption)
            sent_count += 1
        except Exception as e:
            logger.error(f"Error sending story {i + 1}: {e}")
        finally:
            try:
                file_path.unlink()
            except OSError:
                pass

    try:
        file_dir.rmdir()
    except OSError:
        pass

    if sent_count > 0:
        await status_msg.edit_text(f"✅ Sent {sent_count}/{total} stories from @{username}.")
    else:
        await status_msg.edit_text(f"No downloadable stories from @{username}.")


# ─── Posts (parallel download) ─────────────────────────────

async def fetch_and_send_posts(update: Update, username: str, limit: int = 20):
    status_msg = await update.message.reply_text(f"🔍 Searching for @{username} ...")

    entity, err = await resolve_username(username)
    if err:
        await status_msg.edit_text(err)
        return

    display_name = get_display_name(entity)
    await status_msg.edit_text(f"📥 Fetching posts for {display_name} (@{username}) ...")

    try:
        messages = []
        async for msg in user_client.iter_messages(entity, limit=limit):
            if msg.media:
                messages.append(msg)
    except FloodWaitError as e:
        await status_msg.edit_text(f"Rate limited. Wait {e.seconds}s.")
        return
    except Exception as e:
        await status_msg.edit_text(f"Error fetching posts: {e}")
        return

    if not messages:
        await status_msg.edit_text(f"No media posts found for @{username}.")
        return

    total = len(messages)
    await status_msg.edit_text(f"⬇️ Downloading {total} posts...")

    # Parallel download all posts
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    file_dir = DOWNLOAD_DIR / username
    file_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    tasks = []
    for i, msg in enumerate(messages):
        dest = str(file_dir / f"post_{i}_{ts}")
        tasks.append(download_one(semaphore, msg.media, dest))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    await status_msg.edit_text(f"📤 Sending {total} posts...")

    sent_count = 0
    for i, (msg, result) in enumerate(zip(messages, results)):
        if isinstance(result, Exception) or result is None:
            continue
        file_path = result
        try:
            caption = f"📌 Post {i + 1}/{total} — @{username}"
            if msg.date:
                caption += f"\n📅 {msg.date.strftime('%Y-%m-%d %H:%M UTC')}"
            if msg.text:
                preview = msg.text[:400] + "..." if len(msg.text) > 400 else msg.text
                caption += f"\n\n{preview}"
            if len(caption) > 1024:
                caption = caption[:1021] + "..."

            await send_media_file(update, file_path, caption)
            sent_count += 1
        except Exception as e:
            logger.error(f"Error sending post {i + 1}: {e}")
        finally:
            try:
                file_path.unlink()
            except OSError:
                pass

    try:
        file_dir.rmdir()
    except OSError:
        pass

    if sent_count > 0:
        await status_msg.edit_text(f"✅ Sent {sent_count}/{total} posts from @{username}.")
    else:
        await status_msg.edit_text(f"No downloadable posts from @{username}.")


# ─── All (stories + posts) ────────────────────────────────

async def fetch_all(update: Update, username: str, post_limit: int = 20):
    await fetch_and_send_stories(update, username)
    await fetch_and_send_posts(update, username, limit=post_limit)


# ─── Command Handlers ─────────────────────────────────────

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("You are not authorized.")
        return

    await update.message.reply_text(
        "Welcome! Commands:\n\n"
        "/stories username — Fetch stories\n"
        "/posts username — Fetch last 20 media posts\n"
        "/posts username 50 — Fetch last 50 posts\n"
        "/all username — Stories + posts\n\n"
        "Or just send a username to get stories."
    )


async def stories_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: /stories username")
        return
    await fetch_and_send_stories(update, context.args[0].lstrip("@").strip())


async def posts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: /posts username [limit]")
        return
    username = context.args[0].lstrip("@").strip()
    limit = 20
    if len(context.args) > 1:
        try:
            limit = max(1, min(int(context.args[1]), 100))
        except ValueError:
            pass
    await fetch_and_send_posts(update, username, limit=limit)


async def all_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: /all username [post_limit]")
        return
    username = context.args[0].lstrip("@").strip()
    limit = 20
    if len(context.args) > 1:
        try:
            limit = max(1, min(int(context.args[1]), 100))
        except ValueError:
            pass
    await fetch_all(update, username, post_limit=limit)


async def handle_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    text = update.message.text.strip().lstrip("@")
    if not text or len(text) < 4 or len(text) > 32:
        return
    if not all(c.isalnum() or c == "_" for c in text):
        return
    await fetch_and_send_stories(update, text)


async def post_init(application):
    await init_user_client()


async def post_shutdown(application):
    await user_client.disconnect()


def main():
    if not BOT_TOKEN:
        print("ERROR: BOT_TOKEN not set in .env file")
        return
    if not API_ID or not API_HASH:
        print("ERROR: API_ID and API_HASH not set in .env file")
        return
    if not PHONE_NUMBER:
        print("ERROR: PHONE_NUMBER not set in .env file")
        return

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("stories", stories_command))
    app.add_handler(CommandHandler("posts", posts_command))
    app.add_handler(CommandHandler("all", all_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_username))

    print("Bot is running... Press Ctrl+C to stop.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
