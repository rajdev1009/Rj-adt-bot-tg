"""
╔══════════════════════════════════════════════════════════════╗
║                   ADMIN COMMAND HANDLERS                     ║
║   Credit: RAJ DEV                                            ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import asyncio
import logging
from datetime import datetime, timezone
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated

from config import Config
from database import DB
from utils.decorators import admin_only

logger = logging.getLogger("AdminCommands")

RESET_PASSWORD = os.environ.get("DELETE_PASSWORD", "782447")


def _is_admin(_, __, message: Message) -> bool:
    return message.from_user and message.from_user.id in Config.ADMINS

admin_filter = filters.create(_is_admin)


# ══════════════════════════════════════════════════════════════
#  /add_premium
# ══════════════════════════════════════════════════════════════

@Client.on_message(filters.command("add_premium") & admin_filter & filters.private)
@admin_only
async def add_premium_cmd(client: Client, message: Message):
    args = message.command[1:]
    if len(args) < 2:
        await message.reply(
            "Usage: `/add_premium <user_id> <days>`\n"
            "Example: `/add_premium 123456789 30`"
        )
        return
    try:
        target_id = int(args[0])
        days = int(args[1])
    except ValueError:
        await message.reply("Invalid user_id or days.")
        return

    await DB.add_premium(target_id, days, added_by=message.from_user.id)
    expiry = await DB.get_premium_expiry(target_id)
    expiry_str = expiry.strftime("%Y-%m-%d %H:%M UTC") if expiry else "Unknown"

    await message.reply(
        "✅ **Premium Granted!**\n\n"
        f"👤 User ID: `{target_id}`\n"
        f"⏳ Duration: **{days} days**\n"
        f"📅 Expires: `{expiry_str}`\n\n"
        "🔖 _Powered by **RAJ DEV**_"
    )
    try:
        await client.send_message(
            target_id,
            "🎉 **Congratulations!**\n\n"
            "Aapko **Premium** access mil gaya!\n"
            f"📅 Expiry: `{expiry_str}`\n\n"
            "🔖 _Powered by **RAJ DEV**_"
        )
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════
#  /remove_premium
# ══════════════════════════════════════════════════════════════

@Client.on_message(filters.command("remove_premium") & admin_filter & filters.private)
@admin_only
async def remove_premium_cmd(client: Client, message: Message):
    args = message.command[1:]
    if not args:
        await message.reply("Usage: `/remove_premium <user_id>`")
        return
    try:
        target_id = int(args[0])
    except ValueError:
        await message.reply("Invalid user ID.")
        return
    await DB.remove_premium(target_id)
    await message.reply(f"✅ Premium removed for `{target_id}`.")


# ══════════════════════════════════════════════════════════════
#  /ban
# ══════════════════════════════════════════════════════════════

@Client.on_message(filters.command("ban") & admin_filter & filters.private)
@admin_only
async def ban_cmd(client: Client, message: Message):
    args = message.command[1:]
    if not args:
        await message.reply("Usage: `/ban <user_id>`")
        return
    try:
        target_id = int(args[0])
    except ValueError:
        await message.reply("Invalid user ID.")
        return
    await DB.ban_user(target_id)
    await message.reply(f"🚫 User `{target_id}` banned.")


# ══════════════════════════════════════════════════════════════
#  /stats
# ══════════════════════════════════════════════════════════════

@Client.on_message(filters.command("stats") & admin_filter & filters.private)
@admin_only
async def stats_cmd(client: Client, message: Message):
    user_count = await DB.get_user_count()
    shortener_on = await DB.is_shortener_on()
    premium_mode = await DB.is_premium_mode()
    await message.reply(
        "📊 **Bot Statistics**\n\n"
        f"👥 Total Users: `{user_count}`\n"
        f"🔗 Shortener: `{'🟢 ON' if shortener_on else '🔴 OFF'}`\n"
        f"👑 Premium Mode: `{'🟢 ON' if premium_mode else '🔴 OFF'}`\n\n"
        f"🕒 `{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}`\n\n"
        "🔖 _Powered by **RAJ DEV**_"
    )


# ══════════════════════════════════════════════════════════════
#  /broadcast
# ══════════════════════════════════════════════════════════════

@Client.on_message(filters.command("broadcast") & admin_filter & filters.private)
@admin_only
async def broadcast_cmd(client: Client, message: Message):
    if not message.reply_to_message:
        await message.reply(
            "Kisi bhi message ko reply karo `/broadcast` se.\n"
            "Wo message sab users ko bheja jaega."
        )
        return

    broadcast_msg = message.reply_to_message
    user_ids = await DB.get_all_user_ids()
    total = len(user_ids)

    if total == 0:
        await message.reply("No users in database.")
        return

    status_msg = await message.reply(
        f"📡 **Broadcasting...**\n\n"
        f"👥 Total: `{total}`\n"
        "⏳ Please wait..."
    )

    success = 0
    failed = 0

    for uid in user_ids:
        try:
            await broadcast_msg.copy(uid)
            success += 1
        except FloodWait as e:
            await asyncio.sleep(e.value + 2)
            try:
                await broadcast_msg.copy(uid)
                success += 1
            except Exception:
                failed += 1
        except (UserIsBlocked, InputUserDeactivated):
            failed += 1
        except Exception:
            failed += 1

        if (success + failed) % 50 == 0:
            try:
                await status_msg.edit_text(
                    f"📡 **Broadcasting...**\n\n"
                    f"👥 Total: `{total}`\n"
                    f"✅ Sent: `{success}`\n"
                    f"❌ Failed: `{failed}`\n"
                    f"⏳ Remaining: `{total - success - failed}`"
                )
            except Exception:
                pass
        await asyncio.sleep(0.05)

    await status_msg.edit_text(
        "✅ **Broadcast Complete!**\n\n"
        f"👥 Total: `{total}`\n"
        f"✅ Delivered: `{success}`\n"
        f"❌ Failed: `{failed}`\n\n"
        "🔖 _Powered by **RAJ DEV**_"
    )


# ══════════════════════════════════════════════════════════════
#  /add_tutorial
# ══════════════════════════════════════════════════════════════

@Client.on_message(filters.command("add_tutorial") & admin_filter & filters.private)
@admin_only
async def add_tutorial_cmd(client: Client, message: Message):
    replied = message.reply_to_message
    if not replied:
        await message.reply(
            "Steps:\n"
            "1. Bot mein tutorial video bhejo\n"
            "2. Us video ko reply karo `/add_tutorial` se"
        )
        return

    if replied.video:
        file_id = replied.video.file_id
    elif replied.document and replied.document.mime_type and "video" in replied.document.mime_type:
        file_id = replied.document.file_id
    else:
        await message.reply("Sirf VIDEO reply karo!")
        return

    await DB.set_tutorial_file_id(file_id)
    await message.reply(
        "✅ **Tutorial video set ho gaya!**\n\n"
        "Users ko /help pe dikhega.\n\n"
        "🔖 _Powered by **RAJ DEV**_"
    )


# ══════════════════════════════════════════════════════════════
#  /set_about
# ══════════════════════════════════════════════════════════════

@Client.on_message(filters.command("set_about") & admin_filter & filters.private)
@admin_only
async def set_about_cmd(client: Client, message: Message):
    text = " ".join(message.command[1:]).strip()
    if not text:
        await message.reply("Usage: `/set_about <text>`")
        return
    await DB.set_about_text(text)
    await message.reply("✅ About text updated!")


# ══════════════════════════════════════════════════════════════
#  /set_plans
# ══════════════════════════════════════════════════════════════

@Client.on_message(filters.command("set_plans") & admin_filter & filters.private)
@admin_only
async def set_plans_cmd(client: Client, message: Message):
    text = " ".join(message.command[1:]).strip()
    if not text:
        await message.reply("Usage: `/set_plans <text>`")
        return
    await DB.set_premium_text(text)
    await message.reply("✅ Premium plans text updated!")


# ══════════════════════════════════════════════════════════════
#  /reset — Poora database reset karo
#
#  Kya hoga reset ke baad:
#    ✅ Saari files delete
#    ✅ Sab users delete
#    ✅ Sab premium delete
#    ✅ Sab settings delete (shortener, premium mode, about, plans)
#    → Bot bilkul fresh install jaisa ho jaega
#
#  Usage: /reset <password>
#  Password ENV: DELETE_PASSWORD (default: 782447)
# ══════════════════════════════════════════════════════════════

@Client.on_message(filters.command("reset") & admin_filter & filters.private)
@admin_only
async def reset_cmd(client: Client, message: Message):
    args = message.command[1:]

    # Step 1: Password nahi diya — usage dikhao
    if not args:
        await message.reply(
            "⚠️ **FULL SYSTEM RESET**\n\n"
            "Yeh command poora database wipe kar dega:\n\n"
            "🗑 Files — sab delete\n"
            "👥 Users — sab delete\n"
            "👑 Premium — sab delete\n"
            "⚙️ Settings — sab delete\n\n"
            "Bot bilkul fresh ho jaega.\n\n"
            "Usage: `/reset <password>`\n"
            "Example: `/reset 782447`\n\n"
            "🔖 _Powered by **RAJ DEV**_"
        )
        return

    # Step 2: Password check
    if args[0].strip() != RESET_PASSWORD:
        await message.reply(
            "❌ **Wrong Password!**\n\n"
            "ENV var `DELETE_PASSWORD` check karo.\n\n"
            "🔖 _Powered by **RAJ DEV**_"
        )
        return

    # Step 3: Confirmation button dikhao
    await message.reply(
        "🚨 **ARE YOU SURE?**\n\n"
        "Yeh action **UNDO nahi hoga!**\n\n"
        "Poora database wipe ho jaega.\n"
        "Files, Users, Premium, Settings\n"
        "sab kuch permanently delete hoga.\n\n"
        "Confirm karne ke liye neeche button dabao:",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Haan, Reset Karo", callback_data="confirm_reset"),
                InlineKeyboardButton("❌ Cancel", callback_data="cancel_reset"),
            ]
        ])
    )


@Client.on_callback_query(filters.regex("^confirm_reset$"))
async def cb_confirm_reset(client: Client, cq: CallbackQuery):
    # Sirf admin hi reset kar sakta hai
    if cq.from_user.id not in Config.ADMINS:
        await cq.answer("Unauthorized!", show_alert=True)
        return

    await cq.answer()
    await cq.message.edit_text("⏳ **Resetting database...**\n\nPlease wait...")

    try:
        result = await DB.reset_all()

        await cq.message.edit_text(
            "✅ **FULL RESET COMPLETE!**\n\n"
            "Database ab bilkul fresh hai:\n\n"
            f"🗑 Files deleted: `{result['files']}`\n"
            f"👥 Users deleted: `{result['users']}`\n"
            f"👑 Premium deleted: `{result['premium']}`\n"
            f"⚙️ Settings deleted: `{result['settings']}`\n\n"
            "Bot fresh install jaisa ho gaya.\n\n"
            "🔖 _Powered by **RAJ DEV**_"
        )
        logger.warning(
            f"FULL RESET by admin {cq.from_user.id} — "
            f"files={result['files']} users={result['users']} "
            f"premium={result['premium']} settings={result['settings']}"
        )

    except Exception as e:
        logger.error(f"Reset failed: {e}")
        await cq.message.edit_text(
            f"❌ **Reset Failed**\n\n`{e}`\n\n"
            "🔖 _Powered by **RAJ DEV**_"
        )


@Client.on_callback_query(filters.regex("^cancel_reset$"))
async def cb_cancel_reset(client: Client, cq: CallbackQuery):
    if cq.from_user.id not in Config.ADMINS:
        await cq.answer("Unauthorized!", show_alert=True)
        return
    await cq.answer("Reset cancelled.")
    await cq.message.edit_text(
        "✅ **Reset Cancelled.**\n\n"
        "Kuch delete nahi hua.\n\n"
        "🔖 _Powered by **RAJ DEV**_"
    )
