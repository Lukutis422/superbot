import logging
from typing import Any, Iterable, Optional

import aiosqlite

SCHEMA = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS warnings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  guild_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  moderator_id INTEGER NOT NULL,
  reason TEXT NOT NULL,
  created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_warnings_guild_user ON warnings (guild_id, user_id);

CREATE TABLE IF NOT EXISTS tickets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  guild_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  channel_id INTEGER NOT NULL,
  status TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  closed_at INTEGER
);

CREATE INDEX IF NOT EXISTS idx_tickets_guild_user_status ON tickets (guild_id, user_id, status);
CREATE INDEX IF NOT EXISTS idx_tickets_guild_channel ON tickets (guild_id, channel_id);

CREATE TABLE IF NOT EXISTS xp (
  guild_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  xp INTEGER NOT NULL DEFAULT 0,
  level INTEGER NOT NULL DEFAULT 0,
  last_award_at INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (guild_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_xp_guild_level_xp ON xp (guild_id, level DESC, xp DESC);
"""


class Database:
    def __init__(self, *, db_path: str, logger: logging.Logger):
        self.db_path = db_path
        self.log = logger
        self._conn: Optional[aiosqlite.Connection] = None

    async def connect(self) -> aiosqlite.Connection:
        if self._conn is None:
            self._conn = await aiosqlite.connect(self.db_path)
            self._conn.row_factory = aiosqlite.Row
        return self._conn

    async def init(self) -> None:
        conn = await self.connect()
        await conn.executescript(SCHEMA)
        await conn.commit()
        self.log.info("Database initialized at %s", self.db_path)

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None
            self.log.info("Database connection closed.")

    async def execute(self, query: str, params: Iterable[Any] = ()) -> None:
        conn = await self.connect()
        await conn.execute(query, tuple(params))
        await conn.commit()

    async def fetchone(self, query: str, params: Iterable[Any] = ()):
        conn = await self.connect()
        async with conn.execute(query, tuple(params)) as cur:
            return await cur.fetchone()

    async def fetchall(self, query: str, params: Iterable[Any] = ()):
        conn = await self.connect()
        async with conn.execute(query, tuple(params)) as cur:
            return await cur.fetchall()
