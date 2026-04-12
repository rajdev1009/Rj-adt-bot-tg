"""
╔══════════════════════════════════════════════════════════════╗
║                  ADMIN SETTINGS PANEL                        ║
║   /settings → Inline button control panel for admins        ║
║                                                              ║
║  SECURITY (§8 — Exclusive Admin Control):                    ║
║  • /settings is blocked at the Pyrogram filter level for     ║
║    non-admins — they never even reach the handler body.      ║
║  • Every callback tied to this panel carries BOTH a          ║
║    regex filter AND the admin_filter, so spoofing a          ║
║    callback_data from a non-admin account is rejected        ║
║    before any DB call is made.                               ║
║  • @admin_callback provides a final defence-in-depth layer   ║
║    that shows an alert and returns without action.           ║
╚══════════════════════════════════════════════════════════════╝
"""

import logging
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ForceReply,
)
from config import Config
from database import DB
from utils.decorators import admin_only, admin_callback

logger = logging.getLogger("SettingsHandler")

# ── Admin-only Pyrogram filter (applied at registration time) ─
def _is_admin(_, __, update) -> bool:
    user = getattr(update, "from_user", None)
    return bool(user and user.id in Config.ADMINS)

_admin_filter = filters.create(_is_admin)


# ══════════════════════════════════════════════════════════════
#  SETTINGS KEYBOARD BUILDER
# ══════════════════════════════════════════════════════════════

async def build_settings_keyboard() -> InlineKeyboardMarkup:
    shortener_on  = await DB.is_shortener_on()
    premium_mode  = await DB.is_premium_mode()
    api_key       = await DB.get_shortener_api()

    short_label   = "🟢 Shortener: ON"      if shortener_on  else "🔴 Shortener: OFF"
    premium_label = "🟢 Premium Mode: ON"   if premium_mode  else "🔴 Premium Mode: OFF"
    api_preview   = f"…{api_key[-6:]}"      if len(api_key) > 6 else (api_key or "Not set")

    return InlineKeyboardMarkup([
        [InlineKeyboardButton(short_label,                          callback_data="adm_toggle_shortener")],
        [InlineKeyboardButton(f"🔑 Shortener API: {api_preview}",  callback_data="adm_change_api")],
        [InlineKeyboardButton(premium_label,                        callback_data="adm_toggle_premium_mode")],
        [InlineKeyboardButton("📝 Edit About Text",                 callback_data="adm_edit_about")],
        [InlineKeyboardButton("💎 Edit Premium Plans",              callback_data="adm_edit_plans")],
        [InlineKeyboardButton("📊 Bot Statistics",                  callback_data="adm_bot_stats")],
        [InlineKeyboardButton("❌ Close",                           callback_data="adm_close_settings")],
    ])


async def settings_text() -> str:
    shortener_on = await DB.is_shortener_on()
    premium_mode = await DB.is_premium_mode()
    user_count   = await DB.get_user_count()
    return (
        "⚙️ **Admin Control Panel**\n\n"
        f"👥 Total Users: `{user_count}`\n"
        f"🔗 Shortener: {'`ON ✅`' if shortener_on else '`OFF ❌`'}\n"
        f"👑 Premium Mode: {'`ON ✅`' if premium_mode else '`OFF ❌`'}\n\n"
        "Use the buttons below to manage bot settings:"
    )


# ══════════════════════════════════════════════════════════════
#  /settings COMMAND
#  Double-locked: Pyrogram filter + @admin_only decorator
# ══════════════════════════════════════════════════════════════

@Client.on_message(filters.command("settings") & filters.private & _admin_filter)
@admin_only
async def settings_command(client: Client, message: Message):
    await message.reply(
        await settings_text(),
        reply_markup=await build_settings_keyboard(),
    )


# ══════════════════════════════════════════════════════════════
#  TOGGLE CALLBACKS
#  All prefixed with "adm_" — non-admin accounts won't have
#  these buttons rendered, and even if spoofed they are
#  blocked by _admin_filter + @admin_callback.
# ══════════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex("^adm_toggle_shortener$") & _admin_filter)
@admin_callback
async def cb_toggle_shortener(client: Client, cq: CallbackQuery):
    new_state = await DB.toggle_shortener()
    status    = "ON ✅" if new_state else "OFF ❌"
    await cq.answer(f"Shortener is now {status}", show_alert=True)
    await cq.message.edit_text(
        await settings_text(),
        reply_markup=await build_settings_keyboard(),
    )


