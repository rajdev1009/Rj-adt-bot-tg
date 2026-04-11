"""
╔══════════════════════════════════════════════════════════════╗
║                  NEONDB (PostgreSQL) MODULE                  ║
║   Optional secondary database — mirrors MongoDB structure    ║
╚══════════════════════════════════════════════════════════════╝

To SWITCH to NeonDB as primary, replace `MongoDB` import in
handlers with `NeonDB` and ensure NEON_URL is set.

Tables:
  • users     — all bot users
  • premium   — premium status + expiry
  • files     — file metadata
  • settings  — key-value bot settings
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

import asyncpg
from config import Config

logger = logging.getLogger("NeonDB")

# DDL — tables are created on first connect if they don't exist
_DDL = """
CREATE TABLE IF NOT EXISTS users (
    user_id      BIGINT PRIMARY KEY,
    full_name    TEXT NOT NULL,
    username     TEXT,
    joined_at    TIMESTAMPTZ DEFAULT now(),
    last_active  TIMESTAMPTZ DEFAULT now(),
    request_count INT DEFAULT 0,
    banned       BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS premium (
    user_id   BIGINT PRIMARY KEY,
    expiry    TIMESTAMPTZ NOT NULL,
    added_by  BIGINT,
    added_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS files (
    file_id        TEXT PRIMARY KEY,
    file_name      TEXT,
    message_id     BIGINT,
    file_size      BIGINT DEFAULT 0,
    file_type      TEXT DEFAULT 'document',
    direct_url     TEXT,
    short_url      TEXT,
    uploaded_at    TIMESTAMPTZ DEFAULT now(),
    download_count INT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS settings (
    key        TEXT PRIMARY KEY,
    value      TEXT,
    updated_at TIMESTAMPTZ DEFAULT now()
);
"""


class NeonDB:
    _pool: Optional[asyncpg.Pool] = None

    @classmethod
    async def connect(cls):
        cls._pool = await asyncpg.create_pool(Config.NEON_URL, min_size=2, max_size=10)
        async with cls._pool.acquire() as conn:
            await conn.execute(_DDL)
        logger.info("NeonDB tables ready.")

    @classmethod
    async def disconnect(cls):
        if cls._pool:
            await cls._pool.close()

    # ══════════════════════════════════════════════════════════
    #  USER METHODS
    # ══════════════════════════════════════════════════════════

    @classmethod
    async def add_user(cls, user_id: int, full_name: str, username: str = None):
        async with cls._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO users (user_id, full_name, username)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id) DO NOTHING
                """,
                user_id, full_name, username,
            )

    @classmethod
    async def update_last_active(cls, user_id: int):
        async with cls._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE users
                SET last_active = now(), request_count = request_count + 1
                WHERE user_id = $1
                """,
                user_id,
            )

    @classmethod
    async def get_all_user_ids(cls) -> List[int]:
        async with cls._pool.acquire() as conn:
            rows = await conn.fetch("SELECT user_id FROM users WHERE banned = FALSE")
            return [r["user_id"] for r in rows]

    @classmethod
    async def get_user_count(cls) -> int:
        async with cls._pool.acquire() as conn:
            return await conn.fetchval("SELECT COUNT(*) FROM users")

    @classmethod
    async def ban_user(cls, user_id: int):
        async with cls._pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET banned = TRUE WHERE user_id = $1", user_id
            )

    @classmethod
    async def is_banned(cls, user_id: int) -> bool:
        async with cls._pool.acquire() as conn:
            val = await conn.fetchval(
                "SELECT banned FROM users WHERE user_id = $1", user_id
            )
            return bool(val)

    # ══════════════════════════════════════════════════════════
    #  FILE METHODS
    # ══════════════════════════════════════════════════════════

    @classmethod
    async def save_file(cls, file_id: str, file_name: str, message_id: int,
                        file_size: int = 0, file_type: str = "document",
                        direct_url: str = None, short_url: str = None):
        """
        Save file metadata. Stores both direct_url and short_url so the
        delivery handler can apply per-user link logic at request time.
        """
        async with cls._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO files
                    (file_id, file_name, message_id, file_size, file_type, direct_url, short_url)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (file_id) DO UPDATE
                SET file_name=$2, message_id=$3, file_size=$4,
                    file_type=$5, direct_url=$6, short_url=$7, uploaded_at=now()
                """,
                file_id, file_name, message_id, file_size, file_type, direct_url, short_url,
            )

    @classmethod
    async def get_file(cls, file_id: str) -> Optional[Dict[str, Any]]:
        async with cls._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM files WHERE file_id = $1", file_id
            )
            return dict(row) if row else None

    @classmethod
    async def increment_download(cls, file_id: str):
        async with cls._pool.acquire() as conn:
            await conn.execute(
                "UPDATE files SET download_count = download_count + 1 WHERE file_id = $1",
                file_id,
            )

    # ══════════════════════════════════════════════════════════
    #  PREMIUM METHODS
    # ══════════════════════════════════════════════════════════

    @classmethod
    async def add_premium(cls, user_id: int, days: int, added_by: int):
        expiry = datetime.now(timezone.utc) + timedelta(days=days)
        async with cls._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO premium (user_id, expiry, added_by)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id) DO UPDATE SET expiry=$2, added_by=$3, added_at=now()
                """,
                user_id, expiry, added_by,
            )

    @classmethod
    async def is_premium(cls, user_id: int) -> bool:
        async with cls._pool.acquire() as conn:
            expiry = await conn.fetchval(
                "SELECT expiry FROM premium WHERE user_id = $1", user_id
            )
            if not expiry:
                return False
            return expiry > datetime.now(timezone.utc)

    @classmethod
    async def get_premium_expiry(cls, user_id: int) -> Optional[datetime]:
        async with cls._pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT expiry FROM premium WHERE user_id = $1", user_id
            )

    @classmethod
    async def remove_premium(cls, user_id: int):
        async with cls._pool.acquire() as conn:
            await conn.execute("DELETE FROM premium WHERE user_id = $1", user_id)

    # ══════════════════════════════════════════════════════════
    #  SETTINGS METHODS  (JSON-encoded values stored as TEXT)
    # ══════════════════════════════════════════════════════════

    @classmethod
    async def get_setting(cls, key: str, default=None):
        import json
        async with cls._pool.acquire() as conn:
            val = await conn.fetchval(
                "SELECT value FROM settings WHERE key = $1", key
            )
            if val is None:
                return default
            try:
                return json.loads(val)
            except Exception:
                return val

    @classmethod
    async def set_setting(cls, key: str, value):
        import json
        encoded = json.dumps(value) if not isinstance(value, str) else value
        async with cls._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO settings (key, value, updated_at) VALUES ($1, $2, now())
                ON CONFLICT (key) DO UPDATE SET value=$2, updated_at=now()
                """,
                key, encoded,
            )

    # ── Mirrors of MongoDB convenience wrappers ────────────────

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
