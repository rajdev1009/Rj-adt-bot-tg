"""
╔══════════════════════════════════════════════════════════════╗
║                   FILE UPLOAD HANDLER                        ║
║  Admin sends file → save to DB channel → post to update ch   ║
║                                                              ║
║  SECURITY RULES (§8):                                        ║
║  • Only ADMINS listed in Config.ADMINS may upload files.     ║
║  • Any non-admin who sends a file gets an explicit           ║
║    "Unauthorized" rejection — no silent ignore.              ║
║  • Shortener logic at upload time stores BOTH the direct     ║
║    bot_link AND the short_url so the delivery handler can    ║
║    pick the right one per-user at request time.              ║
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

# ── Reusable filter helpers ────────────────────────────────────
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


# ══════════════════════════════════════════════════════════════
#  BLOCK NON-ADMINS WHO SEND FILES
#  This handler fires FIRST for any non-admin file send,
#  gives an explicit rejection, and stops propagation.
# ══════════════════════════════════════════════════════════════

@Client.on_message(
    non_admin_filter & filters.private & _MEDIA_FILTER,
    group=-1,   # Higher priority group runs before the upload handler
)
async def reject_unauthorized_upload(client: Client, message: Message):
    """
    Explicitly reject file uploads from non-admin users.
    Silent ignore is NOT used — an Unauthorized message is sent.
    """
    await message.reply(
        "🚫 **Unauthorized**\n\n"
        "Only authorized admins can upload files to this bot.\n"
        "If you're looking for a file, use a share link from our channel.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "📢 Visit Channel",
                url=f"https://t.me/{Config.UPDATE_CHANNEL.lstrip('@')}"
            )]
        ]),
    )
    # Stop the message from reaching any further handlers
    message.stop_propagation()


# ══════════════════════════════════════════════════════════════
#  ADMIN FILE UPLOAD
# ══════════════════════════════════════════════════════════════

@Client.on_message(
    admin_filter & filters.private & _MEDIA_FILTER,
    group=0,
)
async def file_upload_handler(client: Client, message: Message):
    """
    Admin-only upload flow:
      1. Forward file to private DB channel.
      2. Build the direct deep-link (always stored).
      3. If Shortener is ON, also generate + store the short URL.
         The channel post uses the shortened link for regular users.
         The admin confirmation shows both links.
      4. Save ALL metadata (including both URLs) to DB so the
         delivery handler can apply per-user link logic at request time.
      5. Post announcement to Update Channel.
    """
    info = extract_file_info(message)
    if not info:
        await message.reply("⚠️ Unsupported media type.")
        return

    processing_msg = await message.reply("⏳ **Processing your file...**")

    try:
        # ── 1. Forward to private DB channel ──────────────────
        forwarded = await message.copy(Config.DB_CHANNEL)

        short_key = info["file_id"][:32]   # URL-safe DB key

        # ── 2. Build the permanent direct deep-link ───────────
        direct_link = f"https://t.me/{Config.BOT_USERNAME}?start=file_{short_key}"

        # ── 3. Conditionally generate shortened URL ────────────
        shortener_on = await DB.is_shortener_on()
        api_key      = await DB.get_shortener_api()
        short_url    = None

        if shortener_on and api_key:
            short_url = await shorten_url(direct_link, api_key, Config.SHORTENER_SITE)
            # If shortener returned the original URL (e.g. API error), treat as no shortener
            if short_url == direct_link:
                short_url = None

        # ── 4. Save to DB — store BOTH links ──────────────────
        #    The delivery handler decides which to show per user:
        #      • Premium user   → always direct_link
        #      • Regular user   → short_url if shortener ON, else direct_link
        await DB.save_file(
            file_id    = short_key,
            file_name  = info["file_name"],
            message_id = forwarded.id,
            file_size  = info["file_size"],
            file_type  = info["file_type"],
            direct_url = direct_link,          # always stored
            short_url  = short_url,            # None when shortener is OFF
        )

        # ── 5. Post to Update Channel ──────────────────────────
        #    Channel post always uses shortened link when available
        #    (regular users click from channel; premium users bypass it client-side)
        channel_link = short_url if short_url else direct_link
        emoji        = get_file_emoji(info["file_type"])
        size_str     = humanize_size(info["file_size"])
        caption      = message.caption or ""

        channel_text = (
            f"{emoji} **{info['file_name']}**\n\n"
            f"{'📝 ' + caption + chr(10) + chr(10) if caption else ''}"
            f"📦 **Size:** `{size_str}`\n"
            f"🏷️ **Type:** `{info['file_type'].capitalize()}`\n\n"
            f"🔗 **Download Link:**\n{channel_link}\n\n"
            f"{'🔒 Via Link Shortener' if short_url else '🔗 Direct Link'}"
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
            except Exception as e:
                logger.warning(f"Failed to post to update channel: {e}")

        # ── 6. Confirm to admin (show both links) ──────────────
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
            + f"_Premium users always receive the direct link._",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        await processing_msg.edit_text(f"❌ **Upload Failed**\n\n`{e}`")
