import asyncio
import logging
import os
import sys
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from datetime import datetime
from config import BOT_TOKEN, PORT, ADMIN_ID, WEBAPP_URL
from database import db

# Import handlers
from handlers import group_handlers, private_handlers, common

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable

class BanCheckMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = None
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user

        if user:
            if await db.is_user_banned(user.id):
                if isinstance(event, Message):
                    if event.chat.type == "private":
                        await event.answer("⚠️ Siz botda bloklangansiz! Xizmatlardan foydalana olmaysiz.")
                elif isinstance(event, CallbackQuery):
                    await event.answer("⚠️ Siz bloklangansiz!", show_alert=True)
                return
        return await handler(event, data)


# Initialize logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

# Maintenance Mode Flag
MAINTENANCE_MODE = False

import hmac
import hashlib
import time
import json
from urllib.parse import parse_qsl

def verify_telegram_webapp_data(init_data_str: str, bot_token: str) -> dict | None:
    if not init_data_str or not bot_token:
        return None
    try:
        parsed_data = dict(parse_qsl(init_data_str, keep_blank_values=True))
        if "hash" not in parsed_data:
            return None
        
        received_hash = parsed_data.pop("hash")
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed_data.items()))
        secret_key = hmac.new(b"WebAppData", bot_token.encode('utf-8'), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode('utf-8'), hashlib.sha256).hexdigest()
        
        if not hmac.compare_digest(calculated_hash.lower(), received_hash.lower()):
            return None
            
        auth_date = int(parsed_data.get("auth_date", 0))
        if auth_date > 0 and (time.time() - auth_date > 86400):
            return None
            
        user_json = parsed_data.get("user")
        if user_json:
            return json.loads(user_json)
        return {}
    except Exception as e:
        logging.warning(f"WebApp auth verification error: {e}")
        return None

async def authenticate_webapp_request(request, requested_user_id: int = 0, require_admin: bool = False):
    init_data = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        init_data = auth_header[7:].strip()
    elif "X-Telegram-Init-Data" in request.headers:
        init_data = request.headers["X-Telegram-Init-Data"].strip()
        
    auth_user = None
    if init_data:
        auth_user = verify_telegram_webapp_data(init_data, BOT_TOKEN)

    auth_user_id = auth_user.get("id") if (auth_user and isinstance(auth_user, dict)) else None

    if auth_user_id is not None:
        if require_admin and auth_user_id != ADMIN_ID:
            return False, auth_user_id, web.json_response({"error": "Siz admin emassiz!"}, status=403)
        if requested_user_id and requested_user_id != auth_user_id and auth_user_id != ADMIN_ID:
            return False, auth_user_id, web.json_response({"error": "Ruxsat etilmagan foydalanuvchi ma'lumotlari"}, status=403)
        return True, auth_user_id, None

    if require_admin:
        if requested_user_id != ADMIN_ID:
            return False, 0, web.json_response({"error": "Ruxsat etilmagan (initData kerak)"}, status=403)

    return True, requested_user_id, None

