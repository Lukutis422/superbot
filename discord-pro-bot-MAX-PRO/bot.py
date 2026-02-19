import os
from datetime import datetime, timezone
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from database.db import Database
from utils.config import ConfigManager
from utils.errors import friendly_app_command_error
from utils.logger import setup_logging

INTENTS = discord.Intents.default()
INTENTS.members = True
INTENTS.message_content = True

COGS = (
    "cogs.core",
    "cogs.moderation",
    "cogs.welcome",
    "cogs.tickets",
    "cogs.xp",
    "cogs.roles",
    "cogs.admin",
)

class ProBot(commands.Bot):
    def __init__(self, *, config: ConfigManager, db: Database, logger):
        super().__init__(command_prefix=commands.when_mentioned_or("!"), intents=INTENTS, help_command=None)
        self.config = config
        self.db = db
        self.log = logger
        self.started_at = datetime.now(timezone.utc)

    async def setup_hook(self) -> None:
        for ext in COGS:
            try:
                await self.load_extension(ext)
                self.log.info("Loaded extension: %s", ext)
            except Exception:
                self.log.exception("Failed loading extension: %s", ext)

        await self.db.init()

        sync_flag = os.getenv("SYNC_COMMANDS", "true").strip().lower() in ("1", "true", "yes", "y")
        if sync_flag:
            try:
                synced = await self.tree.sync()
                self.log.info("Synced %d app commands globally.", len(synced))
            except Exception:
                self.log.exception("Command sync failed.")
        else:
            self.log.info("SYNC_COMMANDS disabled; skipping tree.sync().")

    async def on_ready(self) -> None:
        self.log.info("Logged in as %s (ID: %s)", self.user, self.user.id)
        self.log.info("Guilds: %d", len(self.guilds))

    async def on_error(self, event_method: str, /, *args, **kwargs) -> None:
        self.log.exception("Unhandled error in event: %s", event_method)

    async def close(self) -> None:
        try:
            await self.db.close()
        finally:
            await super().close()

def main() -> None:
    load_dotenv()
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("Missing DISCORD_TOKEN in .env")

    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger = setup_logging(log_level=log_level, log_file="logs/bot.log")

    config_path = os.getenv("CONFIG_PATH", "config.yml")
    config = ConfigManager(path=config_path, logger=logger)
    config.load_or_create_from_example(example_path="config.example.yml")

    db_path = os.getenv("DB_PATH", "database/bot.sqlite3")
    db = Database(db_path=db_path, logger=logger)

    bot = ProBot(config=config, db=db, logger=logger)

    @bot.tree.error
    async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
        await friendly_app_command_error(bot, interaction, error)

    bot.run(token, log_handler=None)

if __name__ == "__main__":
    main()
