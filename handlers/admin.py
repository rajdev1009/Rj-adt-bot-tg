"""
╔══════════════════════════════════════════════════════════════╗
║                   ADMIN COMMAND HANDLERS                     ║
║   /add_premium  /broadcast  /add_tutorial  /ban  /stats     ║
╚══════════════════════════════════════════════════════════════╝
"""

import asyncio
import logging
from datetime import datetime, timezone
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated

from config import Config
from database import DB
from utils.decorators import admin_only

logger = logging.getLogger("AdminCommands")


def _is_admin(_, __, message: Message) -> bool:
    return message.from_user and message.from_user.id in Config.ADMINS

admin_filter = filters.create(_is_admin)


# ══════════════════════════════════════════════════════════════
#  /add_premium [user_id] [days]
# ══════════════════════════════════════════════════════════════

@Client.on_message(filters.command("add_premium") & admin_filter & filters.private)
@admin_only
async def add_premium_cmd(client: Client, message: Message):
    """
    Usage: /add_premium 123456789 30
    Grants premium access to user for N days.
    """
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
        await message.reply("❌ Invalid user ID or days. Both must be integers.")
        return

    await DB.add_premium(target_id, days, added_by=message.from_user.id)
    expiry = await DB.get_premium_expiry(target_id)
    expiry_str = expiry.strftime("%Y-%m-%d %H:%M UTC") if expiry else "Unknown"

    await message.reply(
        f"✅ **Premium Granted!**\n\n"
        f"👤 User ID: `{target_id}`\n"
        f"⏳ Duration: **{days} days**\n"
        f"📅 Expires: `{expiry_str}`"
    )

    # Notify the user
    try:
        await client.send_message(
            target_id,
            f"🎉 **Congratulations!**\n\n"
            f"You have been granted **Premium** access!\n"
            f"📅 Your subscription expires on:\n`{expiry_str}`\n\n"
            f"Enjoy all premium perks! 👑"
        )
    except Exception:
        pass  # User may have blocked bot


# ══════════════════════════════════════════════════════════════
#  /remove_premium [user_id]
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
#  /ban [user_id]
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
    await message.reply(f"🚫 User `{target_id}` has been **banned**.")


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
        f"🔗 Shortener: `{'ON' if shortener_on else 'OFF'}`\n"
        f"👑 Premium Mode: `{'ON' if premium_mode else 'OFF'}`\n\n"
        f"🕒 Server Time: `{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}`"
    )


# ══════════════════════════════════════════════════════════════
#  /broadcast  (reply to a message to broadcast it)
# ══════════════════════════════════════════════════════════════

@Client.on_message(filters.command("broadcast") & admin_filter & filters.private)
@admin_only
async def broadcast_cmd(client: Client, message: Message):
    """
    Reply to any message with /broadcast to send it to all users.
    """
    if not message.reply_to_message:
        await message.reply(
            "❌ **Usage:** Reply to a message with `/broadcast`\n\n"
            "_The replied message will be sent to all users._"
        )
        return

    broadcast_msg = message.reply_to_message
    user_ids      = await DB.get_all_user_ids()
    total         = len(user_ids)

    if total == 0:
        await message.reply("ℹ️ No users in database.")
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

        # Update status every 50 users
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

        await asyncio.sleep(0.05)  # Avoid hitting rate limits

    await status_msg.edit_text(
        f"✅ **Broadcast Complete!**\n\n"
        f"👥 Total users: `{total}`\n"
        f"✅ Delivered: `{success}`\n"
        f"❌ Failed: `{failed}`"
    )


# ══════════════════════════════════════════════════════════════
#  /add_tutorial  (reply to a video)
# ══════════════════════════════════════════════════════════════

@Client.on_message(filters.command("add_tutorial") & admin_filter & filters.private)
@admin_only
async def add_tutorial_cmd(client: Client, message: Message):
    """
    Reply to a video with /add_tutorial to set it as the help tutorial.
    """
    replied = message.reply_to_message
    if not replied or not replied.video:
        await message.reply(
            "❌ **Usage:** Reply to a **video** with `/add_tutorial`\n\n"
            "_The video will be shown when users tap Help._"
        )
        return

    file_id = replied.video.file_id
    await DB.set_tutorial_file_id(file_id)
    await message.reply(
        "✅ **Tutorial video updated!**\n\n"
        "Users will see this video when they tap **Help**."
    )


# ══════════════════════════════════════════════════════════════
#  /set_about  (admin sets about text inline)
# ══════════════════════════════════════════════════════════════

@Client.on_message(filters.command("set_about") & admin_filter & filters.private)
@admin_only
async def set_about_cmd(client: Client, message: Message):
    """Usage: /set_about <new about text>"""
    text = " ".join(message.command[1:]).strip()
    if not text:
        await message.reply(
            "❌ **Usage:** `/set_about <your new about text>`\n\n"
            "Markdown supported."
        )
        return
    await DB.set_about_text(text)
    await message.reply("✅ **About text updated!**")


# ══════════════════════════════════════════════════════════════
#  /set_plans  (admin sets premium plans text)
# ══════════════════════════════════════════════════════════════

@Client.on_message(filters.command("set_plans") & admin_filter & filters.private)
@admin_only
async def set_plans_cmd(client: Client, message: Message):
    """Usage: /set_plans <new plans text>"""
    text = " ".join(message.command[1:]).strip()
    if not text:
        await message.reply(
            "❌ **Usage:** `/set_plans <your new plans text>`\n\n"
            "Markdown supported."
        )
        return
    await DB.set_premium_text(text)
    await message.reply("✅ **Premium plans text updated!**")
