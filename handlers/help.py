"""
╔══════════════════════════════════════════════════════════════╗
║                    /help COMMAND HANDLER                     ║
║   Users ke liye: tutorial + guide                            ║
║   Admin ke liye: saare commands ki list                      ║
║                                                              ║
║   Credit: RAJ DEV                                            ║
╚══════════════════════════════════════════════════════════════╝
"""

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import Config
from database import DB


def _is_admin(_, __, msg: Message) -> bool:
    return bool(msg.from_user and msg.from_user.id in Config.ADMINS)

admin_filter = filters.create(_is_admin)


# ══════════════════════════════════════════════════════════════
#  ADMIN /help — Saare commands
# ══════════════════════════════════════════════════════════════

@Client.on_message(filters.command("help") & admin_filter & filters.private, group=0)
async def admin_help_handler(client: Client, message: Message):
    """Admin ko poori command list dikhao"""
    shortener_on = await DB.is_shortener_on()
    premium_mode = await DB.is_premium_mode()

    await message.reply(
        "🔧 **Admin Command Panel**\n\n"

        "━━━━ 📁 FILE MANAGEMENT ━━━━\n"
        "• Bot mein koi bhi file bhejo → Auto upload\n"
        "• File DB channel mein save hogi\n"
        "• Update channel mein post hoga\n\n"

        "━━━━ ⚙️ SETTINGS ━━━━\n"
        "`/settings` — Inline control panel\n\n"

        "━━━━ 🔗 SHORTENER ━━━━\n"
        f"• Status: **{'🟢 ON' if shortener_on else '🔴 OFF'}**\n"
        "`/settings` se toggle karein\n\n"

        "━━━━ 👑 PREMIUM MODE ━━━━\n"
        f"• Status: **{'🟢 ON' if premium_mode else '🔴 OFF'}**\n"
        "`/settings` se toggle karein\n\n"

        "━━━━ 👤 USER MANAGEMENT ━━━━\n"
        "`/add_premium <user_id> <days>` — Premium do\n"
        "`/remove_premium <user_id>` — Premium hato\n"
        "`/ban <user_id>` — User ban karo\n"
        "`/stats` — Bot statistics\n\n"

        "━━━━ 📡 BROADCAST ━━━━\n"
        "`/broadcast` — Kisi message ko reply karke\n"
        "Sab users ko message bhejega\n\n"

        "━━━━ 🎬 TUTORIAL ━━━━\n"
        "`/add_tutorial` — Kisi video ko reply karke\n"
        "Tutorial video set hoga\n\n"

        "━━━━ 📝 CONTENT ━━━━\n"
        "`/set_about <text>` — About text change\n"
        "`/set_plans <text>` — Premium plans text change\n\n"

        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔖 _Powered by **RAJ DEV**_",

        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⚙️ Open Settings Panel", callback_data="adm_open_settings")],
            [InlineKeyboardButton(
                "📢 Update Channel",
                url=f"https://t.me/{Config.UPDATE_CHANNEL.lstrip('@')}"
            )],
        ]),
    )


# ══════════════════════════════════════════════════════════════
#  USER /help — Tutorial + Guide
# ══════════════════════════════════════════════════════════════

@Client.on_message(filters.command("help") & filters.private, group=1)
async def user_help_handler(client: Client, message: Message):
    """Regular users ko help dikhao"""
    if message.from_user.id in Config.ADMINS:
        return  # Admin wala handler upar handle kar chuka hai

    tutorial_id = await DB.get_tutorial_file_id()

    if tutorial_id:
        await message.reply_video(
            video=tutorial_id,
            caption=(
                "🎬 **How to Use This Bot**\n\n"
                "📌 **Quick Steps:**\n"
                "1️⃣ Hamare channel pe jao\n"
                "2️⃣ Kisi file ke link pe click karo\n"
                "3️⃣ Bot file turant bhej dega!\n\n"
                "👑 **Premium** lene ke fayde:\n"
                "  • Shortener bypass (direct link)\n"
                "  • Priority delivery\n"
                "  • Exclusive content\n\n"
                "🔖 _Powered by **RAJ DEV**_"
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👑 Get Premium", callback_data="premium_plans")],
                [InlineKeyboardButton(
                    "📢 Update Channel",
                    url=f"https://t.me/{Config.UPDATE_CHANNEL.lstrip('@')}"
                )],
            ]),
        )
    else:
        await message.reply(
            "🆘 **Help & Guide**\n\n"
            "📌 **Files kaise download karein:**\n"
            "1️⃣ Hamare Update Channel pe jao\n"
            "2️⃣ Kisi bhi file ke link pe click karo\n"
            "3️⃣ Bot turant file bhej dega!\n\n"
            "👑 **Premium** lene pe shortener bypass hoga\n"
            "aur files seedha milegi bina kisi redirect ke.\n\n"
            "📩 Support ke liye admin se contact karein.\n\n"
            "🔖 _Powered by **RAJ DEV**_",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👑 Premium Plans", callback_data="premium_plans")],
                [InlineKeyboardButton(
                    "📢 Update Channel",
                    url=f"https://t.me/{Config.UPDATE_CHANNEL.lstrip('@')}"
                )],
            ]),
        )
