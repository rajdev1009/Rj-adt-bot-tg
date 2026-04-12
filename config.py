"""
╔══════════════════════════════════════════════════════════════╗
║                    CONFIGURATION MODULE                      ║
║       All sensitive values loaded from environment vars      ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
from typing import List


class Config:
    # ── Telegram API Credentials ───────────────────────────────
    API_ID: int = int(os.environ.get("API_ID", 0))
    API_HASH: str = os.environ.get("API_HASH", "")
    BOT_TOKEN: str = os.environ.get("BOT_TOKEN", "")

    # ── Channels ───────────────────────────────────────────────
    # DB_CHANNEL: Private channel where files are stored (forward source)
    DB_CHANNEL: int = int(os.environ.get("DB_CHANNEL", 0))
    # UPDATE_CHANNEL: Public channel where file posts are announced
    UPDATE_CHANNEL: str = os.environ.get("UPDATE_CHANNEL", "@raj_update_channel")  # e.g. "@MyChannel"

    # ── Admins ─────────────────────────────────────────────────
    # Comma-separated Telegram user IDs, e.g. "123456789,987654321"
    ADMINS: List[int] = [
        int(x.strip())
        for x in os.environ.get("ADMINS", "").split(",")
        if x.strip().isdigit()
    ]

    # ── Database URLs ──────────────────────────────────────────
    MONGO_URL: str = os.environ.get("MONGO_URL", "")
    NEON_URL: str = os.environ.get("NEON_URL", "")   # Optional PostgreSQL

    # ── Link Shortener ─────────────────────────────────────────
    SHORTENER_API: str = os.environ.get("SHORTENER_API", "")
    SHORTENER_SITE: str = os.environ.get("SHORTENER_SITE", "api.shrtco.de")

    # ── Bot Meta (set at runtime) ──────────────────────────────
    BOT_USERNAME: str = ""   # Populated after bot.start()

    # ── Anti-Spam ──────────────────────────────────────────────
    # Minimum seconds between file requests per user
    REQUEST_DELAY: int = int(os.environ.get("REQUEST_DELAY", 5))

    # ── Default Texts (overridable via /set_about, /set_plans) ─
    DEFAULT_ABOUT_TEXT: str = (
        "**ℹ️ About This Bot**\n\n"
        "🤖 I am a premium File Store Bot.\n"
        "📦 I safely store and deliver files on demand.\n"
        "🔒 All files are encrypted in a private channel.\n\n"
        "👑 Upgrade to **Premium** for:\n"
        "  • Bypass link shortener\n"
        "  • Priority file delivery\n"
        "  • Exclusive content access\n\n"
        "💬 Support: @raj_support_group"
    )

    DEFAULT_PREMIUM_TEXT: str = (
        "👑 **Premium Plans**\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🥈 **Silver** — 1 Month\n"
        "   ✅ Bypass Shortener\n"
        "   ✅ Priority Delivery\n"
        "   💰 Price: ₹30\n\n"
        "🥇 **Gold** — 3 Months\n"
        "   ✅ All Silver Benefits\n"
        "   ✅ Exclusive Content\n"
        "   💰 Price: ₹80\n\n"
        "💎 **Diamond** — 1year\n"
        "   ✅ All Gold Benefits\n"
        "   ✅ VIP Support\n"
        "   💰 Price: ₹500\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "📩 Contact: @raj_dev_01 to purchase"
    )

    # ── Validation ─────────────────────────────────────────────
    @classmethod
    def validate(cls):
        missing = []
        for field in ["API_ID", "API_HASH", "BOT_TOKEN", "MONGO_URL", "DB_CHANNEL"]:
            val = getattr(cls, field)
            if not val:
                missing.append(field)
        if missing:
            raise EnvironmentError(
                f"❌ Missing required environment variables: {', '.join(missing)}"
            )


# Validate on import
Config.validate()
