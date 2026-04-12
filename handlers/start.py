"""
╔══════════════════════════════════════════════════════════════╗
║                   /start COMMAND HANDLER                     ║
║   Handles both direct /start and ?start=file_id deep links   ║
╚══════════════════════════════════════════════════════════════╝
"""

import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
from config import Config
from database import DB
from utils import (
    animate_start,
    animate_search,
    animate_found,
    humanize_size,
    get_file_emoji,
    check_spam,
    check_force_subscribe,
)

logger = logging.getLogger("StartHandler")


# ══════════════════════════════════════════════════════════════
#  /start  ─── with or without deep-link payload
# ══════════════════════════════════════════════════════════════

@Client.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    user = message.from_user
    args = message.command[1:]  # deep-link payload, if any

    # ── Register user ──────────────────────────────────────────
    await DB.add_user(
        user_id=user.id,
        full_name=user.first_name + (f" {user.last_name}" if user.last_name else ""),
        username=user.username,
    )
    await DB.update_last_active(user.id)

    # ── Deep link: /start file_<encoded_id> ───────────────────
    if args:
        payload = args[0]
        if payload.startswith("file_"):
            await handle_file_request(client, message, payload[5:])
            return

    # ── Regular /start: play animation then show welcome ───────
    anim_msg = await animate_start(message)
    await asyncio.sleep(0.3)

    # Check premium status for personalised greeting
    is_premium = await DB.is_premium(user.id)
    crown = "👑 " if is_premium else ""

    welcome_text = (
        f"✨ **Welcome, {crown}{user.first_name}!**\n\n"
        "🤖 I am a **Premium File Store Bot**.\n"
        "📦 I securely store and deliver files on demand.\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🔗 Send me a file link to download\n"
        "💎 Upgrade to **Premium** for extra perks\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{'👑 You have **Premium** access!\n' if is_premium else ''}"
        "👇 Choose an option below:"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👑 Premium Plans", callback_data="premium_plans"),
            InlineKeyboardButton("ℹ️ About & Tutorial", callback_data="about"),
        ],
        [
            InlineKeyboardButton("📢 Update Channel", url=f"https://t.me/{Config.UPDATE_CHANNEL.lstrip('@')}"),
        ],
        [
            InlineKeyboardButton("🆘 Help", callback_data="help"),
        ],
    ])

    await anim_msg.edit_text(welcome_text, reply_markup=keyboard)


# ══════════════════════════════════════════════════════════════
#  FILE REQUEST LOGIC
# ══════════════════════════════════════════════════════════════

async def handle_file_request(client: Client, message: Message, file_id: str):
    """
    Core file delivery logic.

    Link selection rules (§8 — Dynamic Shortener Bypass):
      ┌─────────────────────┬──────────────────────────────┐
      │ User type           │ Link shown in confirmation   │
      ├─────────────────────┼──────────────────────────────┤
      │ Premium             │ Always direct_link           │
      │ Admin               │ Always direct_link           │
      │ Regular, short ON   │ short_url (if available)     │
      │ Regular, short OFF  │ direct_link                  │
      └─────────────────────┴──────────────────────────────┘

    Note: the actual file is always forwarded via copy_message regardless
    of which link is shown — the link is only for the user's own sharing.
    """
    user = message.from_user

    # ── Anti-spam check ────────────────────────────────────────
    cooldown = check_spam(user.id, Config.REQUEST_DELAY)
    if cooldown > 0:
        await message.reply(
            f"⏳ **Slow down!**\n\nPlease wait **{cooldown:.1f}s** before your next request."
        )
        return

    # ── Resolve user tier ──────────────────────────────────────
    is_admin   = user.id in Config.ADMINS
    is_premium = await DB.is_premium(user.id)

    # ── Premium mode gate (skip for admins and premium users) ─
    premium_mode = await DB.is_premium_mode()
    if premium_mode and not is_premium and not is_admin:
        await message.reply(
            "🔒 **Premium Mode Active**\n\n"
            "This bot is currently in **Premium-only** mode.\n"
            "Upgrade to access all files!\n\n"
            "👇 Tap below to see plans:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👑 View Plans", callback_data="premium_plans")]
            ]),
        )
        return

    # ── Force subscribe (skipped for premium users and admins) ─
    if not is_premium and not is_admin:
        subscribed = await check_force_subscribe(client, user.id)
        if not subscribed:
            channel = Config.UPDATE_CHANNEL
            await message.reply(
                "⚠️ **Join Required!**\n\n"
                "You must join our channel to download files.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{channel.lstrip('@')}")],
                    [InlineKeyboardButton("✅ I've Joined", callback_data=f"verify_join_{file_id}")],
                ]),
            )
            return

    # ── Search animation ───────────────────────────────────────
    search_msg = await animate_search(message)

    # ── Fetch metadata from DB ─────────────────────────────────
    file_doc = await DB.get_file(file_id)
    if not file_doc:
        await search_msg.edit_text(
            "❌ **File Not Found**\n\n"
            "This file may have been deleted or the link is invalid."
        )
        return

    # ── File found animation ───────────────────────────────────
    await animate_found(search_msg)
    await asyncio.sleep(0.5)

    # ── Forward file from DB channel ───────────────────────────
    try:
        await client.copy_message(
            chat_id      = user.id,
            from_chat_id = Config.DB_CHANNEL,
            message_id   = file_doc["message_id"],
        )
        await DB.increment_download(file_id)

        # ── Resolve which link to show the user (§8 logic) ────
        #
        # Priority order:
        #   1. Admin or Premium  → always direct_url
        #   2. Regular + shortener ON + short_url exists → short_url
        #   3. Everything else   → direct_url
        #
        direct_url    = file_doc.get("direct_url") or ""
        short_url_db  = file_doc.get("short_url")        # None if never shortened
        shortener_on  = await DB.is_shortener_on()

        if is_admin or is_premium:
            user_link   = direct_url
            link_label  = "🔗 Your Direct Link" + (" 👑" if is_premium else " 🔧")
            bypass_note = (
                "_(Premium bypass — shortener skipped for you)_"
                if is_premium and shortener_on and short_url_db
                else ""
            )
        elif shortener_on and short_url_db:
            user_link   = short_url_db
            link_label  = "✂️ Your Download Link"
            bypass_note = ""
        else:
            user_link   = direct_url
            link_label  = "🔗 Your Download Link"
            bypass_note = ""

        file_emoji = get_file_emoji(file_doc.get("file_type", "document"))
        size_str   = humanize_size(file_doc.get("file_size", 0))

        confirmation = (
            f"✅ **File Delivered!**\n\n"
            f"{file_emoji} `{file_doc.get('file_name', 'Unknown')}`\n"
            f"📦 Size: **{size_str}**\n\n"
            f"{link_label}:\n`{user_link}`\n\n"
            + (f"{bypass_note}\n\n" if bypass_note else "")
            + "_Enjoy your file! Share the bot with friends._ 😊"
        )

        buttons = []
        if user_link:
            buttons.append([InlineKeyboardButton("🔗 Share Link", url=user_link)])

        await search_msg.edit_text(
            confirmation,
            reply_markup=InlineKeyboardMarkup(buttons) if buttons else None,
        )

    except Exception as e:
        logger.error(f"Error forwarding file {file_id}: {e}")
        await search_msg.edit_text(
            "⚠️ **Delivery Failed**\n\n"
            "Something went wrong. Please try again later."
        )


