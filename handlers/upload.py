"""
╔══════════════════════════════════════════════════════════════╗
║                   FILE UPLOAD HANDLER                        ║
║  Admin file bhejta hai → DB channel mein save →             ║
║  Update channel mein post                                    ║
║                                                              ║
║  Credit: RAJ DEV                                            ║
╚══════════════════════════════════════════════════════════════╝
"""

import logging
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from config import Config
from database import DB
from utils import (
    extract_file_info,
    shorten_url,
    humanize_size,
    get_file_emoji,
)

logger = logging.getLogger("UploadHandler")

_MEDIA_FILTER = (
    filters.document
    | filters.video
    | filters.audio
    | filters.photo
    | filters.animation
    | filters.voice
    | filters.video_note
)

def _is_admin(_, __, msg: Message) -> bool:
    return bool(msg.from_user and msg.from_user.id in Config.ADMINS)

def _is_not_admin(_, __, msg: Message) -> bool:
    return bool(msg.from_user and msg.from_user.id not in Config.ADMINS)

admin_filter     = filters.create(_is_admin)
non_admin_filter = filters.create(_is_not_admin)


# ── Non-admin file bheje to reject ────────────────────────────
@Client.on_message(non_admin_filter & filters.private & _MEDIA_FILTER, group=-1)
async def reject_unauthorized_upload(client: Client, message: Message):
    await message.reply(
        "🚫 **Unauthorized**\n\n"
        "Sirf authorized admins hi files upload kar sakte hain.\n"
        "File download ke liye channel ka link use karein.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "📢 Visit Channel",
                url=f"https://t.me/{Config.UPDATE_CHANNEL.lstrip('@')}"
            )]
        ]),
    )
    message.stop_propagation()


# ══════════════════════════════════════════════════════════════
#  ADMIN FILE UPLOAD
# ══════════════════════════════════════════════════════════════

@Client.on_message(admin_filter & filters.private & _MEDIA_FILTER, group=0)
async def file_upload_handler(client: Client, message: Message):
    info = extract_file_info(message)
    if not info:
        await message.reply("⚠️ Unsupported media type.")
        return

    processing_msg = await message.reply("⏳ **Processing your file...**")

    try:
        # 1. DB channel mein forward karo
        forwarded = await message.copy(Config.DB_CHANNEL)
        short_key = info["file_id"][:32]

        # 2. Direct deep-link banao
        direct_link = f"https://t.me/{Config.BOT_USERNAME}?start=file_{short_key}"

        # 3. Shortener check
        shortener_on = await DB.is_shortener_on()
        api_key      = await DB.get_shortener_api()
        short_url    = None

        if shortener_on and api_key:
            short_url = await shorten_url(direct_link, api_key, Config.SHORTENER_SITE)
            if short_url == direct_link:
                short_url = None

        # 4. DB mein save karo (dono links)
        await DB.save_file(
            file_id    = short_key,
            file_name  = info["file_name"],
            message_id = forwarded.id,
            file_size  = info["file_size"],
            file_type  = info["file_type"],
            direct_url = direct_link,
            short_url  = short_url,
        )

        # 5. Update Channel mein post karo
        channel_link = short_url if short_url else direct_link
        emoji        = get_file_emoji(info["file_type"])
        size_str     = humanize_size(info["file_size"])
        caption      = message.caption or ""

        channel_text = (
            f"{emoji} **{info['file_name']}**\n\n"
            + (f"📝 {caption}\n\n" if caption else "")
            + f"📦 **Size:** `{size_str}`\n"
            f"🏷️ **Type:** `{info['file_type'].capitalize()}`\n\n"
            f"🔗 **Download Link:**\n{channel_link}\n\n"
            + ("🔒 _Via Link Shortener_" if short_url else "🔗 _Direct Link_")
            + "\n\n🔖 _Powered by **RAJ DEV**_"
        )

        if Config.UPDATE_CHANNEL:
            try:
                await client.send_message(
                    Config.UPDATE_CHANNEL,
                    channel_text,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(f"📥 Get File {emoji}", url=channel_link)]
                    ]),
                )
                logger.info(f"Posted to update channel: {info['file_name']}")
            except Exception as e:
                logger.warning(f"Update channel post failed: {e}")
                await processing_msg.edit_text(
                    f"⚠️ **File saved but channel post failed!**\n\n"
                    f"Error: `{e}`\n\n"
                    f"Check karo ki bot **{Config.UPDATE_CHANNEL}** channel ka admin hai."
                )
                return

        # 6. Admin ko confirm karo
        buttons = [[InlineKeyboardButton("🔗 Direct Link", url=direct_link)]]
        if short_url:
            buttons.insert(0, [InlineKeyboardButton("✂️ Shortened Link", url=short_url)])
        if Config.UPDATE_CHANNEL:
            buttons.append([
                InlineKeyboardButton(
                    "📢 View in Channel",
                    url=f"https://t.me/{Config.UPDATE_CHANNEL.lstrip('@')}"
                )
            ])

        await processing_msg.edit_text(
            f"✅ **File Uploaded Successfully!**\n\n"
            f"{emoji} `{info['file_name']}`\n"
            f"📦 Size: **{size_str}**\n\n"
            f"🔗 **Direct Link:**\n`{direct_link}`\n\n"
            + (f"✂️ **Shortened Link:**\n`{short_url}`\n\n" if short_url else "")
            + "✅ _Update Channel mein post ho gaya!_\n\n"
            + "🔖 _Powered by **RAJ DEV**_",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        await processing_msg.edit_text(f"❌ **Upload Failed**\n\n`{e}`")
