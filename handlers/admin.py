"""
╔══════════════════════════════════════════════════════════════╗
║                   ADMIN COMMAND HANDLERS                     ║
║   /add_premium  /broadcast  /add_tutorial  /ban  /stats     ║
║                                                              ║
║   Credit: RAJ DEV                                            ║
╚══════════════════════════════════════════════════════════════╝
"""

import asyncio
import logging
from datetime import datetime, timezone
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated

from config import Config
from database import DB
from utils.decorators import admin_only

logger = logging.getLogger("AdminCommands")


def _is_admin(_, __, message: Message) -> bool:
    return message.from_user and message.from_user.id in Config.ADMINS

admin_filter = filters.create(_is_admin)


# ══════════════════════════════════════════════════════════════
#  /add_premium <user_id> <days>
# ══════════════════════════════════════════════════════════════

@Client.on_message(filters.command("add_premium") & admin_filter & filters.private)
@admin_only
async def add_premium_cmd(client: Client, message: Message):
    args = message.command[1:]
    if len(args) < 2:
        await message.reply(
            "❌ **Usage:** `/add_premium <user_id> <days>`\n\n"
            "_Example:_ `/add_premium 123456789 30`"
        )
        return

    try:
        target_id = int(args[0])
        days      = int(args[1])
    except ValueError:
        await message.reply("❌ Invalid user ID or days. Dono integer hone chahiye.")
        return

    await DB.add_premium(target_id, days, added_by=message.from_user.id)
    expiry = await DB.get_premium_expiry(target_id)
    expiry_str = expiry.strftime("%Y-%m-%d %H:%M UTC") if expiry else "Unknown"

    await message.reply(
        f"✅ **Premium Granted!**\n\n"
        f"👤 User ID: `{target_id}`\n"
        f"⏳ Duration: **{days} days**\n"
        f"📅 Expires: `{expiry_str}`\n\n"
        f"🔖 _Powered by **RAJ DEV**_"
    )

    try:
        await client.send_message(
            target_id,
            f"🎉 **Congratulations!**\n\n"
            f"Aapko **Premium** access mil gaya hai!\n"
            f"📅 Expiry: `{expiry_str}`\n\n"
            f"Premium ke saare fayde enjoy karein! 👑\n\n"
            f"🔖 _Powered by **RAJ DEV**_"
        )
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════
#  /remove_premium <user_id>
# ══════════════════════════════════════════════════════════════

@Client.on_message(filters.command("remove_premium") & admin_filter & filters.private)
@admin_only
async def remove_premium_cmd(client: Client, message: Message):
    args = message.command[1:]
    if not args:
        await message.reply("❌ **Usage:** `/remove_premium <user_id>`")
        return
    try:
        target_id = int(args[0])
    except ValueError:
        await message.reply("❌ Invalid user ID.")
        return

    await DB.remove_premium(target_id)
    await message.reply(f"✅ Premium removed for user `{target_id}`.")


# ══════════════════════════════════════════════════════════════
#  /ban <user_id>
# ══════════════════════════════════════════════════════════════

@Client.on_message(filters.command("ban") & admin_filter & filters.private)
@admin_only
async def ban_cmd(client: Client, message: Message):
    args = message.command[1:]
    if not args:
        await message.reply("❌ **Usage:** `/ban <user_id>`")
        return
    try:
        target_id = int(args[0])
    except ValueError:
        await message.reply("❌ Invalid user ID.")
        return
    await DB.ban_user(target_id)
    await message.reply(f"🚫 User `{target_id}` ban ho gaya.")


# ══════════════════════════════════════════════════════════════
#  /stats
# ══════════════════════════════════════════════════════════════

@Client.on_message(filters.command("stats") & admin_filter & filters.private)
@admin_only
async def stats_cmd(client: Client, message: Message):
    user_count   = await DB.get_user_count()
    shortener_on = await DB.is_shortener_on()
    premium_mode = await DB.is_premium_mode()

    await message.reply(
        f"📊 **Bot Statistics**\n\n"
        f"👥 Total Users: `{user_count}`\n"
        f"🔗 Shortener: `{'🟢 ON' if shortener_on else '🔴 OFF'}`\n"
        f"👑 Premium Mode: `{'🟢 ON' if premium_mode else '🔴 OFF'}`\n\n"
        f"🕒 Server Time: `{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}`\n\n"
        f"🔖 _Powered by **RAJ DEV**_"
    )


# ══════════════════════════════════════════════════════════════
#  /broadcast (reply to any message)
# ══════════════════════════════════════════════════════════════

@Client.on_message(filters.command("broadcast") & admin_filter & filters.private)
@admin_only
async def broadcast_cmd(client: Client, message: Message):
    if not message.reply_to_message:
        await message.reply(
            "❌ **Usage:** Kisi bhi message ko reply karo `/broadcast` se\n\n"
            "_Wo message sab users ko bheja jaega._"
        )
        return

    broadcast_msg = message.reply_to_message
    user_ids      = await DB.get_all_user_ids()
    total         = len(user_ids)

    if total == 0:
        await message.reply("ℹ️ Database mein koi user nahi hai.")
        return

    status_msg = await message.reply(
        f"📡 **Broadcasting...**\n\n"
        f"👥 Total users: `{total}`\n"
        f"⏳ Please wait..."
    )

    success = 0
    failed  = 0

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
        f"✅ **Broadcast Complete!**\n\n"
        f"👥 Total users: `{total}`\n"
        f"✅ Delivered: `{success}`\n"
        f"❌ Failed: `{failed}`\n\n"
        f"🔖 _Powered by **RAJ DEV**_"
    )


