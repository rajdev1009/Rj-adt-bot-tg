"""
╔══════════════════════════════════════════════════════════════╗
║           TELEGRAM FILE STORE BOT - MAIN ENTRY              ║
║           Built with Pyrogram + MongoDB/NeonDB               ║
║                                                              ║
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
    PeerIdInvalid, ChannelInvalid, ChannelPrivate,
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


# ══════════════════════════════════════════════════════════════
#  HEALTH CHECK SERVER
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
#  CHANNEL RESOLVER
#  Pyrogram sirf un channels ko message bhej sakta hai jinhein
#  usne pehle resolve kiya ho (get_chat call).
#  Bot start hote hi dono channels resolve kar lo.
# ══════════════════════════════════════════════════════════════

async def resolve_channels():
    """
    DB_CHANNEL aur UPDATE_CHANNEL dono ko startup pe resolve karo.

    Telegram Peer ID kaise kaam karta hai:
      • Bot kisi channel mein message tab bhej sakta hai jab
        Pyrogram ke internal cache mein us channel ka 'access_hash'
        stored ho.
      • get_chat() call karne se yeh hash cache mein aa jaata hai.
      • Iske baad send_message(chat_id=numeric_id) kaam karta hai.
    """
    errors = []

    # DB Channel resolve
    try:
        chat = await app.get_chat(Config.DB_CHANNEL)
        logger.info(f"✅ DB Channel resolved: {chat.title} (ID: {chat.id})")
        # Runtime mein actual int ID store karo (cache key match ke liye)
        Config.DB_CHANNEL = chat.id
    except (PeerIdInvalid, ChannelInvalid, ChannelPrivate) as e:
        errors.append(
            f"❌ DB_CHANNEL '{Config.DB_CHANNEL}' resolve nahi hua: {e}\n"
            f"   → Bot ko us channel ka Admin banao, phir restart karo."
        )
    except Exception as e:
        errors.append(f"⚠️  DB_CHANNEL resolve warning: {e}")

    # Update Channel resolve (optional — sirf agar set hai)
    if Config.UPDATE_CHANNEL:
        try:
            chat = await app.get_chat(Config.UPDATE_CHANNEL)
            logger.info(f"✅ Update Channel resolved: {chat.title} (ID: {chat.id})")
            # IMPORTANT: int ID store karo — Pyrogram send_message mein kaam karta hai
            Config.UPDATE_CHANNEL = chat.id
            # Username alag store karo buttons ke liye
            if chat.username:
                Config.UPDATE_CHANNEL_USERNAME = chat.username
                logger.info(f"   Username: @{chat.username}")
            else:
                logger.info("   No public username (private channel)")
        except (PeerIdInvalid, ChannelInvalid, ChannelPrivate) as e:
            errors.append(
                f"❌ UPDATE_CHANNEL resolve fail: {e}\n"
                f"   Fix: Bot ko channel ka Admin banao → restart karo"
            )
        except Exception as e:
            errors.append(f"⚠️  UPDATE_CHANNEL warning: {e}")

    # Errors print karo (crash mat karo — bot chal sakta hai bina update channel ke)
    for err in errors:
        logger.warning(err)

    if errors:
        logger.warning(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Channel resolve errors hue hain.\n"
            "Files upload hoti rahegi lekin channel post fail hoga\n"
            "jab tak bot ko channel ka admin nahi banate.\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )


# ══════════════════════════════════════════════════════════════
#  STARTUP
# ══════════════════════════════════════════════════════════════

async def startup():
    logger.info("🚀 Starting File Store Bot...")
    logger.info("   Credit: RAJ DEV")

    await MongoDB.connect()
    logger.info("✅ MongoDB connected.")

    if Config.NEON_URL:
        await NeonDB.connect()
        logger.info("✅ NeonDB connected.")
    else:
        logger.info("ℹ️  NeonDB skipped (NEON_URL not set).")

    await start_health_server()

    # Telegram connect with FloodWait retry
    max_retries = 5
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"🔌 Connecting to Telegram... (attempt {attempt}/{max_retries})")
            await app.start()
            break

        except FloodWait as e:
            wait = e.value + 10
            logger.warning(
                f"⏳ Telegram FloodWait: {e.value}s required. Sleeping {wait}s..."
            )
            await asyncio.sleep(wait)

        except (AccessTokenInvalid, AccessTokenExpired) as e:
            logger.critical(f"❌ Invalid/expired BOT_TOKEN: {e}")
            sys.exit(1)

        except ApiIdInvalid:
            logger.critical("❌ Invalid API_ID/API_HASH.")
            sys.exit(1)

        except Exception as e:
            err = str(e).lower()
            if "already connected" in err:
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

    # Bot connected — ab channels resolve karo
    me = await app.get_me()
    logger.info(f"🤖 Bot started as @{me.username} (ID: {me.id})")
    Config.BOT_USERNAME = me.username

    # ⬇️  CRITICAL: channels resolve karo taaki send_message kaam kare
    await resolve_channels()

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
