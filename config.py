"""
╔══════════════════════════════════════════════════════════════╗
║                    CONFIGURATION MODULE                      ║
║       All sensitive values loaded from environment vars      ║
║   Credit: RAJ DEV                                            ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
from typing import List, Union


def _parse_channel(val: str) -> Union[int, str]:
    val = val.strip()
    if not val:
        return ""
    try:
        return int(val)
    except ValueError:
        pass
    if not val.startswith("@"):
        val = "@" + val
    return val


class Config:
    # ── Telegram API ───────────────────────────────────────────
    API_ID: int    = int(os.environ.get("API_ID", 0))
    API_HASH: str  = os.environ.get("API_HASH", "")
    BOT_TOKEN: str = os.environ.get("BOT_TOKEN", "")

    # ── Channels ───────────────────────────────────────────────
    DB_CHANNEL: Union[int, str]     = _parse_channel(os.environ.get("DB_CHANNEL", "0"))
    UPDATE_CHANNEL: Union[int, str] = _parse_channel(os.environ.get("UPDATE_CHANNEL", ""))
    UPDATE_CHANNEL_USERNAME: str    = os.environ.get("UPDATE_CHANNEL_USERNAME", "").strip()

    # ── Admins ─────────────────────────────────────────────────
    ADMINS: List[int] = [
        int(x.strip())
        for x in os.environ.get("ADMINS", "").split(",")
        if x.strip().lstrip("-").isdigit()
    ]

    # ── Database ───────────────────────────────────────────────
    MONGO_URL: str = os.environ.get("MONGO_URL", "")
    # NeonDB optional hai — set karo to use hoga, nahi set kiya to skip hoga
    NEON_URL: str  = os.environ.get("NEON_URL", "")

    # ── Shortener (Shortzy — supports many sites) ──────────────
    # SHORTLINK_API = aapka shortener API key (env var)
    # SHORTLINK_URL = shortener domain e.g. shrinkme.io
    SHORTLINK_API: str = os.environ.get("SHORTLINK_API", "")
    SHORTLINK_URL: str = os.environ.get("SHORTLINK_URL", "shrinkme.io")

    # ── Auto Delete ────────────────────────────────────────────
    AUTO_DELETE_TIME: int = int(os.environ.get("AUTO_DELETE_TIME", 300))  # seconds

    # ── Anti-Spam ──────────────────────────────────────────────
    REQUEST_DELAY: int = int(os.environ.get("REQUEST_DELAY", 5))

    # ── Bot Meta ───────────────────────────────────────────────
    BOT_USERNAME: str = ""

    # ── Default Texts ──────────────────────────────────────────
    DEFAULT_ABOUT_TEXT: str = (
        "**ℹ️ About This Bot**\n\n"
        "🤖 Main ek Premium File Store Bot hoon.\n"
        "📦 Files safely store aur deliver karta hoon.\n"
        "🔒 Sab files private channel mein secure hain.\n\n"
        "👑 **Premium** ke fayde:\n"
        "  • Link shortener bypass\n"
        "  • Priority file delivery\n"
        "  • Exclusive content access\n\n"
        "💬 Support: @raj_dev_01\n\n"
        "🔖 _Powered by **RAJ DEV**_"
    )

    DEFAULT_PREMIUM_TEXT: str = (
        "👑 **Premium Plans**\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🥈 **Silver** — 1 Month\n"
        "   ✅ Shortener Bypass\n"
        "   ✅ Priority Delivery\n"
        "   💰 Price: ₹30\n\n"
        "🥇 **Gold** — 3 Months\n"
        "   ✅ Silver ke sab fayde\n"
        "   ✅ Exclusive Content\n"
        "   💰 Price: ₹80\n\n"
        "💎 **Diamond** — 6 Months\n"
        "   ✅ Gold ke sab fayde\n"
        "   ✅ VIP Support\n"
        "   💰 Price: ₹159\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "📩 Purchase: @raj_dev_01\n\n"
        "🔖 _Powered by **RAJ DEV**_"
    )

    @classmethod
    def get_channel_url(cls) -> str:
        u = str(cls.UPDATE_CHANNEL_USERNAME).strip().lstrip("@") if cls.UPDATE_CHANNEL_USERNAME else ""
        if u:
            return f"https://t.me/{u}"
        if isinstance(cls.UPDATE_CHANNEL, str):
            clean = cls.UPDATE_CHANNEL.strip().lstrip("@")
            if clean and not clean.lstrip("-").isdigit():
                return f"https://t.me/{clean}"
        return ""

    @classmethod
    def validate(cls):
        missing = []
        for field in ["API_ID", "API_HASH", "BOT_TOKEN", "MONGO_URL"]:
            if not getattr(cls, field):
                missing.append(field)
        if not cls.DB_CHANNEL:
            missing.append("DB_CHANNEL")
        if missing:
            raise EnvironmentError(f"❌ Missing env vars: {', '.join(missing)}")


Config.validate()
