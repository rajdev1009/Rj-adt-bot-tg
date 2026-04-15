"""
╔══════════════════════════════════════════════════════════════╗
║                   /start COMMAND HANDLER                     ║
║                                                              ║
║   FLOW:                                                      ║
║   Premium / Admin → Seedha file                              ║
║   Regular User (shortener ON):                               ║
║     Step 1: /start file_xxx → Naya token → Shortlink bhejo  ║
║     Step 2: User shortlink visit kare                        ║
║             → /start verify_{uid}_{token}_{file_id}          ║
║             → Token valid? → File do, token expire karo      ║
║   Regular User (shortener OFF) → Seedha file                 ║
║                                                              ║
║   Credit: RAJ DEV                                            ║
╚══════════════════════════════════════════════════════════════╝
"""

import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery,
)
from config import Config
from database import DB
from utils import (
    animate_start, animate_search, animate_found,
    humanize_size, get_file_emoji, check_spam,
    check_force_subscribe, shorten_url,
    generate_token, check_token, verify_user, TOKENS,
)

logger = logging.getLogger("StartHandler")


async def _promo_flash(message: Message):
    try:
        p = await message.reply("✨ **RAJ DEV** ✨")
        await asyncio.sleep(1.5)
        await p.delete()
    except Exception:
        pass


@Client.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    user = message.from_user
    args = message.command[1:]

    await DB.add_user(
        user_id   = user.id,
        full_name = user.first_name + (f" {user.last_name}" if user.last_name else ""),
        username  = user.username,
    )
    await DB.update_last_active(user.id)

    if args:
        payload = args[0]
        if payload.startswith("verify_"):
            await _handle_token_verify(client, message, payload)
            return
        if payload.startswith("file_"):
            await _promo_flash(message)
            await handle_file_request(client, message, payload[5:])
            return

    anim_msg   = await animate_start(message)
    await asyncio.sleep(0.3)
    is_premium = await DB.is_premium(user.id)
    crown      = "👑 " if is_premium else ""
    prem_line  = "👑 You have **Premium** access!\n\n" if is_premium else ""

    text = (
        f"✨ **Welcome, {crown}{user.first_name}!**\n\n"
        "🤖 I am a **Premium File Store Bot**.\n"
        "📦 Files securely store aur deliver karta hoon.\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "💎 Upgrade to **Premium** for extra perks\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        + prem_line + "👇 Choose an option below:"
    )
    _ch_url  = Config.get_channel_url()
    _kb_rows = [
        [InlineKeyboardButton("👑 Premium Plans", callback_data="premium_plans"),
         InlineKeyboardButton("ℹ️ About", callback_data="about")],
    ]
    if _ch_url:
        _kb_rows.append([InlineKeyboardButton("📢 Update Channel", url=_ch_url)])
    _kb_rows.append([InlineKeyboardButton("🆘 Help", callback_data="help_menu")])
    await anim_msg.edit_text(text, reply_markup=InlineKeyboardMarkup(_kb_rows))


async def _handle_token_verify(client: Client, message: Message, payload: str):
    try:
        parts   = payload[7:].split("_", 2)
        req_uid = int(parts[0])
        token   = parts[1]
        file_id = parts[2]
    except Exception:
        await message.reply("❌ **Invalid link!** Yeh link galat hai ya expire ho gaya.")
        return

    actual_uid = message.from_user.id

    if req_uid != actual_uid:
        await message.reply("❌ **Yeh link aapke liye nahi hai!**\n\nChannel se apna link use karo.")
        return

    if not await check_token(actual_uid, token):
        ch_url = Config.get_channel_url()
        await message.reply(
            "⚠️ **Link Expire Ho Gaya!**\n\n"
            "Token already use ho chuka hai.\n"
            "Channel se dobara link tap karo.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 Update Channel", url=ch_url)]
            ]) if ch_url else None
        )
        return

    await verify_user(actual_uid, token)
    msg = await message.reply(
        "✅ **Verification Successful!**\n\n🎉 File aa rahi hai...\n\n🔖 _Powered by **RAJ DEV**_"
    )
    await asyncio.sleep(1)
    try:
        await msg.delete()
    except Exception:
        pass
    await handle_file_request(client, message, file_id, skip_shortlink=True)


