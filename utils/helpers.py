"""
╔══════════════════════════════════════════════════════════════╗
║                      UTILITY HELPERS                         ║
║   Shortener, animations, formatting, anti-spam,              ║
║   Token verification (one-time per file request)             ║
║   Credit: RAJ DEV                                            ║
╚══════════════════════════════════════════════════════════════╝
"""

import asyncio
import time
import random
import string
import logging
from typing import Optional, Dict
import aiohttp

from config import Config

logger = logging.getLogger("Utils")

_last_request: Dict[int, float] = {}

# ══════════════════════════════════════════════════════════════
#  TOKEN STORE — in-memory
#  TOKENS = { user_id: { token: is_used (bool) } }
#  NOTE: VERIFIED dictionary NAHI hai — har file ke liye
#        har baar shortlink visit karna hoga
# ══════════════════════════════════════════════════════════════

TOKENS: Dict[int, Dict[str, bool]] = {}


# ══════════════════════════════════════════════════════════════
#  ANTI-SPAM
# ══════════════════════════════════════════════════════════════

def check_spam(user_id: int, delay: int = 5) -> float:
    now = time.time()
    last = _last_request.get(user_id, 0)
    remaining = delay - (now - last)
    if remaining > 0:
        return remaining
    _last_request[user_id] = now
    return 0


# ══════════════════════════════════════════════════════════════
#  LINK SHORTENER
# ══════════════════════════════════════════════════════════════

async def shorten_url(long_url: str, api_key: str, site: str = "shrinkme.io") -> str:
    """
    URL shorten karo via shrinkme.io / compatible API.
    Fallback: original URL return karo on any error.
    """
    if not api_key:
        logger.warning("Shortener API key not set — using direct URL.")
        return long_url

    endpoint = f"https://{site}/api?api={api_key}&url={long_url}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                endpoint,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                text = await resp.text()
                logger.debug(f"Shortener raw response: {text[:200]}")

                try:
                    data = await resp.json(content_type=None)
                except Exception:
                    import json as _json
                    try:
                        data = _json.loads(text)
                    except Exception:
                        logger.warning(f"Shortener non-JSON response: {text[:100]}")
                        return long_url

                if data.get("status") == 1 and data.get("shortenedUrl"):
                    short = data["shortenedUrl"]
                    logger.info(f"Shortened: {long_url[:50]} → {short}")
                    return short
                if data.get("shortenedUrl"):
                    return data["shortenedUrl"]
                if data.get("short_url"):
                    return data["short_url"]
                if data.get("result", {}).get("full_short_link"):
                    return data["result"]["full_short_link"]

                err = data.get("message") or data.get("error") or str(data)
                logger.warning(f"Shortener error response: {err}")
                return long_url

    except aiohttp.ClientError as e:
        logger.warning(f"Shortener network error: {e}")
        return long_url
    except Exception as e:
        logger.warning(f"Shortener failed: {e}")
        return long_url


# ══════════════════════════════════════════════════════════════
#  TOKEN SYSTEM — ONE TIME PER FILE REQUEST
#  Har file request pe naya token banega
#  Token ek baar use hone ke baad expire ho jaega
#  Koi daily verification nahi — har baar shortlink visit karna hoga
# ══════════════════════════════════════════════════════════════

