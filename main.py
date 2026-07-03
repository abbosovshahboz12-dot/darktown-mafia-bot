import asyncio
import logging
import os
import sys
from aiohttp import web
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN, PORT
from database import db

# Import handlers
from handlers import group_handlers, private_handlers, common

# Initialize logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

# Setup aiohttp web server handlers
async def get_profile_handler(request):
    try:
        user_id = int(request.query.get("user_id", 0))
        if not user_id:
            return web.json_response({"error": "user_id kiritilishi shart"}, status=400)
            
        user = await db.get_user(user_id)
        stats = await db.get_user_stats(user_id)
        inventory = await db.get_inventory(user_id)
        
        return web.json_response({
            "user": user,
            "stats": stats,
            "inventory": inventory
        })
    except Exception as e:
        logging.error(f"Error in get_profile_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def buy_handler(request):
    try:
        data = await request.json()
        user_id = int(data.get("user_id", 0))
        item_key = data.get("item_key")
        
        shop_items = {
            "shield": {"name": "XP Qalqoni", "cost": 150},
            "booster_mafia": {"name": "Mafiya Booster", "cost": 250},
            "booster_detective": {"name": "Komissar Booster", "cost": 250},
            "booster_doctor": {"name": "Shifokor Booster", "cost": 200},
            "booster_maniac": {"name": "Telba Booster", "cost": 300}
        }
        
        if not user_id or item_key not in shop_items:
            return web.json_response({"error": "Noto'g'ri so'rov ma'lumotlari"}, status=400)
            
        cost = shop_items[item_key]["cost"]
        success, msg = await db.buy_item(user_id, item_key, cost)
        
        if success:
            return web.json_response({"success": True, "message": msg})
        else:
            return web.json_response({"success": False, "error": msg}, status=400)
    except Exception as e:
        logging.error(f"Error in buy_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def activate_handler(request):
    try:
        data = await request.json()
        user_id = int(data.get("user_id", 0))
        item_key = data.get("item_key")
        
        if not user_id or item_key != "shield":
            return web.json_response({"error": "Noto'g'ri so'rov"}, status=400)
            
        inventory = await db.get_inventory(user_id)
        if inventory.get("shield", 0) <= 0:
            return web.json_response({"error": "Sizda qalqon yo'q!"}, status=400)
            
        user = await db.get_user(user_id)
        if user.get("shield_active", 0) == 1:
            return web.json_response({"error": "Qalqon allaqachon faol!"}, status=400)
            
        used = await db.use_item(user_id, "shield")
        if used:
            await db.set_shield(user_id, True)
            return web.json_response({"success": True, "message": "Qalqon faollashtirildi!"})
            
        return web.json_response({"error": "Xatolik yuz berdi"}, status=400)
    except Exception as e:
        logging.error(f"Error in activate_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def get_leaderboard_handler(request):
    try:
        leaders = await db.get_leaderboard(10)
        return web.json_response({"leaderboard": leaders})
    except Exception as e:
        logging.error(f"Error in get_leaderboard_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def index_handler(request):
    webapp_dir = os.path.join(os.path.dirname(__file__), "webapp")
    return web.FileResponse(os.path.join(webapp_dir, "index.html"))

# Setup Web Server Routing
def setup_web_server():
    app = web.Application()
    
    # API endpoints
    app.router.add_get("/api/profile", get_profile_handler)
    app.router.add_post("/api/buy", buy_handler)
    app.router.add_post("/api/activate", activate_handler)
    app.router.add_get("/api/leaderboard", get_leaderboard_handler)
    
    # Frontend static files and index
    webapp_dir = os.path.join(os.path.dirname(__file__), "webapp")
    app.router.add_static("/static/", webapp_dir, name="static")
    app.router.add_get("/", index_handler)
    
    return app

async def main():
    # 1. Initialize SQLite Database
    await db.init_db()
    logging.info("Database initialized successfully.")
    
    # 2. Setup Telegram Bot
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    # Register routers
    dp.include_router(common.router)
    dp.include_router(group_handlers.router)
    dp.include_router(private_handlers.router)
    
    # Delete webhook to ensure polling works
    await bot.delete_webhook(drop_pending_updates=True)
    
    # 3. Setup Web Server
    web_app = setup_web_server()
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logging.info(f"Web app server started on port {PORT}")
    
    # 4. Start Bot Polling
    logging.info("Telegram Bot polling started...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await runner.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped.")