async def _auto_delete(file_msg, notice_msg, delay: int):
    try:
        if delay > 60:
            await asyncio.sleep(delay - 60)
            try:
                await notice_msg.edit_text(
                    "⏳ **1 minute mein file delete ho jaegi!**\n\nAbhi save kar lo! 💾\n\n🔖 _Powered by **RAJ DEV**_"
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


async def _deliver_file(client: Client, message: Message, file_doc: dict,
                        file_id: str, is_premium: bool, is_admin: bool):
    import os as _os
    AUTO_DEL  = int(_os.environ.get("AUTO_DELETE_TIME", Config.AUTO_DELETE_TIME))
    minutes   = AUTO_DEL // 60
    direct_url = file_doc.get("direct_url") or ""
    emoji      = get_file_emoji(file_doc.get("file_type", "document"))
    size_str   = humanize_size(file_doc.get("file_size", 0))
    file_name  = file_doc.get("file_name", "Unknown")
    del_note   = f"⚠️ File {minutes} min mein delete ho jaegi — save kar lo! 💾"

    sent_file = await client.copy_message(
        chat_id      = message.chat.id,
        from_chat_id = Config.DB_CHANNEL,
        message_id   = file_doc["message_id"],
    )
    await DB.increment_download(file_id)

    if is_admin or is_premium:
        label   = "👑 Direct Link (Premium)" if is_premium else "🔧 Direct Link (Admin)"
        confirm = (
            f"✅ **File Mil Gayi!**\n\n{emoji} `{file_name}`\n📦 Size: **{size_str}**\n\n"
            f"🔗 {label}:\n`{direct_url}`\n\n✨ Shortener bypass — Premium ka fayda!\n\n"
            f"{del_note}\n\n🔖 _Powered by **RAJ DEV**_"
        )
        buttons = [[InlineKeyboardButton("🔗 Direct Link", url=direct_url)]] if direct_url else []
    else:
        confirm = (
            f"✅ **File Mil Gayi!**\n\n{emoji} `{file_name}`\n📦 Size: **{size_str}**\n\n"
            f"{del_note}\n\n━━━━━━━━━━━━━━━━━━━━\n"
            f"💡 Shortener skip karna hai?\n👑 **Premium lo — seedha file milegi!**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n🔖 _Powered by **RAJ DEV**_"
        )
        buttons = [[InlineKeyboardButton("👑 Premium Lo — Direct File Pao", callback_data="premium_plans")]]

    notice_msg = await message.reply(confirm, reply_markup=InlineKeyboardMarkup(buttons) if buttons else None)
    asyncio.create_task(_auto_delete(sent_file, notice_msg, AUTO_DEL))


async def handle_file_request(client: Client, message: Message, file_id: str,
                               skip_shortlink: bool = False):
    user = message.from_user

    cooldown = check_spam(user.id, Config.REQUEST_DELAY)
    if cooldown > 0:
        await message.reply(f"⏳ **Slow down!**\n\nPlease wait **{cooldown:.1f}s**.")
        return

    is_admin   = user.id in Config.ADMINS
    is_premium = await DB.is_premium(user.id)

    if await DB.is_premium_mode() and not is_premium and not is_admin:
        await message.reply(
            "🔒 **Premium Mode Active**\n\nAbhi sirf Premium users ko files milti hain.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("👑 Premium Plans", callback_data="premium_plans")]]),
        )
        return

    if not is_premium and not is_admin:
        if not await check_force_subscribe(client, user.id):
            ch_url = Config.get_channel_url()
            btns   = []
            if ch_url:
                btns.append([InlineKeyboardButton("📢 Channel Join Karo", url=ch_url)])
            btns.append([InlineKeyboardButton("✅ Join Ho Gaya", callback_data="verify_join_" + file_id)])
            await message.reply(
                "⚠️ **Pehle Channel Join Karo!**\n\nFiles pane ke liye channel member hona zaroori hai.",
                reply_markup=InlineKeyboardMarkup(btns),
            )
            return

    search_msg = await animate_search(message)
    file_doc   = await DB.get_file(file_id)
    if not file_doc:
        await search_msg.edit_text("❌ **File Nahi Mili**\n\nYeh file delete ho gayi ya link galat hai.")
        return

    await animate_found(search_msg)
    await asyncio.sleep(0.5)

    try:
        if is_admin or is_premium:
            await search_msg.delete()
            await _deliver_file(client, message, file_doc, file_id, is_premium, is_admin)
            return

        if not await DB.is_shortener_on():
            await search_msg.delete()
            await _deliver_file(client, message, file_doc, file_id, False, False)
            return

        if skip_shortlink:
            await search_msg.delete()
            await _deliver_file(client, message, file_doc, file_id, False, False)
            return

        # Naya token banao
        if not Config.BOT_USERNAME:
            me = await client.get_me()
            Config.BOT_USERNAME = me.username

        token = generate_token(7)
        TOKENS[user.id] = {token: False}

        verify_link = f"https://t.me/{Config.BOT_USERNAME}?start=verify_{user.id}_{token}_{file_id}"
        short_url   = await shorten_url(verify_link)

        if short_url == verify_link:
            await search_msg.edit_text(
                "⚠️ **Shortener Error!**\n\nLink shorten nahi ho saka. Thodi der baad try karo.\n\n"
                "👑 **Premium lo — seedha file milegi!**",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("👑 Premium Lo", callback_data="premium_plans")]]),
            )
            return

        emoji    = get_file_emoji(file_doc.get("file_type", "document"))
        size_str = humanize_size(file_doc.get("file_size", 0))
        fname    = file_doc.get("file_name", "Unknown")

        await search_msg.edit_text(
            f"📥 **File Ready Hai!**\n\n{emoji} `{fname}`\n📦 Size: **{size_str}**\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⚡ **Step 1:** Neeche link pe tap karo\n"
            f"⚡ **Step 2:** Link visit karo (5 sec wait karo)\n"
            f"⚡ **Step 3:** Wapas bot pe aao → File milegi!\n\n"
            f"⚠️ Har baar file ke liye link visit karna hoga!\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💡 Shortener skip karna hai?\n👑 **Premium lo — seedha file milegi!**\n\n"
            f"🔖 _Powered by **RAJ DEV**_",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 Link Visit Karo — File Pao!", url=short_url)],
                [InlineKeyboardButton("👑 Premium Lo — Direct File Pao", callback_data="premium_plans")],
            ]),
        )
    except Exception as e:
        logger.error(f"handle_file_request error {file_id}: {e}")
        try:
            await search_msg.edit_text("⚠️ **File Deliver Nahi Hui**\n\nThodi der baad try karo.")
        except Exception:
            pass


