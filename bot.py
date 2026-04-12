"""
╔══════════════════════════════════════════════════════════════╗
║           TELEGRAM FILE STORE BOT - MAIN ENTRY              ║
║   Credit: RAJ DEV                                            ║
╚══════════════════════════════════════════════════════════════╝
"""

import asyncio
import logging
import sys
from aiohttp import web
from pyrogram import Client, idle
from pyrogram.errors import (
    FloodWait, ApiIdInvalid,
    AccessTokenExpired, AccessTokenInvalid,
)
from config import Config
from database.mongodb import MongoDB
from database.neondb import NeonDB

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("FileStoreBot")

app = Client(
    name="FileStoreBot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    plugins={"root": "handlers"},
    sleep_threshold=300,
)


# ── Health check server ────────────────────────────────────────
async def health_handler(request):
    return web.Response(text="OK", status=200)

async def start_health_server():
    import os
    port = int(os.environ.get("PORT", 8080))
    server = web.Application()
    server.router.add_get("/", health_handler)
    server.router.add_get("/health", health_handler)
    runner = web.AppRunner(server)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", port).start()
    logger.info(f"✅ Health check server on port {port}")


# ══════════════════════════════════════════════════════════════
#  STARTUP
# ══════════════════════════════════════════════════════════════

async def startup():
    logger.info("🚀 Starting File Store Bot... | Credit: RAJ DEV")

    await MongoDB.connect()
    logger.info("✅ MongoDB connected.")

    if Config.NEON_URL:
        await NeonDB.connect()
        logger.info("✅ NeonDB connected.")
    else:
        logger.info("ℹ️  NeonDB skipped.")

    await start_health_server()

    # Telegram connect
    max_retries = 5
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"🔌 Connecting to Telegram... (attempt {attempt}/{max_retries})")
            await app.start()
            break
        except FloodWait as e:
            wait = e.value + 10
            logger.warning(f"⏳ FloodWait {e.value}s — sleeping {wait}s...")
            await asyncio.sleep(wait)
        except (AccessTokenInvalid, AccessTokenExpired) as e:
            logger.critical(f"❌ Bad BOT_TOKEN: {e}")
            sys.exit(1)
        except ApiIdInvalid:
            logger.critical("❌ Bad API_ID/API_HASH.")
            sys.exit(1)
        except Exception as e:
            if "already connected" in str(e).lower():
                try:
                    await app.stop()
                except Exception:
                    pass
                await asyncio.sleep(3)
            else:
                if attempt == max_retries:
                    logger.critical(f"❌ Failed: {e}")
                    sys.exit(1)
                wait = 15 * attempt
                logger.error(f"⚠️ Retry in {wait}s: {e}")
                await asyncio.sleep(wait)

    me = await app.get_me()
    Config.BOT_USERNAME = me.username
    logger.info(f"🤖 Bot: @{me.username} (ID: {me.id})")
    logger.info(f"📦 DB_CHANNEL     : {Config.DB_CHANNEL}")
    logger.info(f"📢 UPDATE_CHANNEL : {Config.UPDATE_CHANNEL}")

    await idle()


async def shutdown():
    logger.info("🛑 Shutting down...")
    try:
        await app.stop()
    except Exception:
        pass
    await MongoDB.disconnect()
    if Config.NEON_URL:
        await NeonDB.disconnect()
    logger.info("👋 Stopped.")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(startup())
    except KeyboardInterrupt:
        loop.run_until_complete(shutdown())
