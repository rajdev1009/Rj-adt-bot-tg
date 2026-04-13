"""
╔══════════════════════════════════════════════════════════════╗
║                   /start COMMAND HANDLER                     ║
║   Handles both direct /start and ?start=file_id deep links   ║
║                                                              ║
║   Credit: RAJ DEV                                            ║
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
#  PROMO ANIMATION — Admin ka naam ek baar flash hokar gayab
# ══════════════════════════════════════════════════════════════

async def show_promo_flash(message: Message):
    """
    Admin ka naam ek baar flash hoga aur phir gayab ho jaega.
    Emojis ki tarah ek baar dikhega aur delete ho jaega.
    """
    try:
        promo = await message.reply(
            "✨ **RAJ DEV** ✨"
        )
        await asyncio.sleep(1.5)
        await promo.delete()
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════
#  /start
# ══════════════════════════════════════════════════════════════

@Client.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    user = message.from_user
    args = message.command[1:]

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
            # Promo flash pehle dikhao, phir file do
            await show_promo_flash(message)
            await handle_file_request(client, message, payload[5:])
            return

    # ── Regular /start: animation → welcome ───────────────────
    anim_msg = await animate_start(message)
    await asyncio.sleep(0.3)

    is_premium = await DB.is_premium(user.id)
    crown = "👑 " if is_premium else ""
    premium_line = "👑 You have **Premium** access!\n\n" if is_premium else ""

    welcome_text = (
        f"✨ **Welcome, {crown}{user.first_name}!**\n\n"
        "🤖 I am a **Premium File Store Bot**.\n"
        "📦 I securely store and deliver files on demand.\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🔗 Send me a file link to download\n"
        "💎 Upgrade to **Premium** for extra perks\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        + premium_line
        + "👇 Choose an option below:"
    )

    _ch_url = Config.get_channel_url()
    _kb_rows = [
        [
            InlineKeyboardButton("👑 Premium Plans", callback_data="premium_plans"),
            InlineKeyboardButton("ℹ️ About", callback_data="about"),
        ],
    ]
    if _ch_url:
        _kb_rows.append([InlineKeyboardButton("📢 Update Channel", url=_ch_url)])
    _kb_rows.append([InlineKeyboardButton("🆘 Help & Tutorial", callback_data="help_menu")])
    keyboard = InlineKeyboardMarkup(_kb_rows)

    await anim_msg.edit_text(welcome_text, reply_markup=keyboard)


# ══════════════════════════════════════════════════════════════
#  AUTO DELETE HELPER
# ══════════════════════════════════════════════════════════════

async def _auto_delete(file_msg, notice_msg, delay: int):
    """
    delay seconds baad file aur notice message dono delete karo.
    Countdown warning 1 minute pehle dikhao.
    """
    try:
        # 1 minute pehle warning (sirf agar delay > 60s hai)
        if delay > 60:
            await asyncio.sleep(delay - 60)
            try:
                await notice_msg.edit_text(
                    "⏳ **1 minute mein file delete ho jaegi!**\n\n"
                    "Abhi save kar lo! 💾\n\n"
                    "🔖 _Powered by **RAJ DEV**_"
                )
            except Exception:
                pass
            await asyncio.sleep(60)
        else:
            await asyncio.sleep(delay)

        # File delete karo
        try:
            await file_msg.delete()
        except Exception:
            pass

        # Notice message bhi delete karo
        try:
            await notice_msg.delete()
        except Exception:
            pass

    except Exception as e:
        logger.warning(f"Auto-delete failed: {e}")


# ══════════════════════════════════════════════════════════════
#  FILE REQUEST LOGIC
# ══════════════════════════════════════════════════════════════

async def handle_file_request(client: Client, message: Message, file_id: str):
    """
    Core file delivery.
    Premium/Admin → always direct_url
    Regular + shortener ON → short_url
    Regular + shortener OFF → direct_url
    """
    user = message.from_user

    # Anti-spam
    cooldown = check_spam(user.id, Config.REQUEST_DELAY)
    if cooldown > 0:
        await message.reply(
            f"⏳ **Slow down!**\n\nPlease wait **{cooldown:.1f}s** before your next request."
        )
        return

    is_admin   = user.id in Config.ADMINS
    is_premium = await DB.is_premium(user.id)

    # Premium mode gate
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

    # Force subscribe check
    if not is_premium and not is_admin:
        subscribed = await check_force_subscribe(client, user.id)
        if not subscribed:
            channel = Config.UPDATE_CHANNEL
            await message.reply(
                "⚠️ **Join Required!**\n\n"
                "You must join our channel to download files.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(
                        "📢 Join Channel",
                        url=f"https://t.me/{channel.lstrip('@')}"
                    )],
                    [InlineKeyboardButton(
                        "✅ I've Joined",
                        callback_data=f"verify_join_{file_id}"
                    )],
                ]),
            )
            return

    # Search animation
    search_msg = await animate_search(message)

    # DB se file fetch
    file_doc = await DB.get_file(file_id)
    if not file_doc:
        await search_msg.edit_text(
            "❌ **File Not Found**\n\n"
            "This file may have been deleted or the link is invalid."
        )
        return

    # Found animation
    await animate_found(search_msg)
    await asyncio.sleep(0.5)

    # Auto-delete delay — ENV se configure karo (default 5 min)
    import os as _os
    AUTO_DELETE_SECONDS = int(_os.environ.get("AUTO_DELETE_TIME", 300))  # 300s = 5 min

    try:
        sent_file = await client.copy_message(
            chat_id      = user.id,
            from_chat_id = Config.DB_CHANNEL,
            message_id   = file_doc["message_id"],
        )
        await DB.increment_download(file_id)

        direct_url   = file_doc.get("direct_url") or ""
        short_url_db = file_doc.get("short_url")
        shortener_on = await DB.is_shortener_on()

        if is_admin or is_premium:
            user_link  = direct_url
            link_label = "🔗 Your Direct Link" + (" 👑" if is_premium else " 🔧")
            bypass_note = (
                "_(Premium bypass — shortener skipped for you)_"
                if is_premium and shortener_on and short_url_db
                else ""
            )
        elif shortener_on and short_url_db:
            user_link  = short_url_db
            link_label = "✂️ Your Download Link"
            bypass_note = ""
        else:
            user_link  = direct_url
            link_label = "🔗 Your Download Link"
            bypass_note = ""

        file_emoji = get_file_emoji(file_doc.get("file_type", "document"))
        size_str   = humanize_size(file_doc.get("file_size", 0))

        # Minutes display ke liye
        minutes = AUTO_DELETE_SECONDS // 60

        confirmation = (
            f"✅ **File Delivered!**\n\n"
            f"{file_emoji} `{file_doc.get('file_name', 'Unknown')}`\n"
            f"📦 Size: **{size_str}**\n\n"
            f"{link_label}:\n`{user_link}`\n\n"
            + (f"{bypass_note}\n\n" if bypass_note else "")
            + f"⚠️ _Yeh file **{minutes} minute** mein auto-delete ho jaegi!_\n"
            + "_Save kar lo abhi._ 💾\n\n"
            + "🔖 _Powered by **RAJ DEV**_"
        )

        buttons = []
        if user_link:
            buttons.append([InlineKeyboardButton("🔗 Share Link", url=user_link)])

        notice_msg = await search_msg.edit_text(
            confirmation,
            reply_markup=InlineKeyboardMarkup(buttons) if buttons else None,
        )

        # Background mein auto-delete schedule karo
        asyncio.create_task(
            _auto_delete(sent_file, notice_msg, AUTO_DELETE_SECONDS)
        )

    except Exception as e:
        logger.error(f"Error forwarding file {file_id}: {e}")
        await search_msg.edit_text(
            "⚠️ **Delivery Failed**\n\n"
            "Something went wrong. Please try again later."
        )


# ══════════════════════════════════════════════════════════════
#  CALLBACK HANDLERS
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
            [InlineKeyboardButton("🆘 Help & Tutorial", callback_data="help_menu")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_start")],
        ]),
    )
    await cq.answer()


@Client.on_callback_query(filters.regex("^help_menu$"))
async def cb_help_menu(client: Client, cq: CallbackQuery):
    """
    Sab users ke liye help menu.
    Tutorial video agar set hai to dikhao.
    """
    tutorial_id = await DB.get_tutorial_file_id()

    help_text = (
        "🆘 **Help & Tutorial**\n\n"
        "📌 **Files kaise download karein:**\n"
        "1️⃣ Hamare Update Channel pe jao\n"
        "2️⃣ Kisi bhi file ke link pe click karo\n"
        "3️⃣ Bot turant file bhej dega!\n\n"
        "👑 **Premium Users ko milta hai:**\n"
        "  • Direct link (shortener bypass)\n"
        "  • Priority delivery\n"
        "  • Exclusive content access\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📩 **Support ke liye admin se contact karein**\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "🔖 _Powered by **RAJ DEV**_"
    )

    buttons = [
        [InlineKeyboardButton("👑 Premium Plans", callback_data="premium_plans")],
        [InlineKeyboardButton(
            "📢 Update Channel",
            url=Config.get_channel_url()
        )],
        [InlineKeyboardButton("🔙 Back", callback_data="back_start")],
    ]

    if tutorial_id:
        # Tutorial video alag message mein bhejo
        try:
            await cq.message.reply_video(
                video=tutorial_id,
                caption=(
                    "🎬 **Tutorial Video**\n\n"
                    "Yeh video dekh ke bot use karna seekho!\n\n"
                    "🔖 _Powered by **RAJ DEV**_"
                ),
            )
        except Exception:
            pass

    await cq.message.edit_text(
        help_text,
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    await cq.answer()


@Client.on_callback_query(filters.regex("^back_start$"))
async def cb_back_start(client: Client, cq: CallbackQuery):
    user = cq.from_user
    is_premium = await DB.is_premium(user.id)
    crown = "👑 " if is_premium else ""
    premium_line = "👑 You have **Premium** access!\n\n" if is_premium else ""

    welcome_text = (
        f"✨ **Welcome back, {crown}{user.first_name}!**\n\n"
        "🤖 I am a **Premium File Store Bot**.\n\n"
        + premium_line
        + "👇 Choose an option below:"
    )
    _ch_url = Config.get_channel_url()
    _kb_rows = [
        [
            InlineKeyboardButton("👑 Premium Plans", callback_data="premium_plans"),
            InlineKeyboardButton("ℹ️ About", callback_data="about"),
        ],
    ]
    if _ch_url:
        _kb_rows.append([InlineKeyboardButton("📢 Update Channel", url=_ch_url)])
    _kb_rows.append([InlineKeyboardButton("🆘 Help & Tutorial", callback_data="help_menu")])
    keyboard = InlineKeyboardMarkup(_kb_rows)
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
