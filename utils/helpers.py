"""
╔══════════════════════════════════════════════════════════════╗
║                      UTILITY HELPERS                         ║
║   Shortener, animations, formatting, anti-spam tracker       ║
╚══════════════════════════════════════════════════════════════╝
"""

import asyncio
import time
import logging
from typing import Optional, Dict
import aiohttp

logger = logging.getLogger("Utils")

# ── Anti-spam: track last request timestamp per user ──────────
_last_request: Dict[int, float] = {}

# ══════════════════════════════════════════════════════════════
#  ANTI-SPAM
# ══════════════════════════════════════════════════════════════

def check_spam(user_id: int, delay: int = 5) -> float:
    """
    Returns 0 if request is allowed, else returns remaining cooldown in seconds.
    """
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

async def shorten_url(long_url: str, api_key: str, site: str = "api.shrtco.de") -> str:
    """
    Shorten a URL using the configured shortener API.
    Falls back to the original URL on any error.

    Supports shrtco.de (no key needed) and generic ?api=KEY&url=URL sites.
    """
    if not api_key and site == "api.shrtco.de":
        # shrtco.de is free and keyless
        endpoint = f"https://api.shrtco.de/v2/shorten?url={long_url}"
    else:
        endpoint = f"https://{site}/api?api={api_key}&url={long_url}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(endpoint, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                data = await resp.json()
                # shrtco.de response format
                if "result" in data:
                    return data["result"].get("full_short_link", long_url)
                # Generic response format
                if "shortenedUrl" in data:
                    return data["shortenedUrl"]
                if "short_url" in data:
                    return data["short_url"]
                return long_url
    except Exception as e:
        logger.warning(f"Shortener failed: {e} — using original URL.")
        return long_url


# ══════════════════════════════════════════════════════════════
#  ANIMATION HELPERS
# ══════════════════════════════════════════════════════════════

async def animate_start(message):
    """
    Play the startup animation sequence:
    ⚡ → 💎 → 🛡️ → 💖  (0.5s each)
    Returns the final animated message object.
    """
    frames = ["⚡", "💎", "🛡️", "💖"]
    sent = await message.reply("⚡")
    for frame in frames[1:]:
        await asyncio.sleep(0.5)
        await sent.edit_text(frame)
    return sent


async def animate_search(message):
    """
    Show a file-search animation with a loading bar.
    Returns the message to be reused.
    """
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
    """Edit a message through 'File Found!' animation frames."""
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
    """Convert bytes to human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / (1024**2):.1f} MB"
    else:
        return f"{size_bytes / (1024**3):.2f} GB"


def get_file_emoji(file_type: str) -> str:
    """Return an emoji based on file type."""
    mapping = {
        "video":    "🎬",
        "audio":    "🎵",
        "photo":    "🖼️",
        "document": "📄",
        "animation":"🎞️",
        "voice":    "🎤",
        "video_note":"📹",
        "sticker":  "🎭",
    }
    return mapping.get(file_type, "📦")


def extract_file_info(message) -> Optional[Dict]:
    """
    Extract (file_id, file_name, file_size, file_type) from a Pyrogram message.
    Returns None if no media found.
    """
    media_map = {
        "document":   ("document",   lambda m: (m.document.file_id,   m.document.file_name or "file",  m.document.file_size)),
        "video":      ("video",      lambda m: (m.video.file_id,      m.video.file_name or "video.mp4",m.video.file_size)),
        "audio":      ("audio",      lambda m: (m.audio.file_id,      m.audio.file_name or "audio.mp3",m.audio.file_size)),
        "photo":      ("photo",      lambda m: (m.photo.file_id,      "photo.jpg",                     m.photo.file_size or 0)),
        "animation":  ("animation",  lambda m: (m.animation.file_id,  "animation.gif",                 m.animation.file_size or 0)),
        "voice":      ("voice",      lambda m: (m.voice.file_id,      "voice.ogg",                     m.voice.file_size or 0)),
        "video_note": ("video_note", lambda m: (m.video_note.file_id, "videonote.mp4",                 m.video_note.file_size or 0)),
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
