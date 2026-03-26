# 📡 Telegram Story & Post Downloader Bot

A Telegram bot that downloads **stories** and **media posts** from any Telegram user — fast, with parallel downloads.

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)
![Telethon](https://img.shields.io/badge/Telethon-MTProto-red?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/template)

</div>

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📖 **Story Download** | Download all active stories from any user |
| 📌 **Post Download** | Download media posts (photos, videos, GIFs) |
| ⚡ **Fast & Parallel** | Downloads 5 files simultaneously |
| 🔒 **Admin Only** | Restrict bot access to your account |
| 📂 **Auto Cleanup** | Files are deleted after sending |

---

## 🤖 Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Show help message |
| `/stories username` | Download user's stories |
| `/posts username` | Download last 20 media posts |
| `/posts username 50` | Download last 50 media posts |
| `/all username` | Download stories + posts |
| Send a username | Quick fetch stories |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Telegram Bot Token → [@BotFather](https://t.me/BotFather)
- API ID & Hash → [my.telegram.org](https://my.telegram.org)
- Your Telegram User ID → [@userinfobot](https://t.me/userinfobot)

### 1. Clone & Install

```bash
git clone https://github.com/emberrenewed/telegram-story-bot.git
cd telegram-story-bot
pip install -r requirements.txt
```

### 2. Configure

Create a `.env` file:

```env
BOT_TOKEN=your_bot_token
API_ID=your_api_id
API_HASH=your_api_hash
PHONE_NUMBER=+your_phone_number
ADMIN_ID=your_telegram_user_id
```

### 3. Run

```bash
python bot.py
```

> On first run, you'll be asked for a verification code sent to your Telegram app. This only happens once.

---

## ☁️ Deploy to Railway

1. Fork this repo
2. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub**
3. Select the repo
4. Add environment variables in the **Variables** tab:

   ```
   BOT_TOKEN=...
   API_ID=...
   API_HASH=...
   PHONE_NUMBER=...
   ADMIN_ID=...
   ```

5. Deploy!

> ⚠️ **Important:** Run the bot locally first to generate `story_session.session`, then commit it to the repo so Railway doesn't need a verification code.

---

## 🐳 Deploy with Docker

```bash
docker compose up -d --build
```

---

## 📁 Project Structure

```
telegram-story-bot/
├── bot.py                 # Main bot code
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (not committed)
├── .env.example           # Example env file
├── Dockerfile             # Docker config
├── docker-compose.yml     # Docker Compose config
├── Procfile               # Railway/Render process file
└── story_session.session  # Telethon session (generated on first run)
```

---

## ⚠️ Notes

- You can **only view stories** that your Telegram account is allowed to see (based on privacy settings)
- The bot uses your **user account** via Telethon to access stories (Bot API doesn't support stories)
- Set `ADMIN_ID=0` to allow anyone to use the bot
- Post download limit is capped at **100** per request

---

## 📄 License

MIT License — free to use, modify, and distribute.