@Client.on_callback_query(filters.regex("^premium_plans$"))
async def cb_premium_plans(client: Client, cq: CallbackQuery):
    await cq.message.edit_text(await DB.get_premium_text(),
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_start")]]))
    await cq.answer()


@Client.on_callback_query(filters.regex("^about$"))
async def cb_about(client: Client, cq: CallbackQuery):
    await cq.message.edit_text(await DB.get_about_text(),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🆘 Help", callback_data="help_menu")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_start")],
        ]))
    await cq.answer()


@Client.on_callback_query(filters.regex("^help_menu$"))
async def cb_help_menu(client: Client, cq: CallbackQuery):
    tutorial_id = await DB.get_tutorial_file_id()
    text = (
        "🆘 **Help & Tutorial**\n\n"
        "📌 **Files kaise download karein:**\n"
        "1️⃣ Update Channel pe jao\n2️⃣ File ke link pe tap karo\n"
        "3️⃣ Shortlink visit karo (5 sec wait karo)\n"
        "4️⃣ Wapas bot pe aao → File mil jaegi!\n\n"
        "⚠️ **Har file ke liye shortlink visit karna hoga!**\n\n"
        "👑 **Premium Users:**\n  • Seedha file — shortener bypass\n\n"
        "🔖 _Powered by **RAJ DEV**_"
    )
    btns = [
        [InlineKeyboardButton("👑 Premium Plans", callback_data="premium_plans")],
        [InlineKeyboardButton("📢 Update Channel", url=Config.get_channel_url())],
        [InlineKeyboardButton("🔙 Back", callback_data="back_start")],
    ]
    if tutorial_id:
        try:
            await cq.message.reply_video(video=tutorial_id,
                caption="🎬 **Tutorial Video**\n\n🔖 _Powered by **RAJ DEV**_")
        except Exception:
            pass
    await cq.message.edit_text(text, reply_markup=InlineKeyboardMarkup(btns))
    await cq.answer()


@Client.on_callback_query(filters.regex("^back_start$"))
async def cb_back_start(client: Client, cq: CallbackQuery):
    user       = cq.from_user
    is_premium = await DB.is_premium(user.id)
    crown      = "👑 " if is_premium else ""
    prem_line  = "👑 You have **Premium** access!\n\n" if is_premium else ""
    text = (
        f"✨ **Welcome back, {crown}{user.first_name}!**\n\n"
        "🤖 I am a **Premium File Store Bot**.\n\n" + prem_line + "👇 Choose an option below:"
    )
    _ch_url  = Config.get_channel_url()
    _kb_rows = [[InlineKeyboardButton("👑 Premium Plans", callback_data="premium_plans"),
                 InlineKeyboardButton("ℹ️ About", callback_data="about")]]
    if _ch_url:
        _kb_rows.append([InlineKeyboardButton("📢 Update Channel", url=_ch_url)])
    _kb_rows.append([InlineKeyboardButton("🆘 Help", callback_data="help_menu")])
    await cq.message.edit_text(text, reply_markup=InlineKeyboardMarkup(_kb_rows))
    await cq.answer()


@Client.on_callback_query(filters.regex("^check_join$"))
async def cb_check_join(client: Client, cq: CallbackQuery):
    if await check_force_subscribe(client, cq.from_user.id):
        await cq.answer("✅ Verified!", show_alert=True)
        await cq.message.delete()
    else:
        await cq.answer("❌ You haven't joined yet!", show_alert=True)


@Client.on_callback_query(filters.regex(r"^verify_join_(.+)$"))
async def cb_verify_join(client: Client, cq: CallbackQuery):
    file_id = cq.data.split("_", 2)[2]
    if await check_force_subscribe(client, cq.from_user.id):
        await cq.answer("✅ Verified! Fetching file...", show_alert=True)
        await cq.message.delete()
        await handle_file_request(client, cq.message, file_id)
    else:
        await cq.answer("❌ You haven't joined yet!", show_alert=True)
