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

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN topilmadi! .env faylini tekshiring.")
