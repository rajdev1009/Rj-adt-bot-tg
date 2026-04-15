"""
╔══════════════════════════════════════════════════════════════╗
║                   FILE UPLOAD HANDLER                        ║
║   Admin files upload karta hai → DB channel mein save        ║
║   Update channel mein thumbnail ke saath post hota hai       ║
║   Credit: RAJ DEV @raj_dev_01                                ║
╚══════════════════════════════════════════════════════════════╝
"""

import io
import logging
from pyrogram import Client, filters
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
)
from config import Config
from database import DB
from utils import extract_file_info, humanize_size, get_file_emoji

logger = logging.getLogger("UploadHandler")

_MEDIA_FILTER = (
    filters.document | filters.video | filters.audio |
    filters.photo | filters.animation | filters.voice | filters.video_note
)

def _is_admin(_, __, msg: Message) -> bool:
    return bool(msg.from_user and msg.from_user.id in Config.ADMINS)

def _is_not_admin(_, __, msg: Message) -> bool:
    return bool(msg.from_user and msg.from_user.id not in Config.ADMINS)

admin_filter     = filters.create(_is_admin)
non_admin_filter = filters.create(_is_not_admin)


@Client.on_message(non_admin_filter & filters.private & _MEDIA_FILTER, group=-1)
async def reject_unauthorized_upload(client: Client, message: Message):
    ch_url  = Config.get_channel_url()
    buttons = [[InlineKeyboardButton("📢 Visit Channel", url=ch_url)]] if ch_url else []
    await message.reply(
        "🚫 **Unauthorized**\n\nSirf admins hi files upload kar sakte hain.",
        reply_markup=InlineKeyboardMarkup(buttons) if buttons else None,
    )
    message.stop_propagation()


async def _get_thumb_bytes(client: Client, message: Message):
    try:
        thumb_file_id = None
        if message.video and message.video.thumbs:
            thumb_file_id = message.video.thumbs[0].file_id
        elif message.animation and message.animation.thumbs:
            thumb_file_id = message.animation.thumbs[0].file_id
        elif message.document and message.document.thumbs:
            thumb_file_id = message.document.thumbs[0].file_id
        if not thumb_file_id:
            return None
        buf = await client.download_media(thumb_file_id, in_memory=True)
        if buf:
            buf.seek(0)
            return buf.read()
    except Exception as e:
        logger.warning(f"Thumb download failed: {e}")
    return None


async def _post_to_channel(client: Client, caption: str, buttons: InlineKeyboardMarkup,
                           message: Message, info: dict):
    posted = False
    if message.photo:
        await client.send_photo(
            chat_id=Config.UPDATE_CHANNEL, photo=message.photo.file_id,
            caption=caption, reply_markup=buttons,
        )
        posted = True
    elif info["file_type"] in ("video", "animation"):
        thumb_bytes = await _get_thumb_bytes(client, message)
        if thumb_bytes:
            thumb_io      = io.BytesIO(thumb_bytes)
            thumb_io.name = "thumb.jpg"
            await client.send_photo(
                chat_id=Config.UPDATE_CHANNEL, photo=thumb_io,
                caption=caption, reply_markup=buttons,
            )
            posted = True
    if not posted:
        await client.send_message(
            chat_id=Config.UPDATE_CHANNEL, text=caption, reply_markup=buttons,
        )
    return True


@Client.on_message(admin_filter & filters.private & _MEDIA_FILTER, group=0)
async def file_upload_handler(client: Client, message: Message):
    info = extract_file_info(message)
    if not info:
        await message.reply("⚠️ Unsupported media type.")
        return

    if not Config.BOT_USERNAME:
        me = await client.get_me()
        Config.BOT_USERNAME = me.username

    processing_msg = await message.reply("⏳ **Processing your file...**")

    try:
        name_part       = info["file_name"].rsplit(".", 1)[0] if "." in info["file_name"] else info["file_name"]
        branded_caption = f"{name_part} | RAJ DEV\n\n🔖 @raj_dev_01"

        forwarded   = await message.copy(Config.DB_CHANNEL, caption=branded_caption)
        short_key   = info["file_id"][:32]
        direct_link = f"https://t.me/{Config.BOT_USERNAME}?start=file_{short_key}"

        await DB.save_file(
            file_id    = short_key,
            file_name  = info["file_name"],
            message_id = forwarded.id,
            file_size  = info["file_size"],
            file_type  = info["file_type"],
            direct_url = direct_link,
        )

        emoji       = get_file_emoji(info["file_type"])
        size_str    = humanize_size(info["file_size"])
        caption_raw = message.caption or ""

        channel_caption = (
            f"{emoji} **{info['file_name']}**\n\n"
            + (f"📝 {caption_raw}\n\n" if caption_raw else "")
            + f"📦 **Size:** `{size_str}`\n"
            + f"🏷️ **Type:** `{info['file_type'].capitalize()}`\n\n"
            + "━━━━━━━━━━━━━━━━━━━━\n"
            + "🔗 **Neeche button tap karo file lene ke liye!**\n"
            + "━━━━━━━━━━━━━━━━━━━━\n\n"
            + "🔒 _Free users: Shortlink visit karna hoga_\n"
            + "👑 _Premium users: Seedha file milegi_\n\n"
            + "🔖 _Powered by **RAJ DEV**_"
        )

        channel_buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"📥 Get File {emoji}", url=direct_link)]
        ])

        post_success = False
        if Config.UPDATE_CHANNEL:
            try:
                await _post_to_channel(client, channel_caption, channel_buttons, message, info)
                post_success = True
            except Exception as e:
                logger.error(f"Channel post failed: {e}")
                await processing_msg.edit_text(
                    f"⚠️ **File save hui, lekin channel post fail!**\n\n`{e}`\n\n"
                    f"Bot ko channel mein admin banao.\n\n🔖 _Powered by **RAJ DEV**_"
                )
                return

        ch_url  = Config.get_channel_url()
        buttons = [[InlineKeyboardButton("🔗 Direct Link", url=direct_link)]]
        if ch_url:
            buttons.append([InlineKeyboardButton("📢 View in Channel", url=ch_url)])

        await processing_msg.edit_text(
            f"✅ **File Upload Complete!**\n\n"
            f"{emoji} `{info['file_name']}`\n"
            f"📦 Size: **{size_str}**\n\n"
            f"🔗 **Direct Link:**\n`{direct_link}`\n\n"
            + ("✅ _Channel mein post ho gaya!_\n\n" if post_success else "")
            + "🔖 _Powered by **RAJ DEV**_",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        await processing_msg.edit_text(f"❌ **Upload Failed**\n\n`{e}`\n\n🔖 _Powered by **RAJ DEV**_")