# ══════════════════════════════════════════════════════════════
#  CALLBACK QUERY HANDLERS  (for start menu buttons)
# ══════════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex("^premium_plans$"))
async def cb_premium_plans(client: Client, cq: CallbackQuery):
    text = await DB.get_premium_text()
    await cq.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="back_start")]
        ]),
    )
    await cq.answer()


@Client.on_callback_query(filters.regex("^about$"))
async def cb_about(client: Client, cq: CallbackQuery):
    text = await DB.get_about_text()
    await cq.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🆘 Help / Tutorial", callback_data="help")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_start")],
        ]),
    )
    await cq.answer()


@Client.on_callback_query(filters.regex("^help$"))
async def cb_help(client: Client, cq: CallbackQuery):
    tutorial_id = await DB.get_tutorial_file_id()
    if tutorial_id:
        await cq.message.reply_video(
            video=tutorial_id,
            caption=(
                "🎬 **Tutorial Video**\n\n"
                "Watch this short video to learn how to use the bot.\n\n"
                "🔗 Share links with your friends!"
            ),
        )
        await cq.answer()
    else:
        await cq.answer("ℹ️ No tutorial set yet. Ask admin to add one.", show_alert=True)


@Client.on_callback_query(filters.regex("^back_start$"))
async def cb_back_start(client: Client, cq: CallbackQuery):
    user = cq.from_user
    is_premium = await DB.is_premium(user.id)
    crown = "👑 " if is_premium else ""

    welcome_text = (
        f"✨ **Welcome back, {crown}{user.first_name}!**\n\n"
        "🤖 I am a **Premium File Store Bot**.\n\n"
        "👇 Choose an option below:"
    )
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👑 Premium Plans", callback_data="premium_plans"),
            InlineKeyboardButton("ℹ️ About & Tutorial", callback_data="about"),
        ],
        [
            InlineKeyboardButton("📢 Update Channel", url=f"https://t.me/{Config.UPDATE_CHANNEL.lstrip('@')}"),
        ],
        [
            InlineKeyboardButton("🆘 Help", callback_data="help"),
        ],
    ])
    await cq.message.edit_text(welcome_text, reply_markup=keyboard)
    await cq.answer()


@Client.on_callback_query(filters.regex("^check_join$"))
async def cb_check_join(client: Client, cq: CallbackQuery):
    subscribed = await check_force_subscribe(client, cq.from_user.id)
    if subscribed:
        await cq.answer("✅ Verified! You can now use the bot.", show_alert=True)
        await cq.message.delete()
    else:
        await cq.answer("❌ You haven't joined yet!", show_alert=True)


@Client.on_callback_query(filters.regex(r"^verify_join_(.+)$"))
async def cb_verify_join(client: Client, cq: CallbackQuery):
    file_id = cq.data.split("_", 2)[2]
    subscribed = await check_force_subscribe(client, cq.from_user.id)
    if subscribed:
        await cq.answer("✅ Verified! Fetching your file now...", show_alert=True)
        await cq.message.delete()
        await handle_file_request(client, cq.message, file_id)
    else:
        await cq.answer("❌ You haven't joined yet!", show_alert=True)
