"""
╔══════════════════════════════════════════════════════════════╗
║           TELEGRAM FILE STORE BOT - MAIN ENTRY              ║
║           Built with Pyrogram + MongoDB/NeonDB               ║
╚══════════════════════════════════════════════════════════════╝
"""

import asyncio
import logging
import sys
from aiohttp import web
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
    sleep_threshold=300,
)

# ══════════════════════════════════════════════════════════════
#  HEALTH CHECK SERVER
#  Koyeb / Render require an HTTP endpoint to confirm the
#  instance is alive. Runs on PORT (default 8080).
# ══════════════════════════════════════════════════════════════

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
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"✅ Health check server running on port {port}")


# ══════════════════════════════════════════════════════════════
#  STARTUP
# ══════════════════════════════════════════════════════════════

async def startup():
    logger.info("🚀 Starting File Store Bot...")

    # ── Connect databases ──────────────────────────────────────
    await MongoDB.connect()
    logger.info("✅ MongoDB connected.")

    if Config.NEON_URL:
        await NeonDB.connect()
        logger.info("✅ NeonDB connected.")
    else:
        logger.info("ℹ️  NeonDB skipped (NEON_URL not set).")

    # ── Start health check server (for Koyeb/Render) ──────────
    await start_health_server()

    # ── Connect to Telegram with FloodWait-aware retry ─────────
    max_retries = 5
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"🔌 Connecting to Telegram... (attempt {attempt}/{max_retries})")
            await app.start()
            break  # success

        except FloodWait as e:
            wait = e.value + 10
            logger.warning(
                f"⏳ Telegram FloodWait: {e.value}s required.\n"
                f"   Sleeping {wait}s — do NOT restart the container."
            )
            await asyncio.sleep(wait)
            # No need to stop — app never fully started

        except (AccessTokenInvalid, AccessTokenExpired) as e:
            logger.critical(f"❌ Invalid/expired BOT_TOKEN: {e}")
            sys.exit(1)

        except ApiIdInvalid:
            logger.critical("❌ Invalid API_ID/API_HASH. Check https://my.telegram.org")
            sys.exit(1)

        except Exception as e:
            err = str(e)
            # "already connected" means a previous attempt partially succeeded
            # Stop cleanly before retrying
            if "already connected" in err.lower():
                logger.warning("⚠️  Client already connected — stopping before retry...")
                try:
                    await app.stop()
                except Exception:
                    pass
                await asyncio.sleep(3)
            else:
                if attempt == max_retries:
                    logger.critical(f"❌ Failed after {max_retries} attempts: {e}")
                    sys.exit(1)
                wait = 15 * attempt
                logger.error(f"⚠️  Connection error: {e}. Retrying in {wait}s...")
                await asyncio.sleep(wait)

    # ── Bot connected ──────────────────────────────────────────
    me = await app.get_me()
    logger.info(f"🤖 Bot started as @{me.username} (ID: {me.id})")
    Config.BOT_USERNAME = me.username

    await idle()


# ══════════════════════════════════════════════════════════════
#  SHUTDOWN
# ══════════════════════════════════════════════════════════════

async def shutdown():
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
