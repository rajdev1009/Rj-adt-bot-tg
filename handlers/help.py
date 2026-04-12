"""
╔══════════════════════════════════════════════════════════════╗
║                    /help COMMAND HANDLER                     ║
║   Admin: Saare commands ki full list                         ║
║   User:  Tutorial video + guide                              ║
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
#  ADMIN /help — Poori command list
# ══════════════════════════════════════════════════════════════

@Client.on_message(filters.command("help") & admin_filter & filters.private, group=0)
async def admin_help_handler(client: Client, message: Message):
    shortener_on = await DB.is_shortener_on()
    premium_mode = await DB.is_premium_mode()
    tutorial_set = bool(await DB.get_tutorial_file_id())
    ch_url       = Config.get_channel_url()

    admin_text = (
        "🔧 **ADMIN CONTROL PANEL — Full Guide**\n"
        "🔖 _Powered by **RAJ DEV**_\n\n"

        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📁 **FILE UPLOAD**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "• Bot mein koi bhi file bhejo\n"
        "• Supported: Video, Audio, Document,\n"
        "  Photo, Animation, Voice, Video Note\n"
        "• File auto DB channel mein save hogi\n"
        "• Update channel mein post hoga\n"
        "  (File name, size, download link)\n\n"

        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚙️ **SETTINGS** — `/settings`\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 Shortener: **{'🟢 ON' if shortener_on else '🔴 OFF'}**\n"
        f"👑 Premium Mode: **{'🟢 ON' if premium_mode else '🔴 OFF'}**\n"
        "• `/settings` → Inline toggle panel\n"
        "  ├ Shortener ON/OFF toggle\n"
        "  ├ Shortener API key change\n"
        "  ├ Premium Mode ON/OFF toggle\n"
        "  ├ About text edit\n"
        "  ├ Premium plans text edit\n"
        "  └ Bot statistics\n\n"

        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔗 **SHORTENER LOGIC**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "• Shortener ON → Regular users ko short link\n"
        "• Shortener OFF → Sab ko direct link\n"
        "• Premium user → Hamesha direct link\n"
        "  (Chahe shortener ON ho ya OFF)\n\n"

        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "👑 **PREMIUM MANAGEMENT**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "`/add_premium <user_id> <days>`\n"
        "  Example: `/add_premium 123456789 30`\n"
        "`/remove_premium <user_id>`\n"
        "  Example: `/remove_premium 123456789`\n\n"

        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🚫 **BAN MANAGEMENT**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "`/ban <user_id>` — User ban karo\n\n"

        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📡 **BROADCAST**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "1. Koi message type karo ya forward karo\n"
        "2. Us message ko reply karo `/broadcast` se\n"
        "3. Sab users ko wo message milega\n\n"

        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎬 **TUTORIAL** — {'✅ Set' if tutorial_set else '❌ Not Set'}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Tutorial video add karne ka tarika:\n"
        "1️⃣ Bot mein tutorial video bhejo\n"
        "2️⃣ Us video ko reply karo `/add_tutorial` se\n"
        "3️⃣ Users ko `/help` pe dikhega\n\n"

        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📝 **DYNAMIC CONTENT**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "`/set_about <text>` — About text change\n"
        "  (Markdown supported)\n"
        "`/set_plans <text>` — Premium plans change\n"
        "  (Markdown supported)\n\n"

        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📊 **STATISTICS** — `/stats`\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "• Total users count\n"
        "• Shortener status\n"
        "• Premium mode status\n"
        "• Server time\n\n"

        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔒 **SECURITY FEATURES**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "• Force Subscribe: Users channel join karne\n"
        "  ke baad hi files milti hain\n"
        "• Anti-Spam: Har request ke beech delay\n"
        "• Non-admin file upload blocked\n"
        "• Admin-only settings panel\n\n"

        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "✨ **RAJ DEV PROMO**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Jab bhi koi file link use karta hai,\n"
        "**✨ RAJ DEV ✨** 1.5 sec flash hokar\n"
        "gayab ho jaata hai automatically.\n"
    )

    buttons = [[InlineKeyboardButton("⚙️ Open Settings Panel", callback_data="adm_open_settings")]]
    if ch_url:
        buttons.append([InlineKeyboardButton("📢 Update Channel", url=ch_url)])

    await message.reply(admin_text, reply_markup=InlineKeyboardMarkup(buttons))


# ══════════════════════════════════════════════════════════════
#  USER /help — Tutorial + Guide
# ══════════════════════════════════════════════════════════════

@Client.on_message(filters.command("help") & filters.private, group=1)
async def user_help_handler(client: Client, message: Message):
    if message.from_user.id in Config.ADMINS:
        return

    tutorial_id = await DB.get_tutorial_file_id()
    ch_url      = Config.get_channel_url()

    buttons = [[InlineKeyboardButton("👑 Get Premium", callback_data="premium_plans")]]
    if ch_url:
        buttons.append([InlineKeyboardButton("📢 Update Channel", url=ch_url)])

    if tutorial_id:
        await message.reply_video(
            video=tutorial_id,
            caption=(
                "🎬 **How to Use This Bot**\n\n"
                "📌 **Quick Steps:**\n"
                "1️⃣ Update Channel pe jao\n"
                "2️⃣ Kisi file ke link pe click karo\n"
                "3️⃣ Bot file turant bhej dega!\n\n"
                "👑 **Premium** ke fayde:\n"
                "  • Shortener bypass (direct link)\n"
                "  • Priority delivery\n"
                "  • Exclusive content\n\n"
                "🔖 _Powered by **RAJ DEV**_"
            ),
            reply_markup=InlineKeyboardMarkup(buttons),
        )
    else:
        await message.reply(
            "🆘 **Help & Guide**\n\n"
            "📌 **Files kaise download karein:**\n"
            "1️⃣ Hamare Update Channel pe jao\n"
            "2️⃣ Kisi bhi file ke link pe click karo\n"
            "3️⃣ Bot turant file bhej dega!\n\n"
            "👑 **Premium** lene pe shortener bypass\n"
            "hoga aur files seedha milegi.\n\n"
            "📩 Support ke liye admin se contact karein.\n\n"
            "🔖 _Powered by **RAJ DEV**_",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
