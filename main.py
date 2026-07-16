import asyncio
import logging
import os
import sys
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from datetime import datetime
from config import BOT_TOKEN, PORT, ADMIN_ID
from database import db

# Import handlers
from handlers import group_handlers, private_handlers, common

# Initialize logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

# Maintenance Mode Flag
MAINTENANCE_MODE = False

# Setup aiohttp web server handlers
async def get_profile_handler(request):
    try:
        user_id = int(request.query.get("user_id", 0))
        username = request.query.get("username")
        first_name = request.query.get("first_name")
        
        if not user_id:
            return web.json_response({"error": "user_id kiritilishi shart"}, status=400)
            
        if MAINTENANCE_MODE and user_id != ADMIN_ID:
            return web.json_response({"maintenance": True})
            
        user = await db.get_user(user_id, username, first_name)
        
        # Check if user is banned
        if user.get('banned', 0) == 1:
            return web.json_response({"banned": True})
            
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
            "active_games": active_games,
            "maintenance_enabled": MAINTENANCE_MODE
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

async def admin_broadcast_handler(request):
    try:
        data = await request.json()
        user_id = int(data.get("user_id", 0))
        text = data.get("text", "").strip()
        image_url = data.get("image_url", "").strip()
        
        if user_id != ADMIN_ID:
            return web.json_response({"error": "Siz admin emassiz!"}, status=403)
            
        if not text:
            return web.json_response({"error": "Matn kiritilishi shart!"}, status=400)
            
        bot = request.app['bot']
        user_ids = await db.get_all_user_ids()
        
        async def broadcast_task():
            success_count = 0
            fail_count = 0
            for uid in user_ids:
                try:
                    if image_url:
                        await bot.send_photo(uid, photo=image_url, caption=text, parse_mode="Markdown")
                    else:
                        await bot.send_message(uid, text, parse_mode="Markdown")
                    success_count += 1
                except Exception as ex:
                    logging.warning(f"Failed to send broadcast to {uid}: {ex}")
                    fail_count += 1
                await asyncio.sleep(0.05)
            logging.info(f"Broadcast completed. Success: {success_count}, Failures: {fail_count}")
            
        asyncio.create_task(broadcast_task())
        return web.json_response({"success": True, "message": "Xabar tarqatish fon rejimida boshlandi!"})
    except Exception as e:
        logging.error(f"Error in admin_broadcast_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def admin_ban_handler(request):
    try:
        data = await request.json()
        user_id = int(data.get("user_id", 0))
        target_id = int(data.get("target_id", 0))
        ban = bool(data.get("ban", False))
        
        if user_id != ADMIN_ID:
            return web.json_response({"error": "Siz admin emassiz!"}, status=403)
            
        if not target_id:
            return web.json_response({"error": "Nishon Telegram ID kiritilishi shart!"}, status=400)
            
        await db.ban_user(target_id, ban)
        action_word = "bloklandi" if ban else "blokdan chiqarildi"
        return web.json_response({"success": True, "message": f"Foydalanuvchi {target_id} muvaffaqiyatli {action_word}."})
    except Exception as e:
        logging.error(f"Error in admin_ban_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def admin_active_games_handler(request):
    try:
        user_id = int(request.query.get("user_id", 0))
        if user_id != ADMIN_ID:
            return web.json_response({"error": "Siz admin emassiz!"}, status=403)
            
        from game.manager import game_manager
        active_list = []
        seen_room_ids = set()
        
        for game in list(game_manager.games.values()):
            room_id = getattr(game, 'room_id', None)
            if room_id and room_id not in seen_room_ids:
                seen_room_ids.add(room_id)
                active_list.append({
                    "room_id": room_id,
                    "owner_id": game.chat_id,
                    "phase": game.phase,
                    "players_count": len(game.players)
                })
                
        return web.json_response({"games": active_list})
    except Exception as e:
        logging.error(f"Error in admin_active_games_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def admin_force_close_handler(request):
    try:
        data = await request.json()
        user_id = int(data.get("user_id", 0))
        room_id = data.get("room_id", "").strip()
        
        if user_id != ADMIN_ID:
            return web.json_response({"error": "Siz admin emassiz!"}, status=403)
            
        if not room_id:
            return web.json_response({"error": "room_id kiritilishi shart!"}, status=400)
            
        from game.manager import game_manager
        game = game_manager.games.get(room_id)
        bot = request.app['bot']
        
        if game:
            try:
                from game.loop import try_mute_chat, try_restrict_user
                await try_mute_chat(bot, game.chat_id, False)
                for p in game.players.values():
                    await try_restrict_user(bot, game.chat_id, p.user_id, False)
            except Exception as ex:
                logging.warning(f"Error releasing restrictions in force-close: {ex}")
                
            game_manager.remove_game(game.chat_id)
            
        import aiosqlite
        async with aiosqlite.connect(db.DB_PATH) as conn:
            await conn.execute("UPDATE rooms SET status = 'finished' WHERE room_id = ?", (room_id,))
            await conn.execute("DELETE FROM room_players WHERE room_id = ?", (room_id,))
            await conn.commit()
            
        return web.json_response({"success": True, "message": f"Xona {room_id} majburan yopildi."})
    except Exception as e:
        logging.error(f"Error in admin_force_close_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def room_force_close_handler(request):
    try:
        data = await request.json()
        user_id = int(data.get("user_id", 0))
        room_id = data.get("room_id", "").strip()
        
        if not user_id or not room_id:
            return web.json_response({"error": "user_id va room_id kiritilishi shart"}, status=400)
            
        import aiosqlite
        async with aiosqlite.connect(db.DB_PATH) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute("SELECT owner_id FROM rooms WHERE room_id = ?", (room_id,)) as cursor:
                room = await cursor.fetchone()
                
        if not room:
            return web.json_response({"error": "Xona topilmadi"}, status=404)
            
        # Only room owner (or bot admin) can force close
        if room['owner_id'] != user_id and user_id != ADMIN_ID:
            return web.json_response({"error": "Faqat xona egasi majburan yopa oladi!"}, status=403)
            
        from game.manager import game_manager
        game = game_manager.games.get(room_id)
        bot = request.app['bot']
        
        if game:
            try:
                from game.loop import try_mute_chat, try_restrict_user
                await try_mute_chat(bot, game.chat_id, False)
                for p in game.players.values():
                    await try_restrict_user(bot, game.chat_id, p.user_id, False)
            except Exception as ex:
                logging.warning(f"Error releasing restrictions in room force-close: {ex}")
                
            game_manager.remove_game(game.chat_id)
            
        async with aiosqlite.connect(db.DB_PATH) as conn:
            await conn.execute("UPDATE rooms SET status = 'finished' WHERE room_id = ?", (room_id,))
            await conn.execute("DELETE FROM room_players WHERE room_id = ?", (room_id,))
            await conn.commit()
            
        return web.json_response({"success": True, "message": "Xona muvaffaqiyatli yopildi."})
    except Exception as e:
        logging.error(f"Error in room_force_close_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def get_game_history_handler(request):
    try:
        user_id = int(request.query.get("user_id", 0))
        if not user_id:
            return web.json_response({"error": "user_id kiritilishi shart"}, status=400)
        history = await db.get_game_history(user_id)
        return web.json_response({"history": history})
    except Exception as e:
        logging.error(f"Error in get_game_history_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def get_quests_handler(request):
    try:
        user_id = int(request.query.get("user_id", 0))
        if not user_id:
            return web.json_response({"error": "user_id kiritilishi shart"}, status=400)
        quests = await db.get_daily_quests(user_id)
        return web.json_response({"quests": quests})
    except Exception as e:
        logging.error(f"Error in get_quests_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def get_achievements_handler(request):
    try:
        user_id = int(request.query.get("user_id", 0))
        if not user_id:
            return web.json_response({"error": "user_id kiritilishi shart"}, status=400)
        achievements = await db.get_user_achievements(user_id)
        return web.json_response({"achievements": achievements})
    except Exception as e:
        logging.error(f"Error in get_achievements_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def admin_users_search_handler(request):
    try:
        admin_id = int(request.query.get("admin_id", 0))
        if admin_id != ADMIN_ID:
            return web.json_response({"error": "Ruxsat yo'q!"}, status=403)
            
        search_query = request.query.get("q", "").strip()
        if not search_query:
            return web.json_response({"users": []})
            
        import aiosqlite
        async with aiosqlite.connect(db.DB_PATH) as conn:
            conn.row_factory = aiosqlite.Row
            sql = "SELECT * FROM users WHERE user_id = ? OR username LIKE ? OR first_name LIKE ? LIMIT 20"
            like_q = f"%{search_query}%"
            async with conn.execute(sql, (search_query, like_q, like_q)) as cursor:
                rows = await cursor.fetchall()
                return web.json_response({"users": [dict(r) for r in rows]})
    except Exception as e:
        logging.error(f"Error in admin_users_search_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def admin_users_edit_handler(request):
    try:
        data = await request.json()
        admin_id = int(data.get("admin_id", 0))
        if admin_id != ADMIN_ID:
            return web.json_response({"error": "Ruxsat yo'q!"}, status=403)
            
        target_id = int(data.get("user_id", 0))
        coins = data.get("coins")
        xp = data.get("xp")
        level = data.get("level")
        banned = data.get("banned")
        
        if not target_id:
            return web.json_response({"error": "user_id kiritilishi shart"}, status=400)
            
        import aiosqlite
        async with aiosqlite.connect(db.DB_PATH) as conn:
            if coins is not None:
                await conn.execute("UPDATE users SET coins = ? WHERE user_id = ?", (int(coins), target_id))
            if xp is not None:
                await conn.execute("UPDATE users SET xp = ? WHERE user_id = ?", (int(xp), target_id))
            if level is not None:
                await conn.execute("UPDATE users SET level = ? WHERE user_id = ?", (int(level), target_id))
            if banned is not None:
                val = 1 if banned else 0
                await conn.execute("UPDATE users SET banned = ? WHERE user_id = ?", (val, target_id))
            await conn.commit()
            
        return web.json_response({"success": True, "message": "Foydalanuvchi ma'lumotlari yangilandi."})
    except Exception as e:
        logging.error(f"Error in admin_users_edit_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def admin_rooms_live_handler(request):
    try:
        admin_id = int(request.query.get("admin_id", 0))
        if admin_id != ADMIN_ID:
            return web.json_response({"error": "Ruxsat yo'q!"}, status=403)
            
        from game.manager import game_manager
        live_games = []
        for chat_id, game in game_manager.games.items():
            if isinstance(chat_id, str): # Skip duplicate room_id keys
                continue
            live_games.append({
                "chat_id": chat_id,
                "room_id": getattr(game, 'room_id', None),
                "phase": game.phase,
                "players_count": len(game.players),
                "players": [p.name for p in game.players.values()]
            })
        return web.json_response({"rooms": live_games})
    except Exception as e:
        logging.error(f"Error in admin_rooms_live_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def admin_system_maintenance_handler(request):
    global MAINTENANCE_MODE
    try:
        data = await request.json()
        admin_id = int(data.get("admin_id", 0))
        if admin_id != ADMIN_ID:
            return web.json_response({"error": "Ruxsat yo'q!"}, status=403)
            
        enabled = bool(data.get("enabled", False))
        MAINTENANCE_MODE = enabled
        return web.json_response({"success": True, "maintenance": MAINTENANCE_MODE})
    except Exception as e:
        logging.error(f"Error in admin_system_maintenance_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def get_game_status_handler(request):
    try:
        user_id = int(request.query.get("user_id", 0))
        if not user_id:
            return web.json_response({"error": "user_id kiritilishi shart"}, status=400)
            
        from game.manager import game_manager
        game = game_manager.get_game_by_player(user_id)
        if not game:
            active_room = await db.get_active_room(user_id)
            if active_room:
                players = await db.get_room_players(active_room['room_id'])
                players_list = [{
                    "user_id": p['user_id'],
                    "name": p['first_name'],
                    "is_alive": True,
                    "role": None
                } for p in players]
                
                return web.json_response({
                    "inGame": True,
                    "phase": "lobby",
                    "room_id": active_room['room_id'],
                    "owner_id": active_room['owner_id'],
                    "isAlive": True,
                    "players": players_list,
                    "logs": ["Ishtirokchilar yig'ilmoqda..."]
                })
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
            "room_id": getattr(game, 'room_id', None),
            "owner_id": getattr(game, 'owner_id', None),
            "myRole": player.role,
            "isAlive": player.is_alive,
            "players": players_list,
            "event": game.event,
            "logs": getattr(game, 'logs', [])
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

# In-memory Ghost Chat store
ghost_chats = {}

async def set_language_handler(request):
    try:
        data = await request.json()
        user_id = int(data.get("user_id", 0))
        lang = data.get("language")
        if not user_id or lang not in ["uz", "ru", "en", "kz"]:
            return web.json_response({"error": "Noto'g'ri ma'lumotlar"}, status=400)
            
        await db.set_user_language(user_id, lang)
        return web.json_response({"success": True, "message": "Language updated!"})
    except Exception as e:
        logging.error(f"Error in set_language_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def daily_claim_handler(request):
    try:
        data = await request.json()
        user_id = int(data.get("user_id", 0))
        if not user_id:
            return web.json_response({"error": "user_id kiritilishi shart"}, status=400)
            
        success, coins_earned, err = await db.claim_daily_reward(user_id)
        if success:
            return web.json_response({"success": True, "coins": coins_earned, "message": "Kunlik bonus olindi!"})
        else:
            return web.json_response({"success": False, "error": err})
    except Exception as e:
        logging.error(f"Error in daily_claim_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def checkout_handler(request):
    try:
        data = await request.json()
        user_id = int(data.get("user_id", 0))
        package_key = data.get("package_key")
        
        packages = {
            "coins_100": {"name": "100 Dark Coins", "description": "100 ta tanga paketi", "price_stars": 50, "coins": 100},
            "coins_500": {"name": "500 Dark Coins", "description": "500 ta tanga paketi", "price_stars": 200, "coins": 500},
            "coins_1000": {"name": "1000 Dark Coins", "description": "1000 ta tanga paketi", "price_stars": 350, "coins": 1000}
        }
        
        if not user_id or package_key not in packages:
            return web.json_response({"error": "Noto'g'ri so'rov"}, status=400)
            
        pkg = packages[package_key]
        bot = request.app['bot']
        
        # Prices in Telegram Stars (currency = "XTR")
        prices = [types.LabeledPrice(label=pkg["name"], amount=pkg["price_stars"])]
        
        invoice_link = await bot.create_invoice_link(
            title=pkg["name"],
            description=pkg["description"],
            payload=package_key,
            provider_token="", # Stars
            currency="XTR",
            prices=prices
        )
        
        return web.json_response({"success": True, "invoice_link": invoice_link})
    except Exception as e:
        logging.error(f"Error in checkout_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def mock_payment_handler(request):
    user_id = request.query.get("user_id", "0")
    coins = request.query.get("coins", "100")
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Darktown Visa/PayPal Payment Simulation</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                background: #0d0e15;
                color: #e2e8f0;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
            }}
            .card-container {{
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border-radius: 16px;
                padding: 30px;
                width: 100%;
                max-width: 400px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
                text-align: center;
            }}
            h2 {{ color: #00f2fe; margin-bottom: 20px; }}
            .input-group {{
                margin-bottom: 15px;
                text-align: left;
            }}
            label {{
                display: block;
                font-size: 12px;
                color: #94a3b8;
                margin-bottom: 5px;
            }}
            input {{
                width: 100%;
                padding: 10px;
                background: rgba(0, 0, 0, 0.2);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                color: #fff;
                box-sizing: border-box;
            }}
            .pay-btn {{
                background: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%);
                color: #fff;
                border: none;
                padding: 12px 20px;
                font-size: 16px;
                border-radius: 8px;
                cursor: pointer;
                width: 100%;
                margin-top: 20px;
                font-weight: bold;
            }}
            .paypal-btn {{
                background: #ffc439;
                color: #012169;
                margin-top: 10px;
            }}
        </style>
    </head>
    <body>
        <div class="card-container">
            <h2>💳 Premium To'lov (Beta)</h2>
            <p style="font-size:14px;color:#ff5400;margin-bottom:20px;font-weight:bold;">
                ⚠️ Beta test rejimi: Ushbu to'lov turi hozircha ishlamaydi!
            </p>
            <p style="font-size:12px;color:#94a3b8;margin-bottom:20px;">
                Siz <strong>{coins} Dark Coins</strong> sotib olmoqchi bo'ldingiz.<br>
                Hozirda Visa/Mastercard va PayPal to'lovlari faqat namoyish uchun.
            </p>
            
            <div class="input-group">
                <label>Karta Raqami</label>
                <input type="text" placeholder="4000 1234 5678 9010" value="4000 1234 5678 9010" disabled>
            </div>
            <div style="display:flex;gap:10px;">
                <div class="input-group" style="flex:1;">
                    <label>Muddati</label>
                    <input type="text" placeholder="12/28" value="12/28" disabled>
                </div>
                <div class="input-group" style="flex:1;">
                    <label>CVV</label>
                    <input type="password" placeholder="***" value="123" disabled>
                </div>
            </div>
            
            <button class="pay-btn" onclick="submitPayment('visa')">Visa / Mastercard bilan to'lash</button>
            <button class="pay-btn paypal-btn" onclick="submitPayment('paypal')">PayPal orqali to'lash</button>
        </div>

        <script>
            function submitPayment(method) {{
                alert("⚠️ Ushbu to'lov turi vaqtincha ishlamaydi (BETA)!");
                if (window.Telegram && window.Telegram.WebApp) {{
                    window.Telegram.WebApp.close();
                }} else {{
                    window.close();
                }}
            }}
        </script>
    </body>
    </html>
    """
    return web.Response(text=html, content_type="text/html")

async def mock_payment_success_handler(request):
    try:
        data = await request.json()
        user_id = int(data.get("user_id", 0))
        coins = int(data.get("coins", 0))
        
        if not user_id or coins <= 0:
            return web.json_response({"error": "Noto'g'ri so'rov"}, status=400)
            
        await db.add_xp_and_coins(user_id, 0, coins)
        
        try:
            bot = request.app['bot']
            lang = await db.get_user_language(user_id)
            msg = f"💳 **Karta orqali xarid!** Hisobingizga **{coins}** Dark Coins qo'shildi."
            if lang == "ru":
                msg = f"💳 **Покупка по карте!** На ваш баланс зачислено **{coins}** Dark Coins."
            elif lang == "en":
                msg = f"💳 **Card Purchase!** **{coins}** Dark Coins have been added to your balance."
            elif lang == "kz":
                msg = f"💳 **Карта арқылы сатып алу!** Балансыңызға **{coins}** Dark Coins қосылды."
            await bot.send_message(user_id, msg, parse_mode="Markdown")
        except Exception:
            pass
            
        return web.json_response({"success": True})
    except Exception as e:
        logging.error(f"Error in mock_payment_success_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def ghost_chat_send_handler(request):
    try:
        data = await request.json()
        user_id = int(data.get("user_id", 0))
        text = data.get("text", "").strip()
        
        if not user_id or not text:
            return web.json_response({"error": "user_id va matn kiritilishi shart"}, status=400)
            
        from game.manager import game_manager
        game = game_manager.get_game_by_player(user_id)
        if not game:
            return web.json_response({"error": "Siz faol o'yinda emassiz!"}, status=400)
            
        player = game.players.get(user_id)
        if not player or player.is_alive:
            return web.json_response({"error": "Faqat vafot etgan (arvoxlar) chatga yozishi mumkin!"}, status=400)
            
        chat_id = game.chat_id
        if chat_id not in ghost_chats:
            ghost_chats[chat_id] = []
            
        msg = {
            "sender": player.name,
            "text": text,
            "timestamp": datetime.now().strftime("%H:%M")
        }
        ghost_chats[chat_id].append(msg)
        
        if len(ghost_chats[chat_id]) > 50:
            ghost_chats[chat_id].pop(0)
            
        return web.json_response({"success": True})
    except Exception as e:
        logging.error(f"Error in ghost_chat_send_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def ghost_chat_messages_handler(request):
    try:
        user_id = int(request.query.get("user_id", 0))
        if not user_id:
            return web.json_response({"error": "user_id kiritilishi shart"}, status=400)
            
        from game.manager import game_manager
        game = game_manager.get_game_by_player(user_id)
        if not game:
            return web.json_response({"messages": []})
            
        chat_id = game.chat_id
        msgs = ghost_chats.get(chat_id, [])
            
        return web.json_response({"messages": msgs})
    except Exception as e:
        logging.error(f"Error in ghost_chat_messages_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

# TMA Matchmaking & Party Handlers
async def create_room_handler(request):
    try:
        data = await request.json()
        user_id = int(data.get("user_id", 0))
        is_private = int(data.get("is_private", 0))
        pin_code = data.get("pin_code", "").strip()
        day_limit = int(data.get("day_limit", 60))
        night_limit = int(data.get("night_limit", 60))
        
        if not user_id:
            return web.json_response({"error": "user_id kiritilishi shart"}, status=400)
            
        active_room = await db.get_active_room(user_id)
        if active_room:
            return web.json_response({"error": "Siz allaqachon faol o'yin xonasidasiz!"}, status=400)
            
        party_row = await db.get_user_party(user_id)
        party_members = []
        if party_row and party_row['leader_id'] == user_id:
            party_members = await db.get_party_members(party_row['party_id'])
            for m in party_members:
                if m['user_id'] != user_id:
                    m_active = await db.get_active_room(m['user_id'])
                    if m_active:
                        return web.json_response({"error": f"Partiya a'zosi {m['first_name']} boshqa o'yin xonasida!"}, status=400)
                        
        import uuid
        room_id = str(uuid.uuid4().int)[:6]
        
        success = await db.create_room(room_id, user_id, is_private, pin_code, day_limit, night_limit)
        if success:
            if party_members:
                for m in party_members:
                    if m['user_id'] != user_id:
                        await db.join_room(room_id, m['user_id'])
            return web.json_response({"success": True, "room_id": room_id})
        else:
            return web.json_response({"error": "Xona yaratishda xatolik yuz berdi"}, status=500)
    except Exception as e:
        logging.error(f"Error in create_room_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def join_room_handler(request):
    try:
        data = await request.json()
        user_id = int(data.get("user_id", 0))
        room_id = data.get("room_id", "").strip()
        pin_code = data.get("pin_code", "").strip()
        
        if not user_id or not room_id:
            return web.json_response({"error": "user_id va room_id kiritilishi shart"}, status=400)
            
        async with aiosqlite.connect(db.DB_PATH) as sqlite_db:
            sqlite_db.row_factory = aiosqlite.Row
            async with sqlite_db.execute("SELECT * FROM rooms WHERE room_id = ?", (room_id,)) as cursor:
                room = await cursor.fetchone()
                
        if not room:
            return web.json_response({"error": "Bunday xona topilmadi!"}, status=404)
            
        if room['status'] != 'lobby':
            return web.json_response({"error": "O'yin allaqachon boshlangan!"}, status=400)
            
        if room['is_private'] and room['pin_code'] != pin_code:
            return web.json_response({"error": "PIN-kod noto'g'ri!"}, status=403)
            
        active_room = await db.get_active_room(user_id)
        if active_room and active_room['room_id'] == room_id:
            return web.json_response({"success": True})
            
        if active_room:
            return web.json_response({"error": "Siz allaqachon boshqa o'yin xonasidasiz!"}, status=400)
            
        party_row = await db.get_user_party(user_id)
        party_members = []
        if party_row and party_row['leader_id'] == user_id:
            party_members = await db.get_party_members(party_row['party_id'])
            for m in party_members:
                if m['user_id'] != user_id:
                    m_active = await db.get_active_room(m['user_id'])
                    if m_active:
                        return web.json_response({"error": f"Partiya a'zosi {m['first_name']} boshqa o'yin xonasida!"}, status=400)
                        
        success = await db.join_room(room_id, user_id)
        if success:
            if party_members:
                for m in party_members:
                    if m['user_id'] != user_id:
                        await db.join_room(room_id, m['user_id'])
            return web.json_response({"success": True})
        else:
            return web.json_response({"error": "Xonaga qo'shilishda xatolik yuz berdi"}, status=500)
    except Exception as e:
        logging.error(f"Error in join_room_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def leave_room_handler(request):
    try:
        data = await request.json()
        user_id = int(data.get("user_id", 0))
        room_id = data.get("room_id", "")
        
        if not user_id or not room_id:
            return web.json_response({"error": "user_id va room_id kiritilishi shart"}, status=400)
            
        success = await db.leave_room(room_id, user_id)
        if success:
            from game.manager import game_manager
            game = game_manager.games.get(room_id)
            if game:
                game.players.pop(user_id, None)
                if len(game.get_alive_players()) == 0:
                    game_manager.games.pop(room_id, None)
            return web.json_response({"success": True})
        else:
            return web.json_response({"error": "Xonadan chiqishda xatolik yuz berdi"}, status=500)
    except Exception as e:
        logging.error(f"Error in leave_room_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def list_rooms_handler(request):
    try:
        rooms = await db.get_open_rooms()
        return web.json_response({"rooms": rooms})
    except Exception as e:
        logging.error(f"Error in list_rooms_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def start_room_handler(request):
    try:
        data = await request.json()
        user_id = int(data.get("user_id", 0))
        room_id = data.get("room_id", "")
        
        if not user_id or not room_id:
            return web.json_response({"error": "user_id va room_id kiritilishi shart"}, status=400)
            
        async with aiosqlite.connect(db.DB_PATH) as sqlite_db:
            sqlite_db.row_factory = aiosqlite.Row
            async with sqlite_db.execute("SELECT * FROM rooms WHERE room_id = ?", (room_id,)) as cursor:
                room = await cursor.fetchone()
                
        if not room:
            return web.json_response({"error": "Bunday xona topilmadi!"}, status=404)
            
        if room['owner_id'] != user_id:
            return web.json_response({"error": "Faqat xona egasi o'yinni boshlay oladi!"}, status=403)
            
        players = await db.get_room_players(room_id)
        if len(players) < 5:
            return web.json_response({"error": "O'yinni boshlash uchun kamida 5 ta o'yinchi kerak!"}, status=400)
            
        from game.manager import game_manager
        from game.models import Game, Player
        from game.loop import start_game_loop
        
        game = Game(chat_id=room['owner_id'])
        game.room_id = room_id
        
        for p in players:
            player_obj = Player(user_id=p['user_id'], name=p['first_name'], username=p['username'])
            game.players[p['user_id']] = player_obj
            
        game_manager.games[room_id] = game
        game_manager.games[game.chat_id] = game
        
        await db.start_room_game(room_id)
        
        bot = request.app['bot']
        asyncio.create_task(start_game_loop(bot, game))
        
        return web.json_response({"success": True})
    except Exception as e:
        logging.error(f"Error in start_room_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def room_chat_send_handler(request):
    try:
        data = await request.json()
        user_id = int(data.get("user_id", 0))
        text = data.get("text", "").strip()
        
        if not user_id or not text:
            return web.json_response({"error": "user_id va text kiritilishi shart"}, status=400)
            
        from game.manager import game_manager
        game = game_manager.get_game_by_player(user_id)
        if not game:
            return web.json_response({"error": "Siz faol o'yinda emassiz!"}, status=400)
            
        player = game.players.get(user_id)
        if not player or not player.is_alive:
            return web.json_response({"error": "Faqat tirik o'yinchilar yozishi mumkin!"}, status=403)
            
        if not hasattr(game, "room_chat_messages"):
            game.room_chat_messages = []
            
        msg = {
            "sender": player.name,
            "sender_id": player.user_id,
            "text": text,
            "timestamp": datetime.now().strftime("%H:%M")
        }
        game.room_chat_messages.append(msg)
        if len(game.room_chat_messages) > 50:
            game.room_chat_messages.pop(0)
            
        return web.json_response({"success": True})
    except Exception as e:
        logging.error(f"Error in room_chat_send_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def room_chat_messages_handler(request):
    try:
        user_id = int(request.query.get("user_id", 0))
        from game.manager import game_manager
        game = game_manager.get_game_by_player(user_id)
        if not game or not hasattr(game, "room_chat_messages"):
            return web.json_response({"messages": []})
            
        return web.json_response({"messages": game.room_chat_messages})
    except Exception as e:
        logging.error(f"Error in room_chat_messages_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

# Party Handlers
async def party_create_handler(request):
    try:
        data = await request.json()
        user_id = int(data.get("user_id", 0))
        if not user_id:
            return web.json_response({"error": "user_id kiritilishi shart"}, status=400)
            
        party_id = f"party_{user_id}"
        success = await db.create_party(party_id, user_id)
        if success:
            return web.json_response({"success": True, "party_id": party_id})
        else:
            return web.json_response({"error": "Partiya yaratishda xatolik"}, status=500)
    except Exception as e:
        logging.error(f"Error in party_create_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def party_join_handler(request):
    try:
        data = await request.json()
        user_id = int(data.get("user_id", 0))
        party_id = data.get("party_id", "").strip()
        
        if not user_id or not party_id:
            return web.json_response({"error": "user_id va party_id kiritilishi shart"}, status=400)
            
        try:
            leader_id = int(party_id.replace("party_", ""))
        except ValueError:
            return web.json_response({"error": "Noto'g'ri partiya ID"}, status=400)
            
        success = await db.add_to_party(party_id, leader_id, user_id)
        if success:
            return web.json_response({"success": True})
        else:
            return web.json_response({"error": "Partiyaga qo'shilishda xatolik"}, status=500)
    except Exception as e:
        logging.error(f"Error in party_join_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def party_status_handler(request):
    try:
        user_id = int(request.query.get("user_id", 0))
        if not user_id:
            return web.json_response({"error": "user_id kiritilishi shart"}, status=400)
            
        party_row = await db.get_user_party(user_id)
        if not party_row:
            return web.json_response({"inParty": False})
            
        party_id = party_row['party_id']
        members = await db.get_party_members(party_id)
        return web.json_response({
            "inParty": True,
            "party_id": party_id,
            "isLeader": party_row['leader_id'] == user_id,
            "leader_id": party_row['leader_id'],
            "members": members
        })
    except Exception as e:
        logging.error(f"Error in party_status_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def party_leave_handler(request):
    try:
        data = await request.json()
        user_id = int(data.get("user_id", 0))
        party_id = data.get("party_id", "")
        
        if not user_id or not party_id:
            return web.json_response({"error": "user_id va party_id kiritilishi shart"}, status=400)
            
        success = await db.remove_from_party(party_id, user_id)
        if success:
            return web.json_response({"success": True})
        else:
            return web.json_response({"error": "Partiyadan chiqishda xatolik"}, status=500)
    except Exception as e:
        logging.error(f"Error in party_leave_handler: {e}")
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
    app.router.add_post("/api/admin/broadcast", admin_broadcast_handler)
    app.router.add_post("/api/admin/ban", admin_ban_handler)
    app.router.add_get("/api/admin/active-games", admin_active_games_handler)
    app.router.add_post("/api/admin/force-close", admin_force_close_handler)
    app.router.add_get("/api/game/status", get_game_status_handler)
    app.router.add_get("/api/game/history", get_game_history_handler)
    app.router.add_get("/api/quests", get_quests_handler)
    app.router.add_get("/api/achievements", get_achievements_handler)
    app.router.add_get("/api/admin/users/search", admin_users_search_handler)
    app.router.add_post("/api/admin/users/edit", admin_users_edit_handler)
    app.router.add_get("/api/admin/rooms/live", admin_rooms_live_handler)
    app.router.add_post("/api/admin/system/maintenance", admin_system_maintenance_handler)
    app.router.add_post("/api/game/action", post_game_action_handler)
    app.router.add_post("/api/game/vote", post_game_vote_handler)
    app.router.add_post("/api/profile/language", set_language_handler)
    app.router.add_post("/api/daily-claim", daily_claim_handler)
    app.router.add_post("/api/payment/checkout", checkout_handler)
    app.router.add_get("/payment/mock", mock_payment_handler)
    app.router.add_post("/api/payment/mock-success", mock_payment_success_handler)
    app.router.add_post("/api/game/ghost-chat/send", ghost_chat_send_handler)
    app.router.add_get("/api/game/ghost-chat/messages", ghost_chat_messages_handler)
    
    # TMA Matchmaking & Party Routing
    app.router.add_post("/api/rooms/create", create_room_handler)
    app.router.add_post("/api/rooms/join", join_room_handler)
    app.router.add_post("/api/rooms/leave", leave_room_handler)
    app.router.add_post("/api/rooms/force-close", room_force_close_handler)
    app.router.add_get("/api/rooms/list", list_rooms_handler)
    app.router.add_post("/api/rooms/start", start_room_handler)
    app.router.add_post("/api/rooms/chat/send", room_chat_send_handler)
    app.router.add_get("/api/rooms/chat/messages", room_chat_messages_handler)
    app.router.add_post("/api/party/create", party_create_handler)
    app.router.add_post("/api/party/join", party_join_handler)
    app.router.add_get("/api/party/status", party_status_handler)
    app.router.add_post("/api/party/leave", party_leave_handler)
    
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
