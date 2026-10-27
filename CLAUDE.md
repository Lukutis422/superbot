# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project layout

The bot lives entirely under `discord-pro-bot-MAX-PRO/`. All commands below assume that as the working directory.

```
bot.py               – entry point; defines ProBot class and wires everything together
config.example.yml   – canonical config template (copy → config.yml)
requirements.txt
cogs/                – one file per feature area (each ends with async def setup(bot))
database/db.py       – single aiosqlite connection wrapper; schema defined inline as SCHEMA
utils/
  checks.py          – reusable app_command checks: require_guild(), is_staff_or_mod(), can_moderate_target()
  config.py          – ConfigManager: loads config.yml, merges per-guild overrides over defaults
  errors.py          – global app_command error handler
  logger.py          – setup_logging()
  time.py            – utc_now_ts() helper
  views.py           – persistent discord.ui.View classes (TicketPanelView, TicketCloseView)
```

## Running the bot

```bash
cd discord-pro-bot-MAX-PRO
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp config.example.yml config.yml   # edit as needed
# create .env with DISCORD_TOKEN=...

python bot.py
```

Useful env vars (all optional):
| Variable | Default | Purpose |
|---|---|---|
| `DISCORD_TOKEN` | — | **Required** |
| `CONFIG_PATH` | `config.yml` | Path to YAML config |
| `DB_PATH` | `database/bot.sqlite3` | SQLite file location |
| `LOG_LEVEL` | `INFO` | Python log level |
| `SYNC_COMMANDS` | `true` | Set to `false` to skip `tree.sync()` on startup |

## Architecture

### Config system (`utils/config.py`)
`ConfigManager` holds a two-level YAML structure: `defaults` and per-guild overrides under `guilds.<guild_id>`. `get_guild_config(guild_id)` deep-merges the guild override on top of defaults, so cogs always call that method and never read `config.data` directly.

`set_key(guild_id, dotted_key, raw_value)` only accepts keys under the five top-level sections: `moderation.`, `welcome.`, `tickets.`, `xp.`, `role_menu.`.

### Database (`database/db.py`)
A single persistent `aiosqlite` connection (WAL mode, foreign keys on). Schema is applied via `executescript` on startup. All cog queries go through `db.execute()`, `db.fetchone()`, or `db.fetchall()` — raw SQL, no ORM.

Tables: `warnings`, `tickets`, `xp`.

### Cog pattern
Every cog receives the `ProBot` instance and accesses `bot.config`, `bot.db`, and `bot.log`. All slash commands are `@app_commands.command`. Guards are applied by calling check helpers (not decorators) inside the command body — e.g. `if not await is_staff_or_mod(self.bot).predicate(interaction): raise app_commands.CheckFailure()`.

### Permission model
- `require_guild()` — guild-only guard (all commands use this)
- `is_admin_or_manage_guild()` — admin setup commands
- `is_staff_or_mod(bot)` — checks for configured `staff_role_id` first, then falls back to Discord permissions (manage_messages / kick / ban / moderate / administrator)
- `can_moderate_target(actor, target, bot_member)` — role-hierarchy check, returns `(bool, reason_str)`

### Ticket flow
`TicketPanelView` / `TicketCloseView` in `utils/views.py` use fixed `custom_id` constants (`TICKET_CREATE_CUSTOM_ID`, `TICKET_CLOSE_CUSTOM_ID`). The `Tickets` cog listens for `on_interaction` and dispatches to `_create_ticket` / `_close_ticket` based on those IDs. The ticket channel is deleted 10 s after close.

### XP system
XP is awarded per message with a per-guild cooldown (default 45 s). Level formula: `xp_for_next_level(level) = 5*level² + 50*level + 100`. On level-up the bot assigns a role reward (if configured under `xp.level_rewards`) and posts a message in the channel.

## Adding a new cog

1. Create `cogs/yourfeature.py` with a `commands.Cog` subclass and `async def setup(bot): await bot.add_cog(YourCog(bot))`.
2. Add `"cogs.yourfeature"` to the `COGS` tuple in `bot.py`.
3. If the feature needs new DB tables, append them to the `SCHEMA` string in `database/db.py`.
4. Config keys for the feature must be added to the `config.example.yml` defaults and white-listed in `ConfigManager.set_key`.

## In-Discord setup commands

After inviting the bot, configure each guild with these slash commands:

```
/setlogchannel       – moderation log channel
/setstaffrole        – staff role (used for mod checks and ticket access)
/setticketcategory   – category where ticket channels are created
/setwelcome          – welcome/goodbye channel and autorole
/setautorole         – role assigned on member join
/config show         – dump current guild config
/config set <key> <value>   – set a dotted config key (e.g. xp.enabled false)
```
