<div align="center">

<img src="https://i.ibb.co/wNm5kJn4/1765831046347-2.jpg" width="120" height="120" style="border-radius: 50%;" alt="RAJ DEV"/>

# 📦 Telegram File Store Bot

### Built with ❤️ by [RAJ DEV](https://t.me/raj_dev_01)

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![Pyrogram](https://img.shields.io/badge/Pyrogram-2.0.106-green)](https://pyrogram.org)
[![MongoDB](https://img.shields.io/badge/MongoDB-Motor-brightgreen?logo=mongodb)](https://mongodb.com)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

*A professional, fully automated Telegram File Store Bot with Admin Controls, Premium System, Link Shortener, Animated UX, and one-click deployment.*

</div>

---

## 📌 Table of Contents

- [Features](#-features)
- [File Structure](#-file-structure)
- [Environment Variables](#-environment-variables)
- [Setup Guide](#-setup-guide)
- [Deployment](#-deployment)
- [Admin Commands](#-admin-commands)
- [User Commands](#-user-commands)
- [Settings Panel](#-settings-panel)
- [Shortener Logic](#-shortener-logic)
- [Premium System](#-premium-system)
- [Reset System](#-reset-system)
- [Security Features](#-security-features)
- [Animations](#-animations)
- [Database](#-database)
- [FAQ](#-faq)
- [Credits](#-credits)

---

## ✨ Features

| Feature | Description |
|---|---|
| 📁 **File Store** | Admin files upload karta hai → auto save DB channel mein |
| 🔗 **Smart Links** | Deep-links with optional URL shortener |
| 👑 **Premium System** | Per-user premium with expiry date |
| ⚙️ **Admin Panel** | Inline button control panel via `/settings` |
| 📡 **Broadcast** | Message send karo sab users ko ek command se |
| 🎬 **Animations** | Startup ⚡💎🛡️💖, Search loading bar, File found animation |
| 🔒 **Force Subscribe** | Channel join required before getting files |
| 🛡️ **Anti-Spam** | Per-user request cooldown |
| 🗄️ **Dual DB** | MongoDB primary + NeonDB (PostgreSQL) optional |
| 🔄 **Full Reset** | Password-protected system reset with confirmation |
| 🐳 **Docker Ready** | Dockerfile + Compose for instant deployment |
| ✨ **RAJ DEV Promo** | Admin name flash animation on every file request |

---

## 📁 File Structure

```
telegram-filestore-bot/
│
├── bot.py                    ← Main entry point — bot start/stop, health server
├── config.py                 ← All ENV variables + channel URL helpers
├── requirements.txt          ← Python dependencies
├── Dockerfile                ← Docker image build file
├── docker-compose.yml        ← Local dev stack (bot + MongoDB)
├── koyeb.yaml                ← Koyeb deployment config
├── render.yaml               ← Render.com deployment config
├── .env.example              ← ENV template — copy to .env
├── .gitignore                ← Git ignore rules
│
├── database/
│   ├── __init__.py           ← DB alias — change DB=MongoDB to DB=NeonDB here
│   ├── mongodb.py            ← Full MongoDB async operations
│   └── neondb.py             ← Full NeonDB/PostgreSQL async operations
│
├── handlers/
│   ├── __init__.py           ← Auto-loads all handlers
│   ├── start.py              ← /start command + file delivery logic + callbacks
│   ├── upload.py             ← Admin file upload → DB channel → Update Channel
│   ├── admin.py              ← All admin commands (/reset, /broadcast, etc.)
│   ├── settings.py           ← /settings inline panel with toggle buttons
│   └── help.py               ← /help command (admin full list, user tutorial)
│
└── utils/
    ├── __init__.py           ← Exports all utilities
    ├── helpers.py            ← Animations, shortener, file info extractor, anti-spam
    └── decorators.py         ← admin_only, admin_callback, force_subscribe decorators
```

### Each File Ka Kaam:

| File | Kaam |
|---|---|
| `bot.py` | Bot start karta hai, MongoDB connect karta hai, health check server chalata hai, FloodWait handle karta hai |
| `config.py` | Sab ENV variables read karta hai, channel URL banata hai |
| `database/mongodb.py` | Users, files, premium, settings — sab MongoDB operations |
| `database/neondb.py` | Same operations PostgreSQL/NeonDB ke liye |
| `database/__init__.py` | `DB = MongoDB` — yahan change karo NeonDB switch ke liye |
| `handlers/start.py` | `/start` command, file delivery, RAJ DEV promo flash, sab menu callbacks |
| `handlers/upload.py` | Admin file upload, DB channel copy, link generate, Update Channel post |
| `handlers/admin.py` | `/reset`, `/broadcast`, `/add_premium`, `/ban`, `/stats`, `/add_tutorial` etc. |
| `handlers/settings.py` | `/settings` inline panel — shortener toggle, premium mode, API key |
| `handlers/help.py` | Admin ke liye full command list, users ke liye tutorial + guide |
| `utils/helpers.py` | Animations (startup, search, found), URL shortener, file size format |
| `utils/decorators.py` | `@admin_only`, `@admin_callback`, force subscribe check |

---

## 🔐 Environment Variables

`.env.example` ko copy karke `.env` banao aur sab values fill karo.

```bash
cp .env.example .env
```

### Required Variables

| Variable | Example | Description |
|---|---|---|
| `API_ID` | `12345678` | Telegram API ID — [my.telegram.org](https://my.telegram.org) se lo |
| `API_HASH` | `abcdef1234567890` | Telegram API Hash — same page se |
| `BOT_TOKEN` | `123456:ABCdef...` | Bot token — [@BotFather](https://t.me/BotFather) se |
| `MONGO_URL` | `mongodb+srv://...` | MongoDB connection string |
| `DB_CHANNEL` | `-1001234567890` | Private storage channel ID |
| `UPDATE_CHANNEL` | `@raj_update_channel` | Public announcement channel username |
| `ADMINS` | `5804953849` | Aapka Telegram user ID (comma-separated multiple ke liye) |

### Optional Variables

| Variable | Default | Description |
|---|---|---|
| `NEON_URL` | *(empty)* | PostgreSQL/NeonDB URL — optional |
| `SHORTENER_API` | *(empty)* | Link shortener API key |
| `SHORTENER_SITE` | `api.shrtco.de` | Shortener domain |
| `REQUEST_DELAY` | `5` | Anti-spam delay seconds between requests |
| `DELETE_PASSWORD` | `782447` | Password for `/reset` command |
| `UPDATE_CHANNEL_USERNAME` | *(empty)* | Channel username for buttons (agar numeric ID use kar rahe ho) |
| `PORT` | `8080` | Health check server port |

### Channel ID Kaise Pata Kare

1. [@getidsbot](https://t.me/getidsbot) ya [@MissRose_bot](https://t.me/MissRose_bot) apne channel mein add karo
2. Woh exact numeric ID bata dega
3. Format: `-100XXXXXXXXXX`

> ⚠️ **Important:** `UPDATE_CHANNEL` mein **@username** format use karo numeric ID ki jagah.
> Example: `@raj_update_channel` ✅ | `-1003083333651` ❌

---

## 🚀 Setup Guide

### Step 1 — Telegram Setup

**a) API Credentials:**
1. [my.telegram.org](https://my.telegram.org) pe jao
2. "API Development Tools" pe click karo
3. `API_ID` aur `API_HASH` copy karo

**b) Bot Token:**
1. [@BotFather](https://t.me/BotFather) pe jao
2. `/newbot` command do
3. Bot name aur username set karo
4. Token copy karo

**c) DB Channel (Private Storage):**
1. Telegram mein ek **private channel** banao
2. Bot ko us channel mein add karo as **Admin**
3. Bot ko **Post Messages** permission do
4. Channel ID pata karo ([@getidsbot](https://t.me/getidsbot) se)
5. `DB_CHANNEL` mein daalo

**d) Update Channel (Public):**
1. Ek **public channel** banao (ya existing use karo)
2. Bot ko Admin banao → **Post Messages** permission do
3. Channel username `UPDATE_CHANNEL` mein daalo (e.g. `@raj_update_channel`)

**e) Admin ID:**
1. [@userinfobot](https://t.me/userinfobot) pe `/start` karo
2. Apna user ID copy karo
3. `ADMINS` mein daalo

### Step 2 — Install & Run

```bash
# Clone karo
git clone https://github.com/yourrepo/telegram-filestore-bot
cd telegram-filestore-bot

# ENV setup karo
cp .env.example .env
nano .env   # values fill karo

# Dependencies install karo
pip install -r requirements.txt

# Bot run karo
python bot.py
```

### Step 3 — Verify

Bot start hone pe logs mein yeh aana chahiye:
```
✅ MongoDB connected.
✅ Health check server on port 8080
🤖 Bot: @YourBot (ID: 123456789)
📦 DB_CHANNEL     : -100XXXXXXXXXX
📢 UPDATE_CHANNEL : @raj_update_channel
```

---

## ☁️ Deployment

### Koyeb (Recommended)

1. GitHub pe code push karo
2. [koyeb.com](https://koyeb.com) → New Service → GitHub
3. Repo select karo
4. **Service Type:** Worker (not Web)
5. Environment Variables add karo dashboard mein
6. Deploy!

> Koyeb mein `PORT` env var automatically set hoti hai.

### Render

1. [render.com](https://render.com) → New → Web Service
2. GitHub repo connect karo
3. **Runtime:** Docker
4. Environment pe `render.yaml` auto-detect hoga
5. Sab ENV vars manually add karo
6. Deploy!

### Railway

```bash
npm install -g @railway/cli
railway login
railway init
railway up
```

ENV vars Railway dashboard pe set karo.

### VPS (Ubuntu)

```bash
# Docker install karo
apt install docker.io docker-compose -y

# Code clone karo
git clone https://github.com/yourrepo/telegram-filestore-bot
cd telegram-filestore-bot
cp .env.example .env
nano .env

# Start karo
docker-compose up -d

# Logs dekho
docker-compose logs -f bot
```

---

## 🔧 Admin Commands

> Yeh commands sirf admin ke liye hain. Koi aur user use nahi kar sakta.

### File Management

| Command | Description |
|---|---|
| *(koi bhi file bhejo)* | File automatically DB channel mein save hogi aur Update Channel mein post hogi |

### Settings

| Command | Description |
|---|---|
| `/settings` | Inline admin control panel open karo |
| `/set_about <text>` | About text change karo (Markdown supported) |
| `/set_plans <text>` | Premium plans text change karo |

### User Management

| Command | Description |
|---|---|
| `/add_premium <user_id> <days>` | User ko premium do with expiry |
| `/remove_premium <user_id>` | User ka premium hato |
| `/ban <user_id>` | User ko ban karo |
| `/stats` | Bot statistics dekho |

### Content

| Command | Description |
|---|---|
| `/add_tutorial` | Kisi video ko reply karke tutorial set karo |
| `/broadcast` | Kisi message ko reply karke sab users ko bhejo |

### System

| Command | Description |
|---|---|
| `/reset <password>` | Poora database reset karo (confirmation maangega) |

#### `/add_premium` Example:
```
/add_premium 5804953849 30
```
User ID `5804953849` ko 30 din ka premium milega.

#### `/broadcast` Kaise Use Kare:
1. Pehle woh message type karo jo broadcast karna hai
2. Us message ko reply karo `/broadcast` se
3. Bot sab users ko woh message bhej dega

#### `/add_tutorial` Kaise Use Kare:
1. Bot mein tutorial video bhejo
2. Us video ko reply karo `/add_tutorial` se
3. Ab `/help` pe users ko woh video dikhega

#### `/reset` Kaise Use Kare:
```
/reset 782447
```
Bot confirmation buttons dikhayega:
- **✅ Haan, Reset Karo** — sab kuch delete
- **❌ Cancel** — kuch nahi hoga

---

## 👤 User Commands

| Command | Description |
|---|---|
| `/start` | Welcome screen with menu buttons |
| `/help` | Tutorial video + guide |
| *(file link click karna)* | `https://t.me/BotName?start=file_XXXXX` — file milegi |

### User Ko Kya Milta Hai `/start` Pe:

```
✨ Welcome, Username!

🤖 I am a Premium File Store Bot.
📦 I securely store and deliver files.

━━━━━━━━━━━━━━━━━━━━
🔗 Send me a file link to download
💎 Upgrade to Premium for extra perks
━━━━━━━━━━━━━━━━━━━━

[👑 Premium Plans]  [ℹ️ About]
[📢 Update Channel]
[🆘 Help & Tutorial]
```

---

## ⚙️ Settings Panel

`/settings` command se admin ko yeh panel milta hai:

```
⚙️ Admin Control Panel

👥 Total Users: 1500
🔗 Shortener: ON ✅
👑 Premium Mode: OFF ❌

[🟢 Shortener: ON]
[🔑 Shortener API: ...abc123]
[🔴 Premium Mode: OFF]
[📝 Edit About Text]
[💎 Edit Premium Plans]
[📊 Bot Statistics]
[❌ Close]
```

### Panel Se Kya Kya Kar Sakte Ho:

| Button | Kaam |
|---|---|
| **Shortener Toggle** | Link shortener globally ON/OFF |
| **Shortener API** | API key update karo bina restart ke |
| **Premium Mode** | ON karo → sirf premium users ko files milegi |
| **Edit About Text** | About page ka text change karo |
| **Edit Premium Plans** | Premium plans text change karo |
| **Bot Statistics** | Users count, settings status |

---

## 🔗 Shortener Logic

Shortener ON/OFF ka effect per user alag alag hai:

| User Type | Shortener ON | Shortener OFF |
|---|---|---|
| **Regular User** | Short link milta hai | Direct link milta hai |
| **Premium User** | Direct link milta hai (bypass) | Direct link milta hai |
| **Admin** | Direct link milta hai | Direct link milta hai |

### Supported Shorteners:

| Site | API Key Chahiye? | `SHORTENER_SITE` Value |
|---|---|---|
| shrtco.de (default) | ❌ Nahi | `api.shrtco.de` |
| tinyurl.com | ✅ Haan | `tinyurl.com/api` |
| Custom | ✅ Haan | Your domain |

### Shortener API Format:
```
https://SHORTENER_SITE/api?api=API_KEY&url=LONG_URL
```

---

## 👑 Premium System

### Premium Add Karo:
```
/add_premium 5804953849 30
```

### Premium Remove Karo:
```
/remove_premium 5804953849
```

### Premium Users Ko Kya Milta Hai:
- ✅ Shortener bypass — hamesha direct link
- ✅ Force subscribe bypass — channel join required nahi
- ✅ Premium mode mein bhi files milti hain
- ✅ Anti-spam bypass nahi (yeh sabke liye same hai)

### Premium Expiry:
Bot automatically premium check karta hai — expiry ke baad user regular ho jaata hai, manually remove nahi karna padta.

---

## 🔄 Reset System

### `/reset` Command:

```
/reset 782447
```

**Confirmation screen:**
```
🚨 ARE YOU SURE?

Yeh action UNDO nahi hoga!

Poora database wipe ho jaega.
Files, Users, Premium, Settings
sab permanently delete hoga.

[✅ Haan, Reset Karo]  [❌ Cancel]
```

**Reset ke baad:**
```
✅ FULL RESET COMPLETE!

🗑 Files deleted: 150
👥 Users deleted: 5200
👑 Premium deleted: 12
⚙️ Settings deleted: 8

Bot fresh install jaisa ho gaya.
```

### Password Change Kaise Kare:
`DELETE_PASSWORD` ENV var update karo:
```
DELETE_PASSWORD=YourNewPassword
```

---

## 🔒 Security Features

### Force Subscribe:
- User ko pehle Update Channel join karna hoga
- Join kiye bina file nahi milegi
- Premium users aur admins bypass kar sakte hain

### Anti-Spam:
- Har user ke requests ke beech minimum delay
- Default: 5 seconds
- `REQUEST_DELAY` ENV se change karo

### Admin-Only Upload:
- Sirf `ADMINS` list mein listed user IDs hi files upload kar sakte hain
- Non-admin file bhejega to "Unauthorized" message milega

### Settings Security (Double Lock):
- `/settings` command → Pyrogram filter level pe block
- Sab admin callbacks `adm_` prefix ke saath
- `@admin_only` decorator — defence in depth

### Banned Users:
- Banned users ko koi bhi feature kaam nahi karega
- Ban permanent hai jab tak manually remove na karo

---

## 🎬 Animations

### Startup Animation (`/start` pe):
```
⚡  →  💎  →  🛡️  →  💖
(0.5s delay each)
```

### File Search Animation (file link click karne pe):
```
🔍 Searching in Database...
▱▱▱▱▱▱▱▱▱▱  0%
▰▰▱▱▱▱▱▱▱▱  20%
▰▰▰▰▱▱▱▱▱▱  40%
▰▰▰▰▰▰▱▱▱▱  60%
▰▰▰▰▰▰▰▰▱▱  80%
▰▰▰▰▰▰▰▰▰▰  100%
```

### File Found Animation:
```
✅ File Found!
✅ File Found! 📂
✅ File Found! 📂✨
✅ File Found! 📂✨
⚡ Sending now...
```

### RAJ DEV Promo Flash:
- Jab bhi koi file link use karta hai
- **✨ RAJ DEV ✨** 1.5 seconds flash hokar gayab ho jaata hai
- Bilkul emoji animation ki tarah

---

## 🗄️ Database

### MongoDB (Primary):

Collections:

| Collection | Kya Store Hota Hai |
|---|---|
| `users` | User ID, name, username, join date, last active, request count, banned status |
| `files` | File ID, name, size, type, message_id, direct_url, short_url, download count |
| `premium` | User ID, expiry date, added by, added at |
| `settings` | Key-value pairs — shortener status, API key, about text, plans text, tutorial |

### NeonDB / PostgreSQL (Optional):

Same data PostgreSQL tables mein. Switch karne ke liye:

1. `NEON_URL` ENV var set karo
2. `database/__init__.py` mein change karo:
```python
# Yeh line change karo:
DB = MongoDB
# Isko yeh karo:
DB = NeonDB
```

Dono databases ka **interface exactly same** hai — baaki koi code change nahi karna.

---

## ❓ FAQ

**Q: Bot file upload kar raha hai lekin Update Channel mein post nahi ho raha?**

A: Bot ko Update Channel ka Admin banana padega:
1. Channel → Settings → Administrators
2. Bot add karo
3. "Post Messages" permission do
4. `UPDATE_CHANNEL` mein `@username` format use karo, numeric ID nahi

---

**Q: `Peer id invalid` error aa raha hai?**

A: `UPDATE_CHANNEL` mein numeric ID ki jagah `@username` use karo.
```
UPDATE_CHANNEL=@raj_update_channel  ✅
UPDATE_CHANNEL=-1003083333651       ❌
```

---

**Q: FloodWait error aa raha hai?**

A: Yeh Telegram ki rate limiting hai. Bot automatically wait karta hai aur retry karta hai. Container restart mat karo — isse flood timer aur badh jaata hai. Bas wait karo.

---

**Q: Database switch karna hai MongoDB se NeonDB pe?**

A: `database/__init__.py` mein ek line change karo:
```python
DB = NeonDB  # MongoDB ki jagah
```
Aur `NEON_URL` ENV var set karo.

---

**Q: Reset password change karna hai?**

A: `DELETE_PASSWORD` ENV var update karo. Default: `782447`.

---

**Q: Tutorial video kaise add kare?**

A:
1. Bot mein tutorial video bhejo
2. Us video ko long press karo → Reply
3. Type karo: `/add_tutorial`
4. Send karo

---

**Q: Premium user ko channel join karna padega?**

A: Nahi. Premium users force subscribe bypass kar sakte hain.

---

**Q: Bot ka session file kahan save hota hai?**

A: `FileStoreBot.session` file project root mein banti hai. Docker mein `sessions/` volume mount karo taaki restart pe session rehe.

---

## 📋 Requirements

```
pyrogram==2.0.106
TgCrypto==1.2.5
motor==3.3.2
pymongo==4.6.1
asyncpg==0.29.0
aiohttp==3.9.3
python-dotenv==1.0.1
```

Python 3.11+ required.

---

## 🔖 Credits

<div align="center">

<img src="https://i.ibb.co/wNm5kJn4/1765831046347-2.jpg" width="80" height="80" style="border-radius: 50%;" alt="RAJ DEV"/>

### Developed by RAJ DEV

**Telegram:** [@raj_dev_01](https://t.me/raj_dev_01)

*If this bot helped you, please give credit!*

```
🔖 Powered by RAJ DEV
```

</div>

---

<div align="center">

**⭐ Star this repo if you like it!**

Made with ❤️ by [RAJ DEV](https://t.me/raj_dev_01)

</div>
