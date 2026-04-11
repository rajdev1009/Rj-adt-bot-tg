"""
╔══════════════════════════════════════════════════════════════╗
║                   MONGODB DATABASE MODULE                    ║
║     Users, Premium, Files, Bot Settings — all in Mongo       ║
╚══════════════════════════════════════════════════════════════╝
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from motor.motor_asyncio import AsyncIOMotorClient
from config import Config

logger = logging.getLogger("MongoDB")


class MongoDB:
    _client: Optional[AsyncIOMotorClient] = None
    _db = None

    # ── Collections ────────────────────────────────────────────
    _users = None
    _files = None
    _settings = None
    _premium = None

    @classmethod
    async def connect(cls):
        cls._client = AsyncIOMotorClient(Config.MONGO_URL)
        cls._db = cls._client["FileStoreBotDB"]
        cls._users    = cls._db["users"]
        cls._files    = cls._db["files"]
        cls._settings = cls._db["settings"]
        cls._premium  = cls._db["premium"]

        # Create indexes for performance
        await cls._users.create_index("user_id", unique=True)
        await cls._files.create_index("file_id", unique=True)
        await cls._premium.create_index("user_id", unique=True)
        logger.info("MongoDB indexes ensured.")

    @classmethod
    async def disconnect(cls):
        if cls._client:
            cls._client.close()

    # ══════════════════════════════════════════════════════════
    #  USER METHODS
    # ══════════════════════════════════════════════════════════

    @classmethod
    async def add_user(cls, user_id: int, full_name: str, username: str = None):
        """Insert user if not exists, otherwise no-op."""
        await cls._users.update_one(
            {"user_id": user_id},
            {
                "$setOnInsert": {
                    "user_id": user_id,
                    "full_name": full_name,
                    "username": username,
                    "joined_at": datetime.now(timezone.utc),
                    "last_active": datetime.now(timezone.utc),
                    "request_count": 0,
                    "banned": False,
                }
            },
            upsert=True,
        )

    @classmethod
    async def update_last_active(cls, user_id: int):
        await cls._users.update_one(
            {"user_id": user_id},
            {
                "$set": {"last_active": datetime.now(timezone.utc)},
                "$inc": {"request_count": 1},
            },
        )

    @classmethod
    async def get_all_user_ids(cls) -> List[int]:
        cursor = cls._users.find({"banned": False}, {"user_id": 1})
        return [doc["user_id"] async for doc in cursor]

    @classmethod
    async def get_user_count(cls) -> int:
        return await cls._users.count_documents({})

    @classmethod
    async def ban_user(cls, user_id: int):
        await cls._users.update_one(
            {"user_id": user_id}, {"$set": {"banned": True}}
        )

    @classmethod
    async def is_banned(cls, user_id: int) -> bool:
        doc = await cls._users.find_one({"user_id": user_id})
        return doc.get("banned", False) if doc else False

    # ══════════════════════════════════════════════════════════
    #  FILE METHODS
    # ══════════════════════════════════════════════════════════

    @classmethod
    async def save_file(cls, file_id: str, file_name: str, message_id: int,
                        file_size: int = 0, file_type: str = "document",
                        direct_url: str = None, short_url: str = None):
        """
        Save file metadata after upload to DB channel.

        Both direct_url (permanent bot deep-link) and short_url (optional
        shortened link) are stored so the delivery handler can pick the
        correct one per user at request time:
          • Premium user  → always direct_url
          • Regular user  → short_url if set, otherwise direct_url
        """
        await cls._files.update_one(
            {"file_id": file_id},
            {
                "$set": {
                    "file_id":        file_id,
                    "file_name":      file_name,
                    "message_id":     message_id,
                    "file_size":      file_size,
                    "file_type":      file_type,
                    "direct_url":     direct_url,
                    "short_url":      short_url,
                    "uploaded_at":    datetime.now(timezone.utc),
                    "download_count": 0,
                }
            },
            upsert=True,
        )

    @classmethod
    async def get_file(cls, file_id: str) -> Optional[Dict[str, Any]]:
        return await cls._files.find_one({"file_id": file_id})

    @classmethod
    async def increment_download(cls, file_id: str):
        await cls._files.update_one(
            {"file_id": file_id}, {"$inc": {"download_count": 1}}
        )

    # ══════════════════════════════════════════════════════════
    #  PREMIUM METHODS
    # ══════════════════════════════════════════════════════════

    @classmethod
    async def add_premium(cls, user_id: int, days: int, added_by: int):
        from datetime import timedelta
        expiry = datetime.now(timezone.utc) + timedelta(days=days)
        await cls._premium.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "user_id": user_id,
                    "expiry": expiry,
                    "added_by": added_by,
                    "added_at": datetime.now(timezone.utc),
                }
            },
            upsert=True,
        )

    @classmethod
    async def is_premium(cls, user_id: int) -> bool:
        doc = await cls._premium.find_one({"user_id": user_id})
        if not doc:
            return False
        return doc["expiry"] > datetime.now(timezone.utc)

    @classmethod
    async def get_premium_expiry(cls, user_id: int) -> Optional[datetime]:
        doc = await cls._premium.find_one({"user_id": user_id})
        return doc["expiry"] if doc else None

    @classmethod
    async def remove_premium(cls, user_id: int):
        await cls._premium.delete_one({"user_id": user_id})

    # ══════════════════════════════════════════════════════════
    #  SETTINGS METHODS
    # ══════════════════════════════════════════════════════════

    @classmethod
    async def get_setting(cls, key: str, default=None):
        doc = await cls._settings.find_one({"key": key})
        return doc["value"] if doc else default

    @classmethod
    async def set_setting(cls, key: str, value):
        await cls._settings.update_one(
            {"key": key},
            {"$set": {"key": key, "value": value, "updated_at": datetime.now(timezone.utc)}},
            upsert=True,
        )

    # ── Convenience wrappers for common settings ───────────────

    @classmethod
    async def is_shortener_on(cls) -> bool:
        return await cls.get_setting("shortener_enabled", False)

    @classmethod
    async def toggle_shortener(cls) -> bool:
        current = await cls.is_shortener_on()
        await cls.set_setting("shortener_enabled", not current)
        return not current

    @classmethod
    async def is_premium_mode(cls) -> bool:
        return await cls.get_setting("premium_mode", False)

    @classmethod
    async def toggle_premium_mode(cls) -> bool:
        current = await cls.is_premium_mode()
        await cls.set_setting("premium_mode", not current)
        return not current

    @classmethod
    async def get_shortener_api(cls) -> str:
        return await cls.get_setting("shortener_api", Config.SHORTENER_API)

    @classmethod
    async def set_shortener_api(cls, api_key: str):
        await cls.set_setting("shortener_api", api_key)

    @classmethod
    async def get_about_text(cls) -> str:
        return await cls.get_setting("about_text", Config.DEFAULT_ABOUT_TEXT)

    @classmethod
    async def set_about_text(cls, text: str):
        await cls.set_setting("about_text", text)

    @classmethod
    async def get_premium_text(cls) -> str:
        return await cls.get_setting("premium_text", Config.DEFAULT_PREMIUM_TEXT)

    @classmethod
    async def set_premium_text(cls, text: str):
        await cls.set_setting("premium_text", text)

    @classmethod
    async def get_tutorial_file_id(cls) -> Optional[str]:
        return await cls.get_setting("tutorial_file_id", None)

    @classmethod
    async def set_tutorial_file_id(cls, file_id: str):
        await cls.set_setting("tutorial_file_id", file_id)
