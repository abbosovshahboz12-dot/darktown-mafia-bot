import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 8080))
WEBAPP_URL = os.getenv("WEBAPP_URL", "http://localhost:8080")
DATABASE_PATH = os.getenv("DATABASE_PATH", os.path.join(os.path.dirname(__file__), "database", "darktown.db"))
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN topilmadi! .env faylini tekshiring.")

# Game Event Stickers (try-except handled)
STICKER_NIGHT = os.getenv("STICKER_NIGHT", "CAACAgIAAxkBAAEEy9Fi_u_LAAF-gAFe_u9gAFe_u9gAAgEA") # sleeping/night
STICKER_DEATH = os.getenv("STICKER_DEATH", "CAACAgIAAxkBAAEEy9Ni_vApAAF-gAFe_u9gAFe_u9gAAgEA") # death/grave
STICKER_VICTORY = os.getenv("STICKER_VICTORY", "CAACAgIAAxkBAAEEy9Vi_vBpAAF-gAFe_u9gAFe_u9gAAgEA") # victory/celebration
