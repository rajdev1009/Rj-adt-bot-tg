"""
╔══════════════════════════════════════════════════════════════╗
║                      UTILITY HELPERS                         ║
║   Shortener (Shortzy), animations, formatting,               ║
║   Token verification (one-time per file request)             ║
║   Credit: RAJ DEV @raj_dev_01                                ║
╚══════════════════════════════════════════════════════════════╝
"""

import asyncio
import time
import random
import string
import logging
from typing import Optional, Dict

from config import Config

logger = logging.getLogger("Utils")

_last_request: Dict[int, float] = {}

# Token Store: { user_id: { token: is_used } }
TOKENS: Dict[int, Dict[str, bool]] = {}


def check_spam(user_id: int, delay: int = 5) -> float:
    now  = time.time()
    last = _last_request.get(user_id, 0)
    remaining = delay - (now - last)
    if remaining > 0:
        return remaining
    _last_request[user_id] = now
    return 0


async def shorten_url(long_url: str) -> str:
    """Shortzy library se URL shorten karo. Config env vars use karta hai."""
    api_key = Config.SHORTLINK_API
    site    = Config.SHORTLINK_URL
    if not api_key:
        logger.warning("SHORTLINK_API not set — using direct URL.")
        return long_url
    try:
        from shortzy import Shortzy
        shortzy   = Shortzy(api_key=api_key, base_site=site)
        shortened = await shortzy.convert(long_url)
        if shortened and shortened != long_url:
            return shortened
        return long_url
    except Exception as e:
        logger.warning(f"Shortzy failed: {e}")
        return long_url


def generate_token(length: int = 7) -> str:
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


async def check_token(user_id: int, token: str) -> bool:
    if user_id in TOKENS:
        tkn_map = TOKENS[user_id]
        if token in tkn_map:
            return not tkn_map[token]
    return False


async def verify_user(user_id: int, token: str):
    if user_id in TOKENS and token in TOKENS[user_id]:
        TOKENS[user_id][token] = True


async def animate_start(message):
    frames = ["⚡", "💎", "🛡️", "💖"]
    sent = await message.reply("⚡")
    for frame in frames[1:]:
        await asyncio.sleep(0.5)
        await sent.edit_text(frame)
    return sent


async def animate_search(message):
    frames = [
        "🔍 **Searching...**\n▱▱▱▱▱▱▱▱▱▱ `0%`",
        "🔍 **Searching...**\n▰▰▱▱▱▱▱▱▱▱ `20%`",
        "🔍 **Searching...**\n▰▰▰▰▱▱▱▱▱▱ `40%`",
        "🔍 **Searching...**\n▰▰▰▰▰▰▱▱▱▱ `60%`",
        "🔍 **Searching...**\n▰▰▰▰▰▰▰▰▱▱ `80%`",
        "🔍 **Searching...**\n▰▰▰▰▰▰▰▰▰▰ `100%`",
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
    return {
        "video": "🎬", "audio": "🎵", "photo": "🖼️",
        "document": "📄", "animation": "🎞️",
        "voice": "🎤", "video_note": "📹",
    }.get(file_type, "📦")


def extract_file_info(message) -> Optional[Dict]:
    media_map = {
        "document":   ("document",   lambda m: (m.document.file_id,   m.document.file_name or "file",      m.document.file_size)),
        "video":      ("video",      lambda m: (m.video.file_id,      m.video.file_name or "video.mp4",    m.video.file_size)),
        "audio":      ("audio",      lambda m: (m.audio.file_id,      m.audio.file_name or "audio.mp3",    m.audio.file_size)),
        "photo":      ("photo",      lambda m: (m.photo.file_id,      "photo.jpg",                         m.photo.file_size or 0)),
        "animation":  ("animation",  lambda m: (m.animation.file_id,  "animation.gif",                     m.animation.file_size or 0)),
        "voice":      ("voice",      lambda m: (m.voice.file_id,      "voice.ogg",                         m.voice.file_size or 0)),
        "video_note": ("video_note", lambda m: (m.video_note.file_id, "videonote.mp4",                     m.video_note.file_size or 0)),
    }
    for attr, (ftype, extractor) in media_map.items():
        if getattr(message, attr, None):
            fid, fname, fsize = extractor(message)
            return {"file_id": fid, "file_name": fname, "file_size": fsize or 0, "file_type": ftype}
    return None


async def check_force_subscribe(client, user_id: int) -> bool:
    ch = Config.UPDATE_CHANNEL
    if not ch:
        return True
    try:
        member = await client.get_chat_member(ch, user_id)
        from pyrogram.enums import ChatMemberStatus
        return member.status not in (ChatMemberStatus.BANNED, ChatMemberStatus.LEFT)
    except Exception:
        return True
