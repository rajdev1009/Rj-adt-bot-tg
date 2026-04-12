"""
╔══════════════════════════════════════════════════════════════╗
║                    CONFIGURATION MODULE                      ║
║       All sensitive values loaded from environment vars      ║
║                                                              ║
║   Credit: RAJ DEV                                            ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
from typing import List, Union


def _parse_channel(val: str) -> Union[int, str]:
    """
    UPDATE_CHANNEL ya DB_CHANNEL dono format accept karta hai:
      • Numeric ID:  -1001234567890  → int(-1001234567890)
      • Username:    @MyChannel      → "@MyChannel"
      • Username:    MyChannel       → "@MyChannel"
    """
    val = val.strip()
    if not val:
        return ""
    # Numeric ID (negative for channels/groups)
    try:
        return int(val)
    except ValueError:
        pass
    # Username — @ add karo agar nahi hai
    if not val.startswith("@"):
        val = "@" + val
    return val


def _channel_url(val: Union[int, str]) -> str:
    """
    Inline button ke liye t.me URL banao.
    Numeric ID se URL nahi banta, isliye numeric ID pe
    UPDATE_CHANNEL_USERNAME env var use hoga.
    """
    if isinstance(val, int):
        # Numeric ID ke saath t.me URL nahi banta directly
        # UPDATE_CHANNEL_USERNAME se username lenge
        username = os.environ.get("UPDATE_CHANNEL_USERNAME", "").strip().lstrip("@")
        if username:
            return f"https://t.me/{username}"
        return ""
    return f"https://t.me/{str(val).lstrip('@')}"


class Config:
    # ── Telegram API Credentials ───────────────────────────────
    API_ID: int = int(os.environ.get("API_ID", 0))
    API_HASH: str = os.environ.get("API_HASH", "")
    BOT_TOKEN: str = os.environ.get("BOT_TOKEN", "")

    # ── Channels ───────────────────────────────────────────────
    # DB_CHANNEL: Private channel jahan files store hoti hain
    # Format: -1001234567890 (numeric ID) ya @username
    DB_CHANNEL: Union[int, str] = _parse_channel(os.environ.get("DB_CHANNEL", "0"))

    # UPDATE_CHANNEL: Public channel jahan file posts announce hote hain
    # Format: -1001234567890 ya @MyChannel ya MyChannel
    UPDATE_CHANNEL: Union[int, str] = _parse_channel(os.environ.get("UPDATE_CHANNEL", ""))

    # UPDATE_CHANNEL_USERNAME: Sirf button URL ke liye (agar numeric ID use kar rahe ho)
    # Example: @MyChannel ya MyChannel
    # Agar UPDATE_CHANNEL username format mein hai to yeh optional hai
    UPDATE_CHANNEL_USERNAME: str = os.environ.get("UPDATE_CHANNEL_USERNAME", "").strip()

    # ── Admins ─────────────────────────────────────────────────
    ADMINS: List[int] = [
        int(x.strip())
        for x in os.environ.get("ADMINS", "").split(",")
        if x.strip().lstrip("-").isdigit()
    ]

    # ── Database URLs ──────────────────────────────────────────
    MONGO_URL: str = os.environ.get("MONGO_URL", "")
    NEON_URL: str = os.environ.get("NEON_URL", "")

    # ── Link Shortener ─────────────────────────────────────────
    SHORTENER_API: str = os.environ.get("SHORTENER_API", "")
    SHORTENER_SITE: str = os.environ.get("SHORTENER_SITE", "api.shrtco.de")

    # ── Bot Meta (runtime mein set hoga) ──────────────────────
    BOT_USERNAME: str = ""

    # ── Anti-Spam ──────────────────────────────────────────────
    REQUEST_DELAY: int = int(os.environ.get("REQUEST_DELAY", 5))

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
        "💬 Support: @YourSupportGroup\n\n"
        "🔖 _Powered by **RAJ DEV**_"
    )

    DEFAULT_PREMIUM_TEXT: str = (
        "👑 **Premium Plans**\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🥈 **Silver** — 1 Month\n"
        "   ✅ Shortener Bypass\n"
        "   ✅ Priority Delivery\n"
        "   💰 Price: ₹X\n\n"
        "🥇 **Gold** — 3 Months\n"
        "   ✅ Silver ke sab fayde\n"
        "   ✅ Exclusive Content\n"
        "   💰 Price: ₹Y\n\n"
        "💎 **Diamond** — Lifetime\n"
        "   ✅ Gold ke sab fayde\n"
        "   ✅ VIP Support\n"
        "   💰 Price: ₹Z\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "📩 Purchase ke liye contact: @YourUsername\n\n"
        "🔖 _Powered by **RAJ DEV**_"
    )

    @classmethod
    def get_channel_url(cls) -> str:
        """
        Update channel ka t.me URL return karo buttons ke liye.
        Priority:
          1. UPDATE_CHANNEL_USERNAME env var (ya runtime mein set hua)
          2. UPDATE_CHANNEL agar @username format mein hai
          3. Numeric ID → koi URL nahi (buttons nahi dikhenge)
        """
        # 1. Explicit username (env se ya bot.py ne runtime mein set kiya)
        if cls.UPDATE_CHANNEL_USERNAME:
            u = str(cls.UPDATE_CHANNEL_USERNAME).lstrip("@")
            if u:
                return f"https://t.me/{u}"
        # 2. UPDATE_CHANNEL username string hai
        if isinstance(cls.UPDATE_CHANNEL, str) and cls.UPDATE_CHANNEL.startswith("@"):
            return f"https://t.me/{cls.UPDATE_CHANNEL.lstrip('@')}"
        # 3. Numeric ID — URL nahi bana sakte
        return ""

    @classmethod
    def validate(cls):
        missing = []
        for field in ["API_ID", "API_HASH", "BOT_TOKEN", "MONGO_URL"]:
            val = getattr(cls, field)
            if not val:
                missing.append(field)
        if not cls.DB_CHANNEL:
            missing.append("DB_CHANNEL")
        if missing:
            raise EnvironmentError(
                f"❌ Missing required environment variables: {', '.join(missing)}"
            )


Config.validate()