# Setup aiohttp web server handlers
async def get_profile_handler(request):
    try:
        user_id = int(request.query.get("user_id", 0))
        username = request.query.get("username")
        first_name = request.query.get("first_name")
        
        if not user_id:
            return web.json_response({"error": "user_id kiritilishi shart"}, status=400)
            
        is_auth, auth_uid, err_resp = await authenticate_webapp_request(request, requested_user_id=user_id)
        if not is_auth:
            return err_resp
            
        if MAINTENANCE_MODE and user_id != ADMIN_ID:
            return web.json_response({"maintenance": True})
            
        user = await db.get_user(user_id, username, first_name)
        
        # Check if user is banned
        if user.get('banned', 0) == 1:
            return web.json_response({"banned": True})
            
        stats = await db.get_user_stats(user_id)
        inventory = await db.get_inventory(user_id)
        achievements = await db.get_user_achievements(user_id)
        
        is_admin = (user_id == ADMIN_ID)
        
        return web.json_response({
            "user": user,
            "stats": stats,
            "inventory": inventory,
            "achievements": achievements,
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
        
        is_auth, auth_uid, err_resp = await authenticate_webapp_request(request, requested_user_id=user_id)
        if not is_auth:
            return err_resp
        
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
        
        is_auth, auth_uid, err_resp = await authenticate_webapp_request(request, requested_user_id=user_id)
        if not is_auth:
            return err_resp
        
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
        is_auth, auth_uid, err_resp = await authenticate_webapp_request(request, requested_user_id=admin_id, require_admin=True)
        if not is_auth:
            return err_resp
            
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
        is_auth, auth_uid, err_resp = await authenticate_webapp_request(request, requested_user_id=admin_id, require_admin=True)
        if not is_auth:
            return err_resp
            
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
        is_auth, auth_uid, err_resp = await authenticate_webapp_request(request, requested_user_id=user_id, require_admin=True)
        if not is_auth:
            return err_resp
            
        text = data.get("text", "").strip()
        image_url = data.get("image_url", "").strip()
            
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
        is_auth, auth_uid, err_resp = await authenticate_webapp_request(request, requested_user_id=user_id, require_admin=True)
        if not is_auth:
            return err_resp
            
        target_id = int(data.get("target_id", 0))
        ban = bool(data.get("ban", False))
            
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
        is_auth, auth_uid, err_resp = await authenticate_webapp_request(request, requested_user_id=user_id, require_admin=True)
        if not is_auth:
            return err_resp
            
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
            if player.role not in ["Witch", "Courtesan"]:
                return web.json_response({"error": "Siz Jodugar emassiz!"}, status=400)
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

# In-memory Ghost Chat store is now managed inside game_manager

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

async def set_custom_bg_handler(request):
    try:
        data = await request.json()
        user_id = int(data.get("user_id", 0))
        bg_url = data.get("bg_url", "").strip()
        if not user_id:
            return web.json_response({"error": "user_id kiritilishi shart"}, status=400)
            
        success = await db.set_custom_bg(user_id, bg_url)
        if success:
            return web.json_response({"success": True, "message": "Orqa fon muvaffaqiyatli o'zgartirildi!"})
        else:
            return web.json_response({"error": "Siz VIP emassiz yoki xatolik yuz berdi"}, status=403)
    except Exception as e:
        logging.error(f"Error in set_custom_bg_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def daily_claim_handler(request):
    try:
        data = await request.json()
        user_id = int(data.get("user_id", 0))
        if not user_id:
            return web.json_response({"error": "user_id kiritilishi shart"}, status=400)
            
        success, coins_earned, streak_info_or_err = await db.claim_daily_reward(user_id)
        if success:
            return web.json_response({
                "success": True, 
                "coins": coins_earned, 
                "streak_info": streak_info_or_err if isinstance(streak_info_or_err, dict) else {},
                "message": "Kunlik bonus olindi!"
            })
        else:
            return web.json_response({"success": False, "error": streak_info_or_err})
    except Exception as e:
        logging.error(f"Error in daily_claim_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def checkout_handler(request):
    try:
        data = await request.json()
        user_id = int(data.get("user_id", 0))
        package_key = data.get("package_key")
        
        packages = {
            "coins_100": {"name": "100 Dark Coins", "description": "100 ta tanga paketi", "price_stars": 25, "coins": 100},
            "coins_500": {"name": "500 Dark Coins", "description": "500 ta tanga paketi", "price_stars": 100, "coins": 500},
            "coins_1000": {"name": "1000 Dark Coins", "description": "1000 ta tanga paketi", "price_stars": 175, "coins": 1000},
            "vip_1month": {"name": "1 Month VIP Status", "description": "1 oylik VIP obuna (Oltin ramka, 2x XP, shaxsiy fon)", "price_stars": 150, "coins": 0}
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

async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    user_id = request.query.get("user_id")
    room_id = request.query.get("room_id")
    
    if not user_id or not room_id:
        await ws.close(code=4000, message=b"Missing user_id or room_id")
        return ws
        
    try:
        user_id = int(user_id)
    except ValueError:
        await ws.close(code=4000, message=b"Invalid user_id")
        return ws
        
    room_id = str(room_id)
    
    rooms = request.app.setdefault('ws_rooms', {})
    if room_id not in rooms:
        rooms[room_id] = {}
    rooms[room_id][user_id] = ws
    
    logging.info(f"WebSocket connected: User {user_id} in Room {room_id}")
    
    # Broadcast join to others
    join_payload = {"type": "join", "user_id": user_id}
    for uid, peer_ws in rooms[room_id].items():
        if uid != user_id and not peer_ws.closed:
            try:
                await peer_ws.send_json(join_payload)
            except Exception:
                pass
                
    try:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                try:
                    data = msg.json()
                    data["user_id"] = user_id
                    
                    # Broadcast to everyone else in the room
                    for uid, peer_ws in rooms[room_id].items():
                        if uid != user_id and not peer_ws.closed:
                            try:
                                await peer_ws.send_json(data)
                            except Exception:
                                pass
                except Exception as e:
                    logging.error(f"Error processing WS message: {e}")
            elif msg.type == aiohttp.WSMsgType.ERROR:
                logging.error(f'ws connection closed with exception {ws.exception()}')
    finally:
        if room_id in rooms and user_id in rooms[room_id]:
            del rooms[room_id][user_id]
            if not rooms[room_id]:
                del rooms[room_id]
                
        logging.info(f"WebSocket disconnected: User {user_id} in Room {room_id}")
        
        disconnect_payload = {"type": "disconnect", "user_id": user_id}
        if room_id in rooms:
            for uid, peer_ws in rooms[room_id].items():
                if uid != user_id and not peer_ws.closed:
                    try:
                        await peer_ws.send_json(disconnect_payload)
                    except Exception:
                        pass
                        
    return ws

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
            msg = get_text(lang, "card_purchase_success", coins=coins)
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
        if chat_id not in game_manager.ghost_chats:
            game_manager.ghost_chats[chat_id] = []
            
        msg = {
            "sender": player.name,
            "text": text,
            "timestamp": datetime.now().strftime("%H:%M")
        }
        game_manager.ghost_chats[chat_id].append(msg)
        
        if len(game_manager.ghost_chats[chat_id]) > 50:
            game_manager.ghost_chats[chat_id].pop(0)
            
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
        msgs = game_manager.ghost_chats.get(chat_id, [])
            
        return web.json_response({"messages": msgs})
    except Exception as e:
        logging.error(f"Error in ghost_chat_messages_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def mafia_chat_send_handler(request):
    try:
        data = await request.json()
        user_id = int(data.get("user_id", 0))
        text = data.get("text", "").strip()
        
        if not user_id or not text:
            return web.json_response({"error": "user_id va matn kiritilishi shart"}, status=400)
            
        from game.manager import game_manager
        game = game_manager.get_game_by_player(user_id)
        if not game or game.phase != "night":
            return web.json_response({"error": "Hozir tungi bosqich emas!"}, status=400)
            
        player = game.players.get(user_id)
        if not player or not player.is_alive or player.role not in ["Mafia", "Don"]:
            return web.json_response({"error": "Faqat tirik mafiya a'zolari yozishi mumkin!"}, status=403)
            
        chat_id = game.chat_id
        if chat_id not in game_manager.mafia_chats:
            game_manager.mafia_chats[chat_id] = []
            
        msg = {
            "sender": player.name,
            "text": text,
            "timestamp": datetime.now().strftime("%H:%M")
        }
        game_manager.mafia_chats[chat_id].append(msg)
        
        if len(game_manager.mafia_chats[chat_id]) > 50:
            game_manager.mafia_chats[chat_id].pop(0)
            
        return web.json_response({"success": True})
    except Exception as e:
        logging.error(f"Error in mafia_chat_send_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def mafia_chat_messages_handler(request):
    try:
        user_id = int(request.query.get("user_id", 0))
        if not user_id:
            return web.json_response({"error": "user_id kiritilishi shart"}, status=400)
            
        from game.manager import game_manager
        game = game_manager.get_game_by_player(user_id)
        if not game:
            return web.json_response({"messages": []})
            
        player = game.players.get(user_id)
        if not player or player.role not in ["Mafia", "Don"]:
            return web.json_response({"messages": []})
            
        chat_id = game.chat_id
        msgs = game_manager.mafia_chats.get(chat_id, [])
            
        return web.json_response({"messages": msgs})
    except Exception as e:
        logging.error(f"Error in mafia_chat_messages_handler: {e}")
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
            
        await db.get_user(user_id)
            
        async with aiosqlite.connect(db.DB_PATH) as sqlite_db:
            sqlite_db.row_factory = aiosqlite.Row
            async with sqlite_db.execute("SELECT * FROM rooms WHERE room_id = ?", (room_id,)) as cursor:
                room = await cursor.fetchone()
                
        if not room:
            return web.json_response({"error": "Bunday xona topilmadi!"}, status=404)
            
        if room['status'] != 'lobby':
            return web.json_response({"error": "O'yin allaqachon boshlangan!"}, status=400)
            
        room_pin = str(room['pin_code'] or "").strip()
        if room['is_private'] and room_pin != pin_code:
            return web.json_response({"error": "PIN-kod noto'g'ri!"}, status=403)
            
        active_room = await db.get_active_room(user_id)
        if active_room:
            if active_room['room_id'] == room_id:
                return web.json_response({"success": True})
            elif active_room['status'] == 'finished':
                await db.leave_room(active_room['room_id'], user_id)
            else:
                # If room status is lobby, leave old lobby to join new room
                if active_room['status'] == 'lobby':
                    await db.leave_room(active_room['room_id'], user_id)
                else:
                    return web.json_response({"error": "Siz allaqachon aktiv o'yindasiz!"}, status=400)
            
        party_row = await db.get_user_party(user_id)
        party_members = []
        if party_row and party_row['leader_id'] == user_id:
            party_members = await db.get_party_members(party_row['party_id'])
            for m in party_members:
                if m['user_id'] != user_id:
                    m_active = await db.get_active_room(m['user_id'])
                    if m_active and m_active['room_id'] != room_id:
                        if m_active['status'] in ('lobby', 'finished'):
                            await db.leave_room(m_active['room_id'], m['user_id'])
                        else:
                            return web.json_response({"error": f"Partiya a'zosi {m['first_name']} boshqa faol o'yinda!"}, status=400)
                        
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

# Clan Handlers
async def clan_create_handler(request):
    try:
        data = await request.json()
        user_id = int(data.get("user_id", 0))
        name = data.get("name", "").strip()
        logo_url = data.get("logo_url", "").strip()
        
        is_auth, auth_uid, err_resp = await authenticate_webapp_request(request, requested_user_id=user_id)
        if not is_auth:
            return err_resp
            
        if not user_id or not name:
            return web.json_response({"error": "user_id va klan nomi kiritilishi shart"}, status=400)
            
        if len(name) < 3 or len(name) > 20:
            return web.json_response({"error": "Klan nomi 3 dan 20 belgichada bo'lishi kerak"}, status=400)
            
        success, message, clan_info = await db.create_clan(name, user_id, logo_url)
        if success:
            return web.json_response({"success": True, "message": message, "clan": clan_info})
        else:
            return web.json_response({"error": message}, status=400)
    except Exception as e:
        logging.error(f"Error in clan_create_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def clan_join_handler(request):
    try:
        data = await request.json()
        user_id = int(data.get("user_id", 0))
        clan_id = data.get("clan_id", "").strip()
        
        is_auth, auth_uid, err_resp = await authenticate_webapp_request(request, requested_user_id=user_id)
        if not is_auth:
            return err_resp
            
        if not user_id or not clan_id:
            return web.json_response({"error": "user_id va clan_id kiritilishi shart"}, status=400)
            
        success, message = await db.join_clan(clan_id, user_id)
        if success:
            return web.json_response({"success": True, "message": message})
        else:
            return web.json_response({"error": message}, status=400)
    except Exception as e:
        logging.error(f"Error in clan_join_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def clan_leave_handler(request):
    try:
        data = await request.json()
        user_id = int(data.get("user_id", 0))
        
        is_auth, auth_uid, err_resp = await authenticate_webapp_request(request, requested_user_id=user_id)
        if not is_auth:
            return err_resp
            
        if not user_id:
            return web.json_response({"error": "user_id kiritilishi shart"}, status=400)
            
        success, message = await db.leave_clan(user_id)
        if success:
            return web.json_response({"success": True, "message": message})
        else:
            return web.json_response({"error": message}, status=400)
    except Exception as e:
        logging.error(f"Error in clan_leave_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def clan_status_handler(request):
    try:
        user_id = int(request.query.get("user_id", 0))
        if not user_id:
            return web.json_response({"error": "user_id kiritilishi shart"}, status=400)
            
        clan = await db.get_user_clan(user_id)
        if not clan:
            return web.json_response({"inClan": False})
            
        members = await db.get_clan_members(clan['clan_id'])
        return web.json_response({
            "inClan": True,
            "clan": clan,
            "members": members
        })
    except Exception as e:
        logging.error(f"Error in clan_status_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def clan_leaderboard_handler(request):
    try:
        limit = int(request.query.get("limit", 10))
        clans = await db.get_clan_leaderboard(limit)
        return web.json_response({"clans": clans})
    except Exception as e:
        logging.error(f"Error in clan_leaderboard_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

# Channel Sub, Tournaments, and Battle Pass Handlers
async def check_sub_handler(request):
    try:
        user_id = int(request.query.get("user_id", 0))
        if not user_id:
            return web.json_response({"error": "user_id kiritilishi shart"}, status=400)
            
        bot = request.app['bot']
        from config import REQUIRED_CHANNEL
        if not REQUIRED_CHANNEL:
            return web.json_response({"is_subscribed": True})
            
        try:
            member = await bot.get_chat_member(REQUIRED_CHANNEL, user_id)
            is_sub = member.status in ["creator", "administrator", "member"]
        except Exception:
            is_sub = False
            
        return web.json_response({"is_subscribed": is_sub, "channel": REQUIRED_CHANNEL})
    except Exception as e:
        logging.error(f"Error in check_sub_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def tournaments_list_handler(request):
    try:
        tournaments = await db.get_tournaments()
        return web.json_response({"tournaments": tournaments})
    except Exception as e:
        logging.error(f"Error in tournaments_list_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def tournament_join_handler(request):
    try:
        data = await request.json()
        user_id = int(data.get("user_id", 0))
        tournament_id = int(data.get("tournament_id", 0))
        
        is_auth, auth_uid, err_resp = await authenticate_webapp_request(request, requested_user_id=user_id)
        if not is_auth:
            return err_resp
            
        if not user_id or not tournament_id:
            return web.json_response({"error": "user_id va tournament_id kiritilishi shart"}, status=400)
            
        success, message = await db.join_tournament(tournament_id, user_id)
        if success:
            return web.json_response({"success": True, "message": message})
        else:
            return web.json_response({"error": message}, status=400)
    except Exception as e:
        logging.error(f"Error in tournament_join_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def battle_pass_handler(request):
    try:
        user_id = int(request.query.get("user_id", 0))
        if not user_id:
            return web.json_response({"error": "user_id kiritilishi shart"}, status=400)
            
        bp = await db.get_user_battle_pass(user_id)
        return web.json_response({"battle_pass": bp})
    except Exception as e:
        logging.error(f"Error in battle_pass_handler: {e}")
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
    app.router.add_post("/api/profile/custom-bg", set_custom_bg_handler)
    app.router.add_post("/api/daily-claim", daily_claim_handler)
    app.router.add_post("/api/payment/checkout", checkout_handler)
    app.router.add_get("/payment/mock", mock_payment_handler)
    app.router.add_post("/api/payment/mock-success", mock_payment_success_handler)
    app.router.add_post("/api/game/ghost-chat/send", ghost_chat_send_handler)
    app.router.add_get("/api/game/ghost-chat/messages", ghost_chat_messages_handler)
    app.router.add_post("/api/game/mafia-chat/send", mafia_chat_send_handler)
    app.router.add_get("/api/game/mafia-chat/messages", mafia_chat_messages_handler)
    app.router.add_get("/ws", websocket_handler)
    
    # Clan API Routes
    app.router.add_post("/api/clan/create", clan_create_handler)
    app.router.add_post("/api/clan/join", clan_join_handler)
    app.router.add_post("/api/clan/leave", clan_leave_handler)
    app.router.add_get("/api/clan/status", clan_status_handler)
    app.router.add_get("/api/clan/leaderboard", clan_leaderboard_handler)
    
    # Sub Check, Tournaments & Battle Pass Routes
    app.router.add_get("/api/check-sub", check_sub_handler)
    app.router.add_get("/api/tournaments", tournaments_list_handler)
    app.router.add_post("/api/tournaments/join", tournament_join_handler)
    app.router.add_get("/api/battle-pass", battle_pass_handler)
    
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

async def self_ping_task(url: str):
    if not url or "localhost" in url or "127.0.0.1" in url:
        logging.info("Localhost aniqlandi, self-ping faollashtirilmadi.")
        return
        
    logging.info(f"Self-ping faollashtirildi. Ping yuboriladigan manzil: {url}")
    import aiohttp
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                await asyncio.sleep(240)  # Sleep for 4 minutes
                async with session.get(url) as response:
                    status = response.status
                    logging.info(f"Self-ping yuborildi. Status: {status}")
            except Exception as e:
                logging.error(f"Self-ping yuborishda xatolik: {e}")

async def periodic_backup_task(bot):
    if not os.getenv("BACKUP_CHAT_ID"):
        return
        
    logging.info("Ma'lumotlar bazasini davriy zaxiralash (periodic backup) faollashtirildi.")
    while True:
        try:
            await asyncio.sleep(600)  # Zaxiralash har 10 daqiqada
            await db.save_db_backup(bot)
        except Exception as e:
            logging.error(f"Davriy zaxiralashda xatolik: {e}")

async def main():
    # 1. Setup Telegram Bot
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    # 2. Restore Database Backup if BACKUP_CHAT_ID is set
    await db.restore_db_backup(bot)
    
    # 3. Initialize SQLite Database
    await db.init_db()
    logging.info("Database initialized successfully.")
    
    # 3.1 Initial database backup to Telegram channel
    await db.save_db_backup(bot)
    
    # Register ban check middleware
    dp.message.outer_middleware(BanCheckMiddleware())
    dp.callback_query.outer_middleware(BanCheckMiddleware())
    
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
    
    # Start self-ping task if WEBAPP_URL is configured
    if WEBAPP_URL:
        asyncio.create_task(self_ping_task(WEBAPP_URL))
        
    # Start periodic database backup task
    asyncio.create_task(periodic_backup_task(bot))
    
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
