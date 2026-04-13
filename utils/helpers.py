"""
╔══════════════════════════════════════════════════════════════╗
║                      UTILITY HELPERS                         ║
║   Shortener, animations, formatting, anti-spam tracker       ║
║   Credit: RAJ DEV                                            ║
╚══════════════════════════════════════════════════════════════╝
"""

import asyncio
import time
import logging
from typing import Optional, Dict
import aiohttp

logger = logging.getLogger("Utils")

_last_request: Dict[int, float] = {}


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
#  shrinkme.io + generic API support
# ══════════════════════════════════════════════════════════════

async def shorten_url(long_url: str, api_key: str, site: str = "shrinkme.io") -> str:
    """
    URL shorten karo.

    shrinkme.io response format:
      {"status": 1, "shortenedUrl": "https://shrinkme.io/xxxxx"}

    Fallback: original URL return karo agar koi bhi error ho.
    """
    if not api_key:
        logger.warning("Shortener API key not set — using direct URL.")
        return long_url

    # shrinkme.io ka sahi endpoint
    endpoint = f"https://{site}/api?api={api_key}&url={long_url}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                endpoint,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:

                # Response text pehle lo — JSON parse error avoid karo
                text = await resp.text()
                logger.debug(f"Shortener raw response: {text[:200]}")

                try:
                    data = await resp.json(content_type=None)
                except Exception:
                    import json
                    try:
                        data = json.loads(text)
                    except Exception:
                        logger.warning(f"Shortener non-JSON response: {text[:100]}")
                        return long_url

                # shrinkme.io format: {"status":1, "shortenedUrl":"..."}
                if data.get("status") == 1 and data.get("shortenedUrl"):
                    short = data["shortenedUrl"]
                    logger.info(f"Shortened: {long_url[:50]} → {short}")
                    return short

                # Generic formats
                if data.get("shortenedUrl"):
                    return data["shortenedUrl"]
                if data.get("short_url"):
                    return data["short_url"]
                if data.get("result", {}).get("full_short_link"):
                    return data["result"]["full_short_link"]

                # Error message log karo
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
#  ANIMATION HELPERS
# ══════════════════════════════════════════════════════════════

async def animate_start(message):
    """⚡ → 💎 → 🛡️ → 💖"""
    frames = ["⚡", "💎", "🛡️", "💖"]
    sent = await message.reply("⚡")
    for frame in frames[1:]:
        await asyncio.sleep(0.5)
        await sent.edit_text(frame)
    return sent


async def animate_search(message):
    """Loading bar animation."""
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
    """File found animation."""
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
