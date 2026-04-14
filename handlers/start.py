"""
╔══════════════════════════════════════════════════════════════╗
║                   /start COMMAND HANDLER                     ║
║                                                              ║
║   FLOW:                                                      ║
║   Premium / Admin                                            ║
║     → Seedha file milegi, koi shortlink nahi                 ║
║                                                              ║
║   Regular User (shortener ON)                                ║
║     HAR BAAR shortlink visit karna hoga — koi bypass nahi    ║
║     Step 1: /start file_xxx → Token banao → Shortlink bhejo  ║
║     Step 2: User shortlink visit kare                        ║
║             → /start verify_{user_id}_{token}_{file_id}      ║
║             → Token valid? → File do, token expire karo      ║
║             → Token invalid/used? → Error dikhao             ║
║                                                              ║
║   Regular User (shortener OFF)                               ║
║     → Seedha file milegi                                      ║
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
    shorten_url,
    generate_token,
    check_token,
    verify_user,
    TOKENS,
)

logger = logging.getLogger("StartHandler")


# ══════════════════════════════════════════════════════════════
#  PROMO FLASH
# ══════════════════════════════════════════════════════════════

async def show_promo_flash(message: Message):
    try:
        promo = await message.reply("✨ **RAJ DEV** ✨")
        await asyncio.sleep(1.5)
        await promo.delete()
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════
#  /start HANDLER
# ══════════════════════════════════════════════════════════════

@Client.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    user = message.from_user
    args = message.command[1:]

    # Register user
    await DB.add_user(
        user_id=user.id,
        full_name=user.first_name + (f" {user.last_name}" if user.last_name else ""),
        username=user.username,
    )
    await DB.update_last_active(user.id)

    if args:
        payload = args[0]

        # ── TOKEN VERIFY: /start verify_{user_id}_{token}_{file_id} ──
        if payload.startswith("verify_"):
            await handle_token_verify(client, message, payload)
            return

        # ── FILE REQUEST: /start file_{file_id} ───────────────────
        if payload.startswith("file_"):
            await show_promo_flash(message)
            await handle_file_request(client, message, payload[5:])
            return

    # ── Regular /start: welcome ────────────────────────────────
    anim_msg = await animate_start(message)
    await asyncio.sleep(0.3)

    is_premium   = await DB.is_premium(user.id)
    crown        = "👑 " if is_premium else ""
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

    _ch_url  = Config.get_channel_url()
    _kb_rows = [
        [
            InlineKeyboardButton("👑 Premium Plans", callback_data="premium_plans"),
            InlineKeyboardButton("ℹ️ About", callback_data="about"),
        ],
    ]
    if _ch_url:
        _kb_rows.append([InlineKeyboardButton("📢 Update Channel", url=_ch_url)])
    _kb_rows.append([InlineKeyboardButton("🆘 Help & Tutorial", callback_data="help_menu")])

    await anim_msg.edit_text(welcome_text, reply_markup=InlineKeyboardMarkup(_kb_rows))


# ══════════════════════════════════════════════════════════════
#  TOKEN VERIFY HANDLER
#  Payload: verify_{user_id}_{token}_{file_id}
# ══════════════════════════════════════════════════════════════

async def handle_token_verify(client: Client, message: Message, payload: str):
    try:
        # "verify_" ke baad: {user_id}_{token}_{file_id}
        parts   = payload[7:].split("_", 2)
        req_uid = int(parts[0])
        token   = parts[1]
        file_id = parts[2]
    except Exception:
        await message.reply("❌ **Invalid link!**\n\nYeh link galat hai ya expire ho gaya.")
        return

    actual_uid = message.from_user.id

    # Security: sirf wahi user verify kar sakta hai jiske liye token bana tha
    if req_uid != actual_uid:
        await message.reply(
            "❌ **Yeh link aapke liye nahi hai!**\n\n"
            "Please channel se apna link use karo."
        )
        return

    # Token valid hai aur use nahi hua?
    is_valid = await check_token(actual_uid, token)
    if not is_valid:
        ch_url = Config.get_channel_url()
        await message.reply(
            "⚠️ **Link Expire Ho Gaya!**\n\n"
            "Token already use ho chuka hai ya expire ho gaya.\n"
            "Channel se dobara link tap karo.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 Update Channel", url=ch_url)]
            ]) if ch_url else None
        )
        return

    # ✅ Token valid — consume karo aur file do
    await verify_user(actual_uid, token)

    confirm_msg = await message.reply(
        "✅ **Verification Successful!**\n\n"
        "🎉 Ab aapki file aa rahi hai...\n\n"
        "🔖 _Powered by **RAJ DEV**_"
    )
    await asyncio.sleep(1)
    try:
        await confirm_msg.delete()
    except Exception:
        pass

    # File do — skip_shortlink=True kyunki verify ho chuka hai
    await handle_file_request(client, message, file_id, skip_shortlink=True)


# ══════════════════════════════════════════════════════════════
#  AUTO DELETE HELPER
# ══════════════════════════════════════════════════════════════

async def _auto_delete(file_msg, notice_msg, delay: int):
    try:
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

        try:
            await file_msg.delete()
        except Exception:
            pass
        try:
            await notice_msg.delete()
        except Exception:
            pass

    except Exception as e:
        logger.warning(f"Auto-delete failed: {e}")


# ══════════════════════════════════════════════════════════════
#  ACTUAL FILE DELIVERY
# ══════════════════════════════════════════════════════════════

async def _deliver_file(client: Client, message: Message, file_doc: dict,
                        file_id: str, is_premium: bool, is_admin: bool):
    import os as _os
    AUTO_DELETE_SECONDS = int(_os.environ.get("AUTO_DELETE_TIME", 300))
    minutes = AUTO_DELETE_SECONDS // 60

    direct_url = file_doc.get("direct_url") or ""
    file_emoji = get_file_emoji(file_doc.get("file_type", "document"))
    size_str   = humanize_size(file_doc.get("file_size", 0))
    file_name  = file_doc.get("file_name", "Unknown")
    del_note   = "⚠️ File {} min mein delete ho jaegi — save kar lo! 💾".format(minutes)

    sent_file = await client.copy_message(
        chat_id      = message.chat.id,
        from_chat_id = Config.DB_CHANNEL,
        message_id   = file_doc["message_id"],
    )
    await DB.increment_download(file_id)

    if is_admin or is_premium:
        label   = "👑 Direct Link (Premium)" if is_premium else "🔧 Direct Link (Admin)"
        confirm = (
            "✅ **File Mil Gayi!**\n\n"
            "{} `{}`\n"
            "📦 Size: **{}**\n\n"
            "🔗 {}:\n`{}`\n\n"
            "✨ Shortener bypass — Premium ka fayda!\n\n"
            "{}\n\n"
            "🔖 _Powered by **RAJ DEV**_"
        ).format(file_emoji, file_name, size_str, label, direct_url, del_note)
        buttons = [[InlineKeyboardButton("🔗 Direct Link", url=direct_url)]] if direct_url else []
    else:
        confirm = (
            "✅ **File Mil Gayi!**\n\n"
            "{} `{}`\n"
            "📦 Size: **{}**\n\n"
            "{}\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "💡 Dobara file chahiye? Shortlink visit karna hoga!\n"
            "👑 **Premium lo — seedha file milegi!**\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "🔖 _Powered by **RAJ DEV**_"
        ).format(file_emoji, file_name, size_str, del_note)
        buttons = [
            [InlineKeyboardButton("👑 Premium Lo — Direct File Pao", callback_data="premium_plans")],
        ]

    notice_msg = await message.reply(
        confirm,
        reply_markup=InlineKeyboardMarkup(buttons) if buttons else None,
    )
    asyncio.create_task(_auto_delete(sent_file, notice_msg, AUTO_DELETE_SECONDS))


# ══════════════════════════════════════════════════════════════
#  FILE REQUEST — MAIN LOGIC
# ══════════════════════════════════════════════════════════════

async def handle_file_request(client: Client, message: Message, file_id: str,
                               skip_shortlink: bool = False):
    """
    skip_shortlink=True sirf tab pass karo jab token verify ho chuka ho.
    Warna har baar shortlink visit karna hoga.
    """
    user = message.from_user

    # Anti-spam
    cooldown = check_spam(user.id, Config.REQUEST_DELAY)
    if cooldown > 0:
        await message.reply(
            "⏳ **Slow down!**\n\nPlease wait **{:.1f}s**.".format(cooldown)
        )
        return

    is_admin   = user.id in Config.ADMINS
    is_premium = await DB.is_premium(user.id)

    # Premium Mode gate
    premium_mode = await DB.is_premium_mode()
    if premium_mode and not is_premium and not is_admin:
        await message.reply(
            "🔒 **Premium Mode Active**\n\n"
            "Is bot mein abhi sirf Premium users ko files mil sakti hain.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👑 Premium Plans Dekho", callback_data="premium_plans")]
            ]),
        )
        return

    # Force subscribe check
    if not is_premium and not is_admin:
        subscribed = await check_force_subscribe(client, user.id)
        if not subscribed:
            ch_url = Config.get_channel_url()
            btns   = []
            if ch_url:
                btns.append([InlineKeyboardButton("📢 Channel Join Karo", url=ch_url)])
            btns.append([InlineKeyboardButton("✅ Join Ho Gaya", callback_data="verify_join_" + file_id)])
            await message.reply(
                "⚠️ **Pehle Channel Join Karo!**\n\n"
                "Files pane ke liye channel member hona zaroori hai.",
                reply_markup=InlineKeyboardMarkup(btns),
            )
            return

    # Search animation
    search_msg = await animate_search(message)

    # DB se file fetch
    file_doc = await DB.get_file(file_id)
    if not file_doc:
        await search_msg.edit_text(
            "❌ **File Nahi Mili**\n\nYeh file delete ho gayi ya link galat hai."
        )
        return

    await animate_found(search_msg)
    await asyncio.sleep(0.5)

    try:
        # ── PREMIUM / ADMIN → seedha file ─────────────────────
        if is_admin or is_premium:
            await search_msg.delete()
            await _deliver_file(client, message, file_doc, file_id, is_premium, is_admin)
            return

        shortener_on = await DB.is_shortener_on()

        # ── Shortener OFF → seedha file ───────────────────────
        if not shortener_on:
            await search_msg.delete()
            await _deliver_file(client, message, file_doc, file_id, False, False)
            return

        # ── Token verify ho chuka → file do ───────────────────
        if skip_shortlink:
            await search_msg.delete()
            await _deliver_file(client, message, file_doc, file_id, False, False)
            return

        # ── Regular User + Shortener ON → Token banao ─────────
        # HAR BAAR naya token — koi bypass nahi
        if not Config.BOT_USERNAME:
            me = await client.get_me()
            Config.BOT_USERNAME = me.username

        token = generate_token(7)
        TOKENS[user.id] = {token: False}  # False = not used yet

        verify_link = (
            f"https://t.me/{Config.BOT_USERNAME}"
            f"?start=verify_{user.id}_{token}_{file_id}"
        )

        # Shortlink banao — env var se API key
        api_key   = Config.SHORTENER_API
        short_url = await shorten_url(verify_link, api_key, Config.SHORTENER_SITE)

        # Agar shortener fail hua aur direct link wapas aaya
        if short_url == verify_link:
            logger.warning(f"Shortener failed for user {user.id}, showing error")
            await search_msg.edit_text(
                "⚠️ **Shortener Error!**\n\n"
                "Link shorten nahi ho saka. Thodi der baad try karo.\n\n"
                "👑 **Premium lo — seedha file milegi!**",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("👑 Premium Lo", callback_data="premium_plans")],
                ]),
            )
            return

        file_emoji = get_file_emoji(file_doc.get("file_type", "document"))
        file_name  = file_doc.get("file_name", "Unknown")
        size_str   = humanize_size(file_doc.get("file_size", 0))

        await search_msg.edit_text(
            "📥 **File Ready Hai!**\n\n"
            f"{file_emoji} `{file_name}`\n"
            f"📦 Size: **{size_str}**\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "⚡ **Step 1:** Neeche link pe tap karo\n"
            "⚡ **Step 2:** Link visit karo (5 sec wait karo)\n"
            "⚡ **Step 3:** Wapas bot pe aao → File milegi!\n\n"
            "⚠️ Har baar file ke liye link visit karna hoga!\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "💡 Shortener skip karna hai?\n"
            "👑 **Premium lo — seedha file milegi!**\n\n"
            "🔖 _Powered by **RAJ DEV**_",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 Link Visit Karo — File Pao!", url=short_url)],
                [InlineKeyboardButton("👑 Premium Lo — Direct File Pao", callback_data="premium_plans")],
            ]),
        )

    except Exception as e:
        logger.error("Error in handle_file_request {}: {}".format(file_id, e))
        try:
            await search_msg.edit_text(
                "⚠️ **File Deliver Nahi Hui**\n\nKuch problem aa gayi. Thodi der baad try karo."
            )
        except Exception:
            pass


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
    tutorial_id = await DB.get_tutorial_file_id()

    help_text = (
        "🆘 **Help & Tutorial**\n\n"
        "📌 **Files kaise download karein:**\n"
        "1️⃣ Update Channel pe jao\n"
        "2️⃣ File ke link pe tap karo\n"
        "3️⃣ Shortlink visit karo (5 sec wait karo)\n"
        "4️⃣ Wapas bot pe aao → File mil jaegi!\n\n"
        "⚠️ **Har file ke liye shortlink visit karna hoga!**\n\n"
        "👑 **Premium Users ko milta hai:**\n"
        "  • Seedha file — shortener bypass\n"
        "  • Har baar shortlink nahi\n"
        "  • Priority delivery\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📩 **Support ke liye admin se contact karein**\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "🔖 _Powered by **RAJ DEV**_"
    )

    buttons = [
        [InlineKeyboardButton("👑 Premium Plans", callback_data="premium_plans")],
        [InlineKeyboardButton("📢 Update Channel", url=Config.get_channel_url())],
        [InlineKeyboardButton("🔙 Back", callback_data="back_start")],
    ]

    if tutorial_id:
        try:
            await cq.message.reply_video(
                video=tutorial_id,
                caption="🎬 **Tutorial Video**\n\n🔖 _Powered by **RAJ DEV**_",
            )
        except Exception:
            pass

    await cq.message.edit_text(help_text, reply_markup=InlineKeyboardMarkup(buttons))
    await cq.answer()


@Client.on_callback_query(filters.regex("^back_start$"))
async def cb_back_start(client: Client, cq: CallbackQuery):
    user         = cq.from_user
    is_premium   = await DB.is_premium(user.id)
    crown        = "👑 " if is_premium else ""
    premium_line = "👑 You have **Premium** access!\n\n" if is_premium else ""

    welcome_text = (
        f"✨ **Welcome back, {crown}{user.first_name}!**\n\n"
        "🤖 I am a **Premium File Store Bot**.\n\n"
        + premium_line
        + "👇 Choose an option below:"
    )
    _ch_url  = Config.get_channel_url()
    _kb_rows = [
        [
            InlineKeyboardButton("👑 Premium Plans", callback_data="premium_plans"),
            InlineKeyboardButton("ℹ️ About", callback_data="about"),
        ],
    ]
    if _ch_url:
        _kb_rows.append([InlineKeyboardButton("📢 Update Channel", url=_ch_url)])
    _kb_rows.append([InlineKeyboardButton("🆘 Help & Tutorial", callback_data="help_menu")])

    await cq.message.edit_text(welcome_text, reply_markup=InlineKeyboardMarkup(_kb_rows))
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
    file_id    = cq.data.split("_", 2)[2]
    subscribed = await check_force_subscribe(client, cq.from_user.id)
    if subscribed:
        await cq.answer("✅ Verified! Fetching your file now...", show_alert=True)
        await cq.message.delete()
        await handle_file_request(client, cq.message, file_id)
    else:
        await cq.answer("❌ You haven't joined yet!", show_alert=True)
