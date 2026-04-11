"""
╔══════════════════════════════════════════════════════════════╗
║                    DECORATOR UTILITIES                       ║
║   admin_only, admin_callback, force_subscribe decorators     ║
║                                                              ║
║  SECURITY (§8):                                              ║
║  • admin_only / admin_callback both log the attempt and      ║
║    return immediately with no data leak.                     ║
║  • is_admin_filter is a reusable Pyrogram-level filter        ║
║    that can be composed directly into @Client.on_* calls     ║
║    for a zero-overhead first gate before any handler body    ║
║    is entered.                                               ║
╚══════════════════════════════════════════════════════════════╝
"""

import functools
import logging
from pyrogram import filters
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import UserNotParticipant, ChatAdminRequired
from config import Config
from database import DB

logger = logging.getLogger("Decorators")


# ── Reusable Pyrogram-level admin filter ──────────────────────
# Use this directly in @Client.on_message(...) / @Client.on_callback_query(...)
# so non-admin updates are dropped before any Python handler body runs.

def _admin_check(_, __, update) -> bool:
    user = getattr(update, "from_user", None)
    return bool(user and user.id in Config.ADMINS)

is_admin_filter = filters.create(_admin_check)


# ══════════════════════════════════════════════════════════════
#  DECORATOR: admin_only  (for Message handlers)
# ══════════════════════════════════════════════════════════════

def admin_only(func):
    """
    Defence-in-depth decorator for Message handlers.
    Should be paired with `is_admin_filter` at the Pyrogram level.
    Logs the unauthorised attempt and replies with a denial.
    """
    @functools.wraps(func)
    async def wrapper(client, message, *args, **kwargs):
        if message.from_user.id not in Config.ADMINS:
            logger.warning(
                "Unauthorised access attempt: user=%s tried %s",
                message.from_user.id,
                func.__name__,
            )
            await message.reply(
                "🚫 **Access Denied**\n\n"
                "This command is reserved for authorized admins only."
            )
            return
        return await func(client, message, *args, **kwargs)
    return wrapper


# ══════════════════════════════════════════════════════════════
#  DECORATOR: admin_callback  (for CallbackQuery handlers)
# ══════════════════════════════════════════════════════════════

def admin_callback(func):
    """
    Defence-in-depth decorator for CallbackQuery handlers.
    Should be paired with `is_admin_filter` at the Pyrogram level.
    Shows a dismissible alert — no data is returned.
    """
    @functools.wraps(func)
    async def wrapper(client, callback_query, *args, **kwargs):
        if callback_query.from_user.id not in Config.ADMINS:
            logger.warning(
                "Unauthorised callback attempt: user=%s data=%s",
                callback_query.from_user.id,
                callback_query.data,
            )
            await callback_query.answer(
                "🚫 Unauthorized — admins only.", show_alert=True
            )
            return
        return await func(client, callback_query, *args, **kwargs)
    return wrapper


# ══════════════════════════════════════════════════════════════
#  FORCE SUBSCRIBE CHECK
# ══════════════════════════════════════════════════════════════

async def check_force_subscribe(client, user_id: int) -> bool:
    """
    Returns True if the user is a member of UPDATE_CHANNEL.
    Admins always pass — they should never be blocked.
    """
    if not Config.UPDATE_CHANNEL:
        return True
    # Admins are always considered subscribed
    if user_id in Config.ADMINS:
        return True
    try:
        member = await client.get_chat_member(Config.UPDATE_CHANNEL, user_id)
        return member.status not in (
            ChatMemberStatus.BANNED,
            ChatMemberStatus.LEFT,
        )
    except UserNotParticipant:
        return False
    except ChatAdminRequired:
        logger.warning("Bot is not admin in UPDATE_CHANNEL — force-join check disabled.")
        return True
    except Exception as e:
        logger.error(f"Force subscribe check failed: {e}")
        return True


# ══════════════════════════════════════════════════════════════
#  DECORATOR: require_subscription  (for Message handlers)
# ══════════════════════════════════════════════════════════════

def require_subscription(func):
    """
    Blocks non-subscribed users from a handler.
    Premium users and admins bypass this automatically.
    """
    @functools.wraps(func)
    async def wrapper(client, message, *args, **kwargs):
        user_id = message.from_user.id
        # Admins and premium users always pass
        if user_id in Config.ADMINS:
            return await func(client, message, *args, **kwargs)
        subscribed = await check_force_subscribe(client, user_id)
        if not subscribed:
            channel = Config.UPDATE_CHANNEL
            from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            await message.reply(
                "⚠️ **Join Required!**\n\n"
                "You must join our channel to use this bot.\n\n"
                "👇 Click below, then tap **I Joined**.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{channel.lstrip('@')}")],
                    [InlineKeyboardButton("✅ I Joined",     callback_data="check_join")],
                ]),
            )
            return
        return await func(client, message, *args, **kwargs)
    return wrapper
