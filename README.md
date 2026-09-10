# DarkTown Mafia Engine & Telegram Mini App

[1]r(#installation) ![License](https://img.shields.io/badge/License-Proprietary-blue.svg) ![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue.svg) ![Framework](https://img.shields.io/badge/Framework-aiogram%203.x-green.svg)

> High-performance, asynchronous online Mafia gaming engine engineered specifically for Telegram Bot & WebApp ecosystems.

Developed by **DarkTown Interactive Studios (c) 2026**. All rights reserved.

---

## ǜ Architecture Overview

DarkTown operates on a hybrid architecture combining a high-throughput Telegram Bot Gateway with a modern asynchronous WebApp client:

- **Core Engine:** Built on `iogram 3.x`with asynchronous event dispatching.
- **REST & Socket Gateway:** `aiohttp` web server handling secure WebApp session authorization (`HMAC-SHA256` telegram auth validation).
- **Matchmaking Subsystem:** CS2-style auto-matching queue and isolated PIN-protected private lobbies.
- **Storage Subsystem:** High-concurrency WAL-mode SQLite database with automated cloud backup snapshots streamed to Telegram storage archives.
- **Client Frontend:** Vanilla ES6+ WebApp with GPU-accelerated CSS animations and multi-language localization (`uz`, `ru`, `en`, `kz`).

---

## 🥀= Quick Start

### Prerequisites
- Python 3.11+
- Telegram Bot Token via [@BotFather](https://t.me/BotFather)

### Installation

```bash
git clone https://github.com/abbosovshahboz12-dot/darktown-mafia-bot.git
cd darktown-mafia-bot
pip install -r requirements.txt
�`

### Environment Configuration
Create a `.env` file in the root directory:
```env
BOT_TOKEN=your_bot_token_here
ADMIN_ID=your_telegram_id_here
PORT=8080
WEBAPP_URL=https://your-domain.onrender.com
REQUIRED_CHANNEL=@DarkTownuz
```

### Run Server
```bash
python main.py
```

---

## 📦 License & Commercial Rights
Copyright (c) 2026 DarkTown Interactive Studios.
Proprietary Commercial License. Unauthorized copying or redistribution is strictly prohibited.