# ══════════════════════════════════════════════════════════════
#  /add_tutorial — Video ko reply karke
# ══════════════════════════════════════════════════════════════

@Client.on_message(filters.command("add_tutorial") & admin_filter & filters.private)
@admin_only
async def add_tutorial_cmd(client: Client, message: Message):
    """
    Kisi bhi VIDEO ko reply karo /add_tutorial se.
    Wo video /help command pe dikhegi.

    Example:
      1. Pehle tutorial video bhejo bot mein
      2. Us video ko reply karo /add_tutorial se
      3. Done!
    """
    replied = message.reply_to_message

    if not replied:
        await message.reply(
            "❌ **Pehle ek video bhejo, phir us video ko reply karo:**\n\n"
            "`/add_tutorial`\n\n"
            "**Steps:**\n"
            "1️⃣ Bot mein tutorial video bhejo\n"
            "2️⃣ Us video ko select karo (long press)\n"
            "3️⃣ Reply mein `/add_tutorial` likho\n"
            "4️⃣ Send karo!"
        )
        return

    # Video ya document (video file) dono accept karo
    if replied.video:
        file_id   = replied.video.file_id
        file_type = "video"
    elif replied.document and replied.document.mime_type and "video" in replied.document.mime_type:
        file_id   = replied.document.file_id
        file_type = "document"
    else:
        await message.reply(
            "❌ **Sirf VIDEO reply karo!**\n\n"
            "Aapne jo reply kiya hai wo video nahi hai.\n"
            "Ek video bhejo aur phir us par `/add_tutorial` reply karo."
        )
        return

    await DB.set_tutorial_file_id(file_id)
    await message.reply(
        "✅ **Tutorial video set ho gaya!**\n\n"
        "Ab jab bhi users `/help` karenge ya\n"
        "**Help & Tutorial** button dabayenge,\n"
        "unhe yeh video dikhega.\n\n"
        "🔖 _Powered by **RAJ DEV**_"
    )


# ══════════════════════════════════════════════════════════════
#  /set_about <text>
# ══════════════════════════════════════════════════════════════

@Client.on_message(filters.command("set_about") & admin_filter & filters.private)
@admin_only
async def set_about_cmd(client: Client, message: Message):
    text = " ".join(message.command[1:]).strip()
    if not text:
        await message.reply(
            "❌ **Usage:** `/set_about <naya about text>`\n\n"
            "Markdown supported hai."
        )
        return
    await DB.set_about_text(text)
    await message.reply("✅ **About text update ho gaya!**")


# ══════════════════════════════════════════════════════════════
#  /set_plans <text>
# ══════════════════════════════════════════════════════════════

@Client.on_message(filters.command("set_plans") & admin_filter & filters.private)
@admin_only
async def set_plans_cmd(client: Client, message: Message):
    text = " ".join(message.command[1:]).strip()
    if not text:
        await message.reply(
            "❌ **Usage:** `/set_plans <naya plans text>`\n\n"
            "Markdown supported hai."
        )
        return
    await DB.set_premium_text(text)
    await message.reply("✅ **Premium plans text update ho gaya!**")


# ══════════════════════════════════════════════════════════════
#  /delete_all — Saari files DB se delete karo (password protected)
#  Password ENV: DELETE_PASSWORD (default: 782447)
# ══════════════════════════════════════════════════════════════

import os as _os

@Client.on_message(filters.command("delete_all") & admin_filter & filters.private)
@admin_only
async def delete_all_cmd(client: Client, message: Message):
    """
    Saari saved files DB se delete karo.
    Password required — ENV: DELETE_PASSWORD

    Usage:
      /delete_all <password>
    Example:
      /delete_all 782447
    """
    args = message.command[1:]

    # Password check
    correct_password = _os.environ.get("DELETE_PASSWORD", "782447")

    if not args:
        await message.reply(
            "🗑️ **Delete All Files**\n\n"
            "Yeh command DB mein save saari files delete kar degi.\n\n"
            "⚠️ **Yeh action undo nahi hoga!**\n\n"
            "Usage: `/delete_all <password>`\n"
            "Example: `/delete_all 782447`\n\n"
            "🔖 _Powered by **RAJ DEV**_"
        )
        return

    entered_password = args[0].strip()

    if entered_password != correct_password:
        await message.reply(
            "❌ **Wrong Password!**\n\n"
            "Galat password diya hai.\n"
            "Sahi password ENV var `DELETE_PASSWORD` mein set hai.\n\n"
            "🔖 _Powered by **RAJ DEV**_"
        )
        return

    # Confirm message
    confirm_msg = await message.reply(
        "🗑️ **Deleting all files from database...**\n\n"
        "⏳ Please wait..."
    )

    try:
        deleted_count = await DB.delete_all_files()
        await confirm_msg.edit_text(
            f"✅ **All Files Deleted!**\n\n"
            f"🗑️ Total deleted: `{deleted_count}` files\n\n"
            f"⚠️ Note: DB channel mein files abhi bhi hain.\n"
            f"Sirf bot ka database clear hua hai.\n\n"
            f"🔖 _Powered by **RAJ DEV**_"
        )
        logger.info(f"Admin {message.from_user.id} deleted all {deleted_count} files from DB.")

    except Exception as e:
        logger.error(f"delete_all error: {e}", exc_info=True)
        await confirm_msg.edit_text(
            f"❌ **Delete Failed**\n\n`{e}`\n\n"
            f"🔖 _Powered by **RAJ DEV**_"
        )
