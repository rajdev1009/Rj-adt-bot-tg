"""
╔══════════════════════════════════════════════════════════════╗
║           TELEGRAM FILE STORE BOT - MAIN ENTRY              ║
║           Built with Pyrogram + MongoDB/NeonDB               ║
╚══════════════════════════════════════════════════════════════╝
"""

import asyncio
import logging
import sys
from pyrogram import Client, idle
from pyrogram.errors import FloodWait, ApiIdInvalid, AccessTokenExpired, AccessTokenInvalid
from config import Config
from database.mongodb import MongoDB
from database.neondb import NeonDB

# ── Logging Setup ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("FileStoreBot")

# ── Pyrogram Client ────────────────────────────────────────────
app = Client(
    name="FileStoreBot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    plugins={"root": "handlers"},
    # sleep_threshold: Pyrogram will auto-sleep on FloodWait up to this many
    # seconds instead of raising an exception. Set high so routine floods
    # during normal operation (sendMessage, etc.) are handled transparently.
    sleep_threshold=300,
)


async def startup():
    """
    Initialize databases and start the bot.

    FloodWait handling strategy:
      • If Telegram returns FLOOD_WAIT on the initial auth call, we log the
        required wait time clearly and sleep inside the process — this stops
        the container from exiting, which would cause the orchestrator to
        restart it immediately and compound the flood timer.
      • Fatal credential errors (invalid token / invalid API id) exit with
        code 1 immediately because retrying won't help.
    """
    logger.info("🚀 Starting File Store Bot...")

    # ── Connect databases first (no Telegram calls yet) ───────
    await MongoDB.connect()
    logger.info("✅ MongoDB connected.")

    if Config.NEON_URL:
        await NeonDB.connect()
        logger.info("✅ NeonDB connected.")
    else:
        logger.info("ℹ️  NeonDB skipped (NEON_URL not set).")

    # ── Start Pyrogram with FloodWait-aware retry loop ─────────
    max_retries = 5
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"🔌 Connecting to Telegram... (attempt {attempt}/{max_retries})")
            await app.start()
            break  # success — exit the retry loop

        except FloodWait as e:
            wait = e.value + 10   # add 10s buffer on top of Telegram's requirement
            logger.warning(
                f"⏳ Telegram FloodWait: must wait {e.value}s before authenticating.\n"
                f"   Sleeping {wait}s inside the process to avoid restart loops.\n"
                f"   The bot will resume automatically — do NOT restart the container."
            )
            # Sleep here (not exit) so the container stays alive and the
            # orchestrator doesn't immediately relaunch and extend the flood.
            await asyncio.sleep(wait)
            # After sleeping, loop retries app.start()

        except (AccessTokenInvalid, AccessTokenExpired) as e:
            logger.critical(
                f"❌ Invalid or expired BOT_TOKEN: {e}\n"
                "   Get a new token from @BotFather and update your BOT_TOKEN env var."
            )
            sys.exit(1)

        except ApiIdInvalid:
            logger.critical(
                "❌ Invalid API_ID / API_HASH combination.\n"
                "   Check your credentials at https://my.telegram.org"
            )
            sys.exit(1)

        except Exception as e:
            if attempt == max_retries:
                logger.critical(f"❌ Failed to connect after {max_retries} attempts: {e}")
                sys.exit(1)
            wait = 15 * attempt   # 15s, 30s, 45s, 60s back-off
            logger.error(f"⚠️  Connection error: {e}. Retrying in {wait}s...")
            await asyncio.sleep(wait)

    # ── Bot is now connected ───────────────────────────────────
    me = await app.get_me()
    logger.info(f"🤖 Bot started as @{me.username} (ID: {me.id})")
    Config.BOT_USERNAME = me.username

    await idle()


async def shutdown():
    """Graceful shutdown — close Telegram session and DB connections."""
    logger.info("🛑 Shutting down...")
    try:
        await app.stop()
    except Exception:
        pass
    await MongoDB.disconnect()
    if Config.NEON_URL:
        await NeonDB.disconnect()
    logger.info("👋 Bot stopped cleanly.")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(startup())
    except KeyboardInterrupt:
        loop.run_until_complete(shutdown())
