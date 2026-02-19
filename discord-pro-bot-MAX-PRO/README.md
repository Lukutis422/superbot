# Discord PRO Bot (MAX PRO) – discord.py 2.x

## Quick start (Windows)
1) Copy `.env.example` → `.env` and set `DISCORD_TOKEN`
2) Copy `config.example.yml` → `config.yml`
3) Install:
```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```
4) Run:
```bat
python bot.py
```

## Deploy Railway / Render
Railway: Deploy repo, set env `DISCORD_TOKEN`, start `python bot.py`.
Render: Background Worker, build `pip install -r requirements.txt`, start `python bot.py`.

## Setup commands
- /setlogchannel
- /setstaffrole
- /setticketcategory
- /setwelcome
- /setautorole
- /config show
- /config set key value
