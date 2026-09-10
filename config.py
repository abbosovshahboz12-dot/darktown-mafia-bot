"""
Project:       DarkTown Mafia Engine
Module:        Configuration & FeatureFlags
Author:        DarkTown Interactive Studios
Copyright:     (c) 2026 DarkTown Interactive. All rights reserved.
License:       Proprietary
"""

import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 8080))
WEBAPP_URL = os.getenv("WEBAPP_URL") or os.getenv("RENDER_EXTERNAL_URL") or "https://darktown-mafia-bot.onrender.com"
if not WEBAPP_URL.startswith("https://"):
    WEBAPP_URL = "https://darktown-mafia-bot.onrender.com"
DATABASE_PATH = os.getenv("DATABASE_PATH", os.path.join(os.path.dirname(__file__), "database", "darktown.db"))
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL", "@DarkTownuz")

# ==========================================
# 🚀 FEATURE FLAGS (MVP / KELAJAKDAGI BOSQICHLAR)
# ==========================================
# 1-bosqichda (MVP) faqat asosiy bot, yengil do'kon va referral ishlaydi.
# Kengayish davrida quyidagilarni True qilib bitta-bitta yoqish mumkin:
FEATURE_WEBAPP = os.getenv("FEATURE_WEBAPP", "True").lower() in ("true", "1", "yes")
FEATURE_SHOP = os.getenv("FEATURE_SHOP", "True").lower() in ("true", "1", "yes")
FEATURE_REFERRAL = os.getenv("FEATURE_REFERRAL", "True").lower() in ("true", "1", "yes")
FEATURE_LEADERBOARD = os.getenv("FEATURE_LEADERBOARD", "True").lower() in ("true", "1", "yes")
FEATURE_CLANS = os.getenv("FEATURE_CLANS", "False").lower() in ("true", "1", "yes")
FEATURE_BATTLEPASS = os.getenv("FEATURE_BATTLEPASS", "False").lower() in ("true", "1", "yes")
FEATURE_CASINO = os.getenv("FEATURE_CASINO", "False").lower() in ("true", "1", "yes")
FEATURE_VIP = os.getenv("FEATURE_VIP", "True").lower() in ("true", "1", "yes")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN topilmadi! .env faylini tekshiring.")

