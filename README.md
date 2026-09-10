# identifikatsiya-murojaat-bot

Telegram bot skeleton built with aiogram 3.x, SQLAlchemy 2.x (async, SQLite) and python-dotenv.

## Stack

- Python 3.12
- aiogram 3.x
- SQLite
- SQLAlchemy 2.x
- python-dotenv

## Setup

1. Create a virtual environment and install dependencies:

   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and fill in the values:

   ```
   copy .env.example .env
   ```

   - `BOT_TOKEN` — your Telegram bot token from @BotFather
   - `ADMIN_IDS` — comma-separated Telegram user IDs of admins

3. Run the bot:

   ```
   python -m app.main
   ```

## Structure

```
app/
  main.py            # entry point, starts polling
  config.py          # loads BOT_TOKEN and ADMIN_IDS from .env
  database.py         # SQLAlchemy async engine/session setup
  handlers/
    start.py          # /start command handler
  models/              # SQLAlchemy models
  services/            # business logic
```

## Implemented

- `/start` — replies with a welcome message.
