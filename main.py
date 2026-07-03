import asyncio
import logging
import os
import sys
from aiohttp import web
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN, PORT, ADMIN_ID
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
        
        is_admin = (user_id == ADMIN_ID)
        
        return web.json_response({
            "user": user,
            "stats": stats,
            "inventory": inventory,
            "isAdmin": is_admin
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

async def admin_stats_handler(request):
    try:
        admin_id = int(request.query.get("admin_id", 0))
        if admin_id != ADMIN_ID:
            return web.json_response({"error": "Ruxsat etilmagan"}, status=403)
            
        stats = await db.get_global_stats()
        from game.manager import game_manager
        active_games = len(game_manager.games)
        
        return web.json_response({
            "success": True,
            "total_users": stats["total_users"],
            "total_plays": stats["total_plays"],
            "active_games": active_games
        })
    except Exception as e:
        logging.error(f"Error in admin_stats_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def admin_give_handler(request):
    try:
        data = await request.json()
        admin_id = int(data.get("admin_id", 0))
        if admin_id != ADMIN_ID:
            return web.json_response({"error": "Ruxsat etilmagan"}, status=403)
            
        target_uid = int(data.get("target_id", 0))
        coins = int(data.get("coins", 0))
        xp = int(data.get("xp", 0))
        
        if not target_uid:
            return web.json_response({"error": "target_id kiritilishi shart"}, status=400)
            
        await db.add_xp_and_coins(target_uid, xp, coins)
        return web.json_response({"success": True, "message": "Muvaffaqiyatli to'ldirildi!"})
    except Exception as e:
        logging.error(f"Error in admin_give_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def admin_give_handler(request):
    try:
        data = await request.json()
        admin_id = int(data.get("admin_id", 0))
        if admin_id != ADMIN_ID:
            return web.json_response({"error": "Ruxsat etilmagan"}, status=403)
            
        target_uid = int(data.get("target_id", 0))
        coins = int(data.get("coins", 0))
        xp = int(data.get("xp", 0))
        
        if not target_uid:
            return web.json_response({"error": "target_id kiritilishi shart"}, status=400)
            
        await db.add_xp_and_coins(target_uid, xp, coins)
        return web.json_response({"success": True, "message": "Muvaffaqiyatli to'ldirildi!"})
    except Exception as e:
        logging.error(f"Error in admin_give_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def get_game_status_handler(request):
    try:
        user_id = int(request.query.get("user_id", 0))
        if not user_id:
            return web.json_response({"error": "user_id kiritilishi shart"}, status=400)
            
        from game.manager import game_manager
        game = game_manager.get_game_by_player(user_id)
        if not game:
            return web.json_response({"inGame": False})
            
        player = game.players.get(user_id)
        if not player:
            return web.json_response({"inGame": False})
            
        # Compile players list
        players_list = []
        from game.loop import ROLE_EMOJIS
        for p in game.players.values():
            is_mafia_team = player.role in ["Mafia", "Don"] and p.role in ["Mafia", "Don"]
            show_role = not p.is_alive or p.user_id == user_id or is_mafia_team
            players_list.append({
                "user_id": p.user_id,
                "name": p.name,
                "is_alive": p.is_alive,
                "role": p.role if show_role else None
            })
            
        return web.json_response({
            "inGame": True,
            "phase": game.phase,
            "chat_id": game.chat_id,
            "myRole": player.role,
            "isAlive": player.is_alive,
            "players": players_list,
            "event": game.event
        })
    except Exception as e:
        logging.error(f"Error in get_game_status_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def post_game_action_handler(request):
    try:
        data = await request.json()
        user_id = int(data.get("user_id", 0))
        target_id = int(data.get("target_id", 0))
        action_type = data.get("action_type")
        
        from game.manager import game_manager
        game = game_manager.get_game_by_player(user_id)
        if not game or game.phase != "night":
            return web.json_response({"error": "Hozir tungi faza emas!"}, status=400)
            
        player = game.players.get(user_id)
        if not player or not player.is_alive:
            return web.json_response({"error": "Siz tirik emassiz!"}, status=400)
            
        target_player = game.players.get(target_id)
        if not target_player or not target_player.is_alive:
            return web.json_response({"error": "Tanlangan o'yinchi tirik emas!"}, status=400)
            
        if action_type == "mafia":
            if player.role not in ["Mafia", "Don"]:
                return web.json_response({"error": "Siz mafiya emassiz!"}, status=400)
            game.night_actions["mafia"][user_id] = target_id
        elif action_type == "don":
            if player.role != "Don":
                return web.json_response({"error": "Siz Don emassiz!"}, status=400)
            game.night_actions["don"] = target_id
        elif action_type == "det_check":
            if player.role != "Detective":
                return web.json_response({"error": "Siz Komissar emassiz!"}, status=400)
            game.night_actions["detective_check"] = target_id
        elif action_type == "det_shoot":
            if player.role != "Detective":
                return web.json_response({"error": "Siz Komissar emassiz!"}, status=400)
            game.night_actions["detective_shoot"] = target_id
        elif action_type == "doctor":
            if player.role != "Doctor":
                return web.json_response({"error": "Siz Shifokor emassiz!"}, status=400)
            if game.last_doctor_target == target_id and not (game.event and game.event["key"] == "epidemic"):
                return web.json_response({"error": "Ketma-ket bir kishini davolay olmaysiz!"}, status=400)
            game.night_actions["doctor"] = target_id
        elif action_type == "bodyguard":
            if player.role != "Bodyguard":
                return web.json_response({"error": "Siz Tansoqchi emassiz!"}, status=400)
            if game.last_bodyguard_target == target_id:
                return web.json_response({"error": "Ketma-ket bir kishini himoya qila olmaysiz!"}, status=400)
            game.night_actions["bodyguard"] = target_id
        elif action_type == "courtesan":
            if player.role != "Courtesan":
                return web.json_response({"error": "Siz Kutizanka emassiz!"}, status=400)
            game.night_actions["courtesan"] = target_id
        elif action_type == "maniac":
            if player.role != "Maniac":
                return web.json_response({"error": "Siz Telba emassiz!"}, status=400)
            game.night_actions["maniac"] = target_id
        else:
            return web.json_response({"error": "Noto'g'ri harakat turi"}, status=400)
            
        return web.json_response({"success": True, "message": "Tanlov qabul qilindi!"})
    except Exception as e:
        logging.error(f"Error in post_game_action_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def post_game_vote_handler(request):
    try:
        data = await request.json()
        user_id = int(data.get("user_id", 0))
        target_id = data.get("target_id")
        
        from game.manager import game_manager
        game = game_manager.get_game_by_player(user_id)
        if not game or game.phase != "voting":
            return web.json_response({"error": "Hozir ovoz berish bosqichi emas!"}, status=400)
            
        player = game.players.get(user_id)
        if not player or not player.is_alive:
            return web.json_response({"error": "Siz tirik emassiz!"}, status=400)
            
        if target_id == "skip":
            game.votes[user_id] = "skip"
        else:
            target_id = int(target_id)
            target_player = game.players.get(target_id)
            if not target_player or not target_player.is_alive:
                return web.json_response({"error": "Tanlangan o'yinchi tirik emas!"}, status=400)
            game.votes[user_id] = target_id
            
        bot = request.app.get('bot')
        if bot:
            try:
                alive = game.get_alive_players()
                vote_counts = {}
                for target in game.votes.values():
                    vote_counts[target] = vote_counts.get(target, 0) + 1
                    
                text = "🗳️ **Ovoz berish boshlandi!**\nKimni dorda osmoqchisiz? Quyidagi tugmalardan birini tanlang.\n\n"
                for p in alive:
                    count = vote_counts.get(p.user_id, 0)
                    votes_box = "🗳️" * count if count > 0 else ""
                    text += f"- **{p.name}**: {votes_box} ({count})\n"
                    
                skip_count = vote_counts.get("skip", 0)
                skip_box = "🗳️" * skip_count if skip_count > 0 else ""
                text += f"- Hech kimga: {skip_box} ({skip_count})\n\n"
                text += f"Ovoz berganlar: {len(game.votes)} / {len(alive)}"
                
                from aiogram.utils.keyboard import InlineKeyboardBuilder
                from aiogram import types
                kb = InlineKeyboardBuilder()
                for p in alive:
                    kb.add(types.InlineKeyboardButton(text=p.name, callback_data=f"vote_{p.user_id}"))
                kb.add(types.InlineKeyboardButton(text="⏩ Hech kimga", callback_data="vote_skip"))
                kb.adjust(2)
                
                await bot.edit_message_text(
                    chat_id=game.chat_id,
                    message_id=game.vote_message_id,
                    text=text,
                    reply_markup=kb.as_markup(),
                    parse_mode="Markdown"
                )
            except Exception as e:
                logging.error(f"Error updating live voting from web: {e}")
                
        return web.json_response({"success": True, "message": "Ovozingiz qabul qilindi!"})
    except Exception as e:
        logging.error(f"Error in post_game_vote_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

# Setup Web Server Routing
def setup_web_server():
    app = web.Application()
    
    # API endpoints
    app.router.add_get("/api/profile", get_profile_handler)
    app.router.add_post("/api/buy", buy_handler)
    app.router.add_post("/api/activate", activate_handler)
    app.router.add_get("/api/leaderboard", get_leaderboard_handler)
    app.router.add_get("/api/admin/stats", admin_stats_handler)
    app.router.add_post("/api/admin/give", admin_give_handler)
    app.router.add_get("/api/game/status", get_game_status_handler)
    app.router.add_post("/api/game/action", post_game_action_handler)
    app.router.add_post("/api/game/vote", post_game_vote_handler)
    
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
    web_app['bot'] = bot
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
