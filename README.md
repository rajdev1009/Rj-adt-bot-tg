# 📦 Telegram File Store Bot

> A professional, fully automated **Pyrogram + MongoDB** File Store Bot with admin controls, premium system, link shortener, animated UX, and one-click deployment support.

---

## ✨ Features

| Feature | Description |
|---|---|
| 📁 **File Store** | Admin uploads files → auto-saved to private DB channel |
| 🔗 **Smart Links** | Deep-links with optional URL shortener toggle |
| 👑 **Premium System** | Per-user premium with expiry, bypass shortener & premium mode |
| ⚙️ **Admin Panel** | Inline button control panel via `/settings` |
| 📡 **Broadcast** | Send messages to all users in one command |
| 🎬 **Animations** | Startup, search, and delivery animations |
| 🔒 **Force Subscribe** | Block file access until user joins update channel |
| 🛡️ **Anti-Spam** | Per-user request cooldown |
| 🗄️ **Dual DB** | MongoDB primary + NeonDB (PostgreSQL) optional |
| 🐳 **Docker Ready** | Dockerfile + Compose for instant deployment |

---

## 🚀 Quick Start

### 1. Clone & Configure

```bash
git clone https://github.com/yourrepo/telegram-filestore-bot
cd telegram-filestore-bot
cp .env.example .env
nano .env   # Fill in your credentials
```

### 2. Get Required Credentials

| Credential | Where to get |
|---|---|
| `API_ID` / `API_HASH` | [my.telegram.org](https://my.telegram.org) → API Development Tools |
| `BOT_TOKEN` | [@BotFather](https://t.me/BotFather) → `/newbot` |
| `DB_CHANNEL` | Create a **private** channel, add bot as admin, get numeric ID |
| `UPDATE_CHANNEL` | Create a **public** channel, add bot as admin |
| `ADMINS` | Your Telegram user ID (get from [@userinfobot](https://t.me/userinfobot)) |
| `MONGO_URL` | [MongoDB Atlas](https://cloud.mongodb.com) free tier |

### 3. Run Locally

```bash
pip install -r requirements.txt
python bot.py
```

### 4. Run with Docker

```bash
docker-compose up --build -d
docker-compose logs -f bot    # view logs
```

---

## ☁️ Cloud Deployment

### Koyeb

1. Push your code to GitHub
2. New Service → GitHub → select repo
3. Add all ENV variables in the Koyeb dashboard
4. Build Command: *(empty — uses Dockerfile)*
5. Run Command: `python bot.py`

### Render

1. New Web Service → Connect GitHub repo
2. Environment: **Docker**
3. Add ENV vars under *Environment*
4. Deploy!

### Railway

```bash
railway login
railway init
railway up
```
Set ENV vars in the Railway dashboard.

---

## 📖 Bot Commands

### User Commands

| Command | Description |
|---|---|
| `/start` | Welcome screen with menu buttons |
| `/help` | Show tutorial video or text guide |

### Admin Commands

| Command | Description |
|---|---|
| `/settings` | Open inline admin control panel |
| `/add_premium <id> <days>` | Grant premium to a user |
| `/remove_premium <id>` | Revoke premium |
| `/ban <id>` | Ban a user |
| `/broadcast` | Broadcast (reply to any message) |
| `/add_tutorial` | Set help tutorial (reply to video) |
| `/set_about <text>` | Update about text |
| `/set_plans <text>` | Update premium plans text |
| `/stats` | View bot statistics |

---

## ⚙️ Settings Panel (`/settings`)

The settings panel gives admins an inline button interface to:

- **🟢/🔴 Shortener Toggle** — Turn link shortening on/off globally
- **🔑 Change API Key** — Update the shortener API key without restart
- **👑 Premium Mode** — Restrict all file access to premium users only
- **📝 Edit About / Plans** — Update dynamic text shown to users
- **📊 Stats** — Quick stats overview

---

## 🗄️ Switching to NeonDB

By default, **MongoDB** is used. To switch to **NeonDB (PostgreSQL)**:

1. Set `NEON_URL` in your `.env`
2. Open `database/__init__.py`
3. Change: `DB = MongoDB` → `DB = NeonDB`
4. Restart the bot

Both databases expose an **identical async interface** so nothing else changes.

---

## 🔗 Link Shortener

The bot supports any shortener API that accepts:
```
https://your-site.com/api?api=KEY&url=LONG_URL
```

Tested with:
- **shrtco.de** (free, no key needed — set `SHORTENER_API=` blank)
- **tinyurl.com API**
- Any custom shortener following the above format

**Premium users always receive direct links**, even when shortener is ON.

---

## 📁 Project Structure

```
telegram-filestore-bot/
├── bot.py                  ← Entry point
├── config.py               ← All ENV variables + validation
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── database/
│   ├── __init__.py         ← DB alias (switch MongoDB ↔ NeonDB here)
│   ├── mongodb.py          ← MongoDB async operations
│   └── neondb.py           ← NeonDB/PostgreSQL async operations
├── handlers/
│   ├── __init__.py
│   ├── start.py            ← /start + file delivery
│   ├── upload.py           ← Admin file uploads
│   ├── settings.py         ← Admin settings panel
│   ├── admin.py            ← Admin commands
│   └── help.py             ← /help command
└── utils/
    ├── __init__.py
    ├── helpers.py          ← Animations, shortener, formatting
    └── decorators.py       ← admin_only, force_subscribe
```

---

## 🛡️ Security Notes

- Never commit your `.env` file (it's in `.gitignore`)
- The DB channel should be **private** — only the bot has access
- Bot must be admin in both `DB_CHANNEL` and `UPDATE_CHANNEL`
- Banned users are stored in DB and blocked from all file access

---

## 📄 License

MIT — free to use and modify.
