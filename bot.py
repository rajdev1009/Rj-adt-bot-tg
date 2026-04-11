"""
╔══════════════════════════════════════════════════════════════╗
║           TELEGRAM FILE STORE BOT - MAIN ENTRY              ║
║           Built with Pyrogram + MongoDB/NeonDB               ║
╚══════════════════════════════════════════════════════════════╝
"""

import asyncio
import logging
from pyrogram import Client, idle
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
    sleep_threshold=60,
)


async def startup():
    """Initialize databases and start the bot."""
    logger.info("🚀 Starting File Store Bot...")

    # Connect MongoDB
    await MongoDB.connect()
    logger.info("✅ MongoDB connected.")

    # Connect NeonDB (optional – only if NEON_URL is set)
    if Config.NEON_URL:
        await NeonDB.connect()
        logger.info("✅ NeonDB connected.")
    else:
        logger.info("ℹ️  NeonDB skipped (NEON_URL not set).")

    # Start Pyrogram
    await app.start()
    me = await app.get_me()
    logger.info(f"🤖 Bot started as @{me.username} (ID: {me.id})")

    # Persist bot username in config for link generation
    Config.BOT_USERNAME = me.username

    await idle()


async def shutdown():
    """Graceful shutdown."""
    logger.info("🛑 Shutting down...")
    await app.stop()
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