@Client.on_callback_query(filters.regex("^adm_toggle_premium_mode$") & _admin_filter)
@admin_callback
async def cb_toggle_premium(client: Client, cq: CallbackQuery):
    new_state = await DB.toggle_premium_mode()
    status    = "ON ✅" if new_state else "OFF ❌"
    await cq.answer(f"Premium Mode is now {status}", show_alert=True)
    await cq.message.edit_text(
        await settings_text(),
        reply_markup=await build_settings_keyboard(),
    )


@Client.on_callback_query(filters.regex("^adm_change_api$") & _admin_filter)
@admin_callback
async def cb_change_api(client: Client, cq: CallbackQuery):
    await cq.message.reply(
        "🔑 **Change Shortener API Key**\n\n"
        "Reply to this message with the new API key.\n\n"
        "_Example:_ `abc123xyz`",
        reply_markup=ForceReply(selective=True),
    )
    await cq.answer()


@Client.on_callback_query(filters.regex("^adm_edit_about$") & _admin_filter)
@admin_callback
async def cb_edit_about(client: Client, cq: CallbackQuery):
    current = await DB.get_about_text()
    await cq.message.reply(
        "📝 **Edit About Text**\n\n"
        "Reply to this message with the new about text.\n"
        "Markdown is supported.\n\n"
        f"**Current (preview):**\n{current[:300]}{'...' if len(current) > 300 else ''}",
        reply_markup=ForceReply(selective=True),
    )
    await cq.answer()


@Client.on_callback_query(filters.regex("^adm_edit_plans$") & _admin_filter)
@admin_callback
async def cb_edit_plans(client: Client, cq: CallbackQuery):
    current = await DB.get_premium_text()
    await cq.message.reply(
        "💎 **Edit Premium Plans Text**\n\n"
        "Reply to this message with the new plans text.\n"
        "Markdown is supported.\n\n"
        f"**Current (preview):**\n{current[:300]}{'...' if len(current) > 300 else ''}",
        reply_markup=ForceReply(selective=True),
    )
    await cq.answer()


@Client.on_callback_query(filters.regex("^adm_bot_stats$") & _admin_filter)
@admin_callback
async def cb_bot_stats(client: Client, cq: CallbackQuery):
    user_count   = await DB.get_user_count()
    shortener_on = await DB.is_shortener_on()
    premium_mode = await DB.is_premium_mode()
    await cq.answer()
    await cq.message.edit_text(
        f"📊 **Bot Statistics**\n\n"
        f"👥 Total Users: `{user_count}`\n"
        f"🔗 Shortener: `{'ON' if shortener_on else 'OFF'}`\n"
        f"👑 Premium Mode: `{'ON' if premium_mode else 'OFF'}`\n",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Settings", callback_data="adm_back_settings")]
        ]),
    )


@Client.on_callback_query(filters.regex("^adm_back_settings$") & _admin_filter)
@admin_callback
async def cb_back_settings(client: Client, cq: CallbackQuery):
    await cq.message.edit_text(
        await settings_text(),
        reply_markup=await build_settings_keyboard(),
    )
    await cq.answer()


@Client.on_callback_query(filters.regex("^adm_close_settings$") & _admin_filter)
@admin_callback
async def cb_close_settings(client: Client, cq: CallbackQuery):
    await cq.message.delete()
    await cq.answer("Settings closed.")


@Client.on_callback_query(filters.regex("^adm_open_settings$") & _admin_filter)
@admin_callback
async def cb_open_settings(client: Client, cq: CallbackQuery):
    """Help panel ke 'Open Settings' button se open hoga"""
    await cq.message.reply(
        await settings_text(),
        reply_markup=await build_settings_keyboard(),
    )
    await cq.answer()


# ══════════════════════════════════════════════════════════════
#  REPLY HANDLERS  (admin ForceReply responses)
#  Filtered to: admin users replying to the bot's own ForceReply
# ══════════════════════════════════════════════════════════════

@Client.on_message(_admin_filter & filters.private & filters.text & filters.reply)
async def admin_reply_handler(client: Client, message: Message):
    """
    Intercept admin replies to ForceReply prompts and persist changes.
    Non-admins never reach this handler due to _admin_filter.
    """
    replied = message.reply_to_message
    if not replied or not replied.text:
        return

    prompt_text = replied.text
    new_val     = message.text.strip()

    if "Change Shortener API Key" in prompt_text:
        await DB.set_shortener_api(new_val)
        await message.reply(
            "✅ **Shortener API key updated!**\n\n"
            f"New key: `…{new_val[-6:] if len(new_val) > 6 else new_val}`"
        )

    elif "Edit About Text" in prompt_text:
        await DB.set_about_text(new_val)
        await message.reply("✅ **About text updated!**")

    elif "Edit Premium Plans Text" in prompt_text:
        await DB.set_premium_text(new_val)
        await message.reply("✅ **Premium plans text updated!**")