def generate_token(length: int = 7) -> str:
    """Random alphanumeric token generate karo."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


async def check_token(user_id: int, token: str) -> bool:
    """
    Token valid hai aur abhi tak use nahi hua — True return karo.
    """
    if user_id in TOKENS:
        tkn_map = TOKENS[user_id]
        if token in tkn_map:
            is_used = tkn_map[token]
            return not is_used  # False = not used yet = valid
    return False


async def verify_user(user_id: int, token: str):
    """
    Token ko used mark karo — ek baar use hone ke baad expire.
    """
    if user_id in TOKENS and token in TOKENS[user_id]:
        TOKENS[user_id][token] = True
        logger.info(f"Token verified and consumed for user {user_id}")


# ══════════════════════════════════════════════════════════════
#  ANIMATION HELPERS
# ══════════════════════════════════════════════════════════════

async def animate_start(message):
    frames = ["⚡", "💎", "🛡️", "💖"]
    sent = await message.reply("⚡")
    for frame in frames[1:]:
        await asyncio.sleep(0.5)
        await sent.edit_text(frame)
    return sent


async def animate_search(message):
    frames = [
        "🔍 **Searching in Database...**\n▱▱▱▱▱▱▱▱▱▱ `0%`",
        "🔍 **Searching in Database...**\n▰▰▱▱▱▱▱▱▱▱ `20%`",
        "🔍 **Searching in Database...**\n▰▰▰▰▱▱▱▱▱▱ `40%`",
        "🔍 **Searching in Database...**\n▰▰▰▰▰▰▱▱▱▱ `60%`",
        "🔍 **Searching in Database...**\n▰▰▰▰▰▰▰▰▱▱ `80%`",
        "🔍 **Searching in Database...**\n▰▰▰▰▰▰▰▰▰▰ `100%`",
    ]
    sent = await message.reply(frames[0])
    for frame in frames[1:]:
        await asyncio.sleep(0.4)
        try:
            await sent.edit_text(frame)
        except Exception:
            pass
    return sent


async def animate_found(msg):
    frames = [
        "✅ **File Found!**",
        "✅ **File Found!** 📂",
        "✅ **File Found!** 📂✨",
        "✅ **File Found!** 📂✨\n⚡ **Sending now...**",
    ]
    for frame in frames:
        await asyncio.sleep(0.3)
        try:
            await msg.edit_text(frame)
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════
#  FORMATTING HELPERS
# ══════════════════════════════════════════════════════════════

def humanize_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / (1024**2):.1f} MB"
    else:
        return f"{size_bytes / (1024**3):.2f} GB"


def get_file_emoji(file_type: str) -> str:
    mapping = {
        "video":      "🎬",
        "audio":      "🎵",
        "photo":      "🖼️",
        "document":   "📄",
        "animation":  "🎞️",
        "voice":      "🎤",
        "video_note": "📹",
        "sticker":    "🎭",
    }
    return mapping.get(file_type, "📦")


def extract_file_info(message) -> Optional[Dict]:
    """Extract file metadata from a Pyrogram message."""
    media_map = {
        "document":   ("document",   lambda m: (m.document.file_id,   m.document.file_name or "file",   m.document.file_size)),
        "video":      ("video",      lambda m: (m.video.file_id,      m.video.file_name or "video.mp4", m.video.file_size)),
        "audio":      ("audio",      lambda m: (m.audio.file_id,      m.audio.file_name or "audio.mp3", m.audio.file_size)),
        "photo":      ("photo",      lambda m: (m.photo.file_id,      "photo.jpg",                      m.photo.file_size or 0)),
        "animation":  ("animation",  lambda m: (m.animation.file_id,  "animation.gif",                  m.animation.file_size or 0)),
        "voice":      ("voice",      lambda m: (m.voice.file_id,      "voice.ogg",                      m.voice.file_size or 0)),
        "video_note": ("video_note", lambda m: (m.video_note.file_id, "videonote.mp4",                  m.video_note.file_size or 0)),
    }
    for attr, (ftype, extractor) in media_map.items():
        if getattr(message, attr, None):
            file_id, file_name, file_size = extractor(message)
            return {
                "file_id":   file_id,
                "file_name": file_name,
                "file_size": file_size or 0,
                "file_type": ftype,
            }
    return None


# ══════════════════════════════════════════════════════════════
#  FORCE SUBSCRIBE CHECK
# ══════════════════════════════════════════════════════════════

async def check_force_subscribe(client, user_id: int) -> bool:
    ch = Config.UPDATE_CHANNEL
    if not ch:
        return True
    try:
        member = await client.get_chat_member(ch, user_id)
        from pyrogram.enums import ChatMemberStatus
        return member.status not in (
            ChatMemberStatus.BANNED,
            ChatMemberStatus.LEFT,
        )
    except Exception:
        return True
