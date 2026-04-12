"""
╔══════════════════════════════════════════════════════════════╗
║                   FILE UPLOAD HANDLER                        ║
║  Admin file bhejta hai → DB channel save → Update channel   ║
║                                                              ║
║   Credit: RAJ DEV                                           ║
╚══════════════════════════════════════════════════════════════╝
"""

import io
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


# ── Non-admin reject ───────────────────────────────────────────
@Client.on_message(non_admin_filter & filters.private & _MEDIA_FILTER, group=-1)
async def reject_unauthorized_upload(client: Client, message: Message):
    ch_url = Config.get_channel_url()
    buttons = []
    if ch_url:
        buttons.append([InlineKeyboardButton("📢 Visit Channel", url=ch_url)])
    await message.reply(
        "🚫 **Unauthorized**\n\n"
        "Sirf authorized admins hi files upload kar sakte hain.",
        reply_markup=InlineKeyboardMarkup(buttons) if buttons else None,
    )
    message.stop_propagation()


# ══════════════════════════════════════════════════════════════
#  THUMBNAIL HELPER
#  Telegram thumbnail file_id directly send_photo mein nahi
#  chalta. Download karke bytes mein bhejte hain.
# ══════════════════════════════════════════════════════════════

async def _get_thumb_bytes(client: Client, message: Message) -> bytes | None:
    """
    Video ka thumbnail bytes mein return karo.
    download_media(in_memory=True) use karta hai — BytesIO directly.
    """
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

        # in_memory=True → BytesIO object return karta hai directly
        buf = await client.download_media(thumb_file_id, in_memory=True)
        if buf:
            buf.seek(0)
            return buf.read()
    except Exception as e:
        logger.warning(f"Thumbnail download failed: {e}")
    return None


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
        # 1. DB channel mein forward
        forwarded = await message.copy(Config.DB_CHANNEL)
        short_key = info["file_id"][:32]

        # 2. Direct link
        direct_link = f"https://t.me/{Config.BOT_USERNAME}?start=file_{short_key}"

        # 3. Shortener
        shortener_on = await DB.is_shortener_on()
        api_key      = await DB.get_shortener_api()
        short_url    = None
        if shortener_on and api_key:
            short_url = await shorten_url(direct_link, api_key, Config.SHORTENER_SITE)
            if short_url == direct_link:
                short_url = None

        # 4. DB save
        await DB.save_file(
            file_id    = short_key,
            file_name  = info["file_name"],
            message_id = forwarded.id,
            file_size  = info["file_size"],
            file_type  = info["file_type"],
            direct_url = direct_link,
            short_url  = short_url,
        )

        # 5. Update Channel post
        channel_link = short_url if short_url else direct_link
        emoji        = get_file_emoji(info["file_type"])
        size_str     = humanize_size(info["file_size"])
        caption_raw  = message.caption or ""

        channel_text = (
            f"{emoji} **{info['file_name']}**\n\n"
            + (f"📝 {caption_raw}\n\n" if caption_raw else "")
            + f"📦 **Size:** `{size_str}`\n"
            + f"🏷️ **Type:** `{info['file_type'].capitalize()}`\n\n"
            + "━━━━━━━━━━━━━━━━━━━━\n"
            + f"🔗 **Download Link:**\n`{channel_link}`\n"
            + "━━━━━━━━━━━━━━━━━━━━\n\n"
            + ("🔒 _Via Link Shortener_" if short_url else "🔗 _Direct Link_")
            + "\n\n🔖 _Powered by **RAJ DEV**_"
        )

        channel_button = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"📥 Get File {emoji}", url=channel_link)]
        ])

        post_success = False
        if Config.UPDATE_CHANNEL:
            try:
                posted = False

                # ── Photo file directly bhejo ──────────────────
                if message.photo:
                    await client.send_photo(
                        chat_id      = Config.UPDATE_CHANNEL,
                        photo        = message.photo.file_id,
                        caption      = channel_text,
                        reply_markup = channel_button,
                    )
                    posted = True

                # ── Video: thumbnail bytes download karke bhejo ─
                elif info["file_type"] == "video":
                    thumb_bytes = await _get_thumb_bytes(client, message)
                    if thumb_bytes:
                        thumb_io = io.BytesIO(thumb_bytes)
                        thumb_io.name = "thumb.jpg"
                        await client.send_photo(
                            chat_id      = Config.UPDATE_CHANNEL,
                            photo        = thumb_io,
                            caption      = channel_text,
                            reply_markup = channel_button,
                        )
                        posted = True

                # ── Animation: thumbnail try karo ──────────────
                elif info["file_type"] == "animation":
                    thumb_bytes = await _get_thumb_bytes(client, message)
                    if thumb_bytes:
                        thumb_io = io.BytesIO(thumb_bytes)
                        thumb_io.name = "thumb.jpg"
                        await client.send_photo(
                            chat_id      = Config.UPDATE_CHANNEL,
                            photo        = thumb_io,
                            caption      = channel_text,
                            reply_markup = channel_button,
                        )
                        posted = True

                # ── Koi bhi aur type: plain text post ──────────
                if not posted:
                    await client.send_message(
                        chat_id      = Config.UPDATE_CHANNEL,
                        text         = channel_text,
                        reply_markup = channel_button,
                    )

                post_success = True
                logger.info(f"✅ Posted to channel: {info['file_name']}")

            except Exception as e:
                logger.error(f"Channel post failed: {e}")
                await processing_msg.edit_text(
                    f"⚠️ **File DB mein save ho gaya, lekin Update Channel post fail!**\n\n"
                    f"**Error:** `{e}`\n\n"
                    f"**Check karo:**\n"
                    f"1️⃣ Bot ko `{Config.UPDATE_CHANNEL}` channel ka **Admin** banao\n"
                    f"2️⃣ Bot ko **Post Messages** permission do\n"
                    f"3️⃣ `UPDATE_CHANNEL` env var check karo\n\n"
                    f"🔖 _Powered by **RAJ DEV**_"
                )
                return

        # 6. Admin confirm
        buttons = [[InlineKeyboardButton("🔗 Direct Link", url=direct_link)]]
        if short_url:
            buttons.insert(0, [InlineKeyboardButton("✂️ Shortened Link", url=short_url)])
        ch_url = Config.get_channel_url()
        if ch_url:
            buttons.append([InlineKeyboardButton("📢 View in Channel", url=ch_url)])

        await processing_msg.edit_text(
            f"✅ **File Upload Complete!**\n\n"
            f"{emoji} `{info['file_name']}`\n"
            f"📦 Size: **{size_str}**\n\n"
            f"🔗 **Direct Link:**\n`{direct_link}`\n\n"
            + (f"✂️ **Shortened Link:**\n`{short_url}`\n\n" if short_url else "")
            + ("✅ _Update Channel mein post ho gaya!_\n\n" if post_success else "")
            + "🔖 _Powered by **RAJ DEV**_",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        await processing_msg.edit_text(
            f"❌ **Upload Failed**\n\n`{e}`\n\n"
            f"🔖 _Powered by **RAJ DEV**_"
        )
