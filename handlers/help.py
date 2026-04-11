"""
╔══════════════════════════════════════════════════════════════╗
║                    /help COMMAND HANDLER                     ║
╚══════════════════════════════════════════════════════════════╝
"""

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import Config
from database import DB


@Client.on_message(filters.command("help") & filters.private)
async def help_handler(client: Client, message: Message):
    tutorial_id = await DB.get_tutorial_file_id()

    if tutorial_id:
        await message.reply_video(
            video=tutorial_id,
            caption=(
                "🎬 **How to Use the Bot**\n\n"
                "Watch the tutorial above!\n\n"
                "📌 **Quick Guide:**\n"
                "1️⃣ Get a file link from our channel\n"
                "2️⃣ Click the link to open the bot\n"
                "3️⃣ The bot will send the file to you\n\n"
                "👑 **Premium users** get:\n"
                "  • Direct links (no shortener)\n"
                "  • Priority delivery\n"
                "  • Exclusive access"
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👑 Get Premium", callback_data="premium_plans")],
                [InlineKeyboardButton("📢 Channel",     url=f"https://t.me/{Config.UPDATE_CHANNEL.lstrip('@')}")],
            ]),
        )
    else:
        await message.reply(
            "🆘 **Help & Guide**\n\n"
            "📌 **How to get files:**\n"
            "1️⃣ Visit our update channel\n"
            "2️⃣ Click any file link\n"
            "3️⃣ The bot sends the file directly!\n\n"
            "👑 **Premium users** bypass the shortener and get files instantly.\n\n"
            "📩 **Support:** Contact an admin for help.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👑 Premium Plans", callback_data="premium_plans")],
                [InlineKeyboardButton("📢 Update Channel", url=f"https://t.me/{Config.UPDATE_CHANNEL.lstrip('@')}")],
            ]),
        )


# Admin help panel
@Client.on_message(filters.command("help") & filters.private)
async def admin_help(client: Client, message: Message):
    if message.from_user.id not in Config.ADMINS:
        return  # Handled by public handler above

    await message.reply(
        "🔧 **Admin Commands**\n\n"
        "`/settings` — Open control panel\n"
        "`/add_premium <id> <days>` — Grant premium\n"
        "`/remove_premium <id>` — Remove premium\n"
        "`/ban <id>` — Ban a user\n"
        "`/broadcast` — Broadcast (reply to msg)\n"
        "`/add_tutorial` — Set tutorial (reply to video)\n"
        "`/set_about <text>` — Update about text\n"
        "`/set_plans <text>` — Update premium plans\n"
        "`/stats` — View bot statistics\n\n"
        "_Send any file to upload it to the store._"
    )
