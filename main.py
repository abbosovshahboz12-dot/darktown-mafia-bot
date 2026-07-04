import asyncio
import logging
import os
import sys
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from datetime import datetime, timedelta
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

# --- Friends API Handlers ---
async def get_friends_handler(request):
    try:
        user_id = int(request.query.get("user_id", 0))
        if not user_id:
            return web.json_response({"error": "user_id kiritilishi shart"}, status=400)
        res = await db.get_friends(user_id)
        return web.json_response(res)
    except Exception as e:
        logging.error(f"Error in get_friends_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def add_friend_handler(request):
    try:
        data = await request.json()
        user_id = int(data.get("user_id", 0))
        friend_username = data.get("friend_username", "").strip().replace("@", "")
        if not user_id or not friend_username:
            return web.json_response({"error": "Ma'lumotlar chala"}, status=400)
        
        async with db.aiosqlite.connect(db.DB_PATH) as sqlite_db:
            sqlite_db.row_factory = db.aiosqlite.Row
            async with sqlite_db.execute("SELECT user_id FROM users WHERE username = ?", (friend_username,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return web.json_response({"error": "Bunday foydalanuvchi topilmadi"}, status=404)
                friend_id = row["user_id"]
        
        success = await db.add_friend(user_id, friend_id)
        if success:
            try:
                bot = request.app['bot']
                user = await db.get_user(user_id)
                await bot.send_message(
                    friend_id, 
                    f"👥 **{user['first_name']}** sizga do'stlik so'rovi yubordi! Mini App-da tasdiqlashingiz mumkin."
                )
            except Exception:
                pass
            return web.json_response({"success": True})
        else:
            return web.json_response({"error": "Do'stlik so'rovi allaqachon yuborilgan yoki u bilan do'stsiz"}, status=400)
    except Exception as e:
        logging.error(f"Error in add_friend_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def accept_friend_handler(request):
    try:
        data = await request.json()
        user_id = int(data.get("user_id", 0))
        requester_id = int(data.get("requester_id", 0))
        if not user_id or not requester_id:
            return web.json_response({"error": "Ma'lumotlar chala"}, status=400)
        
        success = await db.accept_friend(user_id, requester_id)
        if success:
            try:
                bot = request.app['bot']
                user = await db.get_user(user_id)
                await bot.send_message(
                    requester_id, 
                    f"✅ **{user['first_name']}** do'stlik so'rovingizni qabul qildi!"
                )
            except Exception:
                pass
            return web.json_response({"success": True})
        else:
            return web.json_response({"error": "So'rov topilmadi"}, status=400)
    except Exception as e:
        logging.error(f"Error in accept_friend_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

# --- Wheel of Fortune Handler ---
async def wheel_spin_handler(request):
    try:
        data = await request.json()
        user_id = int(data.get("user_id", 0))
        if not user_id:
            return web.json_response({"error": "user_id kiritilishi shart"}, status=400)
            
        user = await db.get_user(user_id)
        if not user:
            return web.json_response({"error": "Foydalanuvchi topilmadi"}, status=404)
            
        last_spin = user.get("last_spin_claim")
        if last_spin:
            last_spin_dt = datetime.fromisoformat(last_spin)
            diff = datetime.now() - last_spin_dt
            if diff.total_seconds() < 86400:
                seconds_left = int(86400 - diff.total_seconds())
                return web.json_response({
                    "success": False, 
                    "error": "wheel_claimed", 
                    "seconds_left": seconds_left
                })
        
        import random
        reward_idx = random.randint(0, 5)
        reward_coins = 0
        reward_item = None
        reward_text = ""
        
        if reward_idx == 0:
            reward_coins = 20
            reward_text = "🪙 20 Coins"
        elif reward_idx == 1:
            reward_coins = 50
            reward_text = "🪙 50 Coins"
        elif reward_idx == 2:
            reward_coins = 100
            reward_text = "🪙 100 Coins"
        elif reward_idx == 3:
            reward_item = "shield"
            reward_text = "🛡️ XP Qalqoni"
        elif reward_idx == 4:
            reward_item = "booster_mafia"
            reward_text = "🔴 Mafiya Booster"
        elif reward_idx == 5:
            reward_item = "booster_detective"
            reward_text = "🔵 Komissar Booster"
            
        await db.claim_spin(user_id, reward_coins, reward_item)
        
        try:
            bot = request.app['bot']
            lang = user.get("language", "uz")
            if lang == "ru":
                msg = f"🎡 **Колесо Удачи!** Вы выиграли **{reward_text}**."
            elif lang == "en":
                msg = f"🎡 **Wheel of Fortune!** You won **{reward_text}**."
            elif lang == "kz":
                msg = f"🎡 **Бақыт дөңгелегі!** Сіз **{reward_text}** ұтып алдыңыз."
            else:
                msg = f"🎡 **Omad G'ildiragi!** Siz **{reward_text}** yutib oldingiz."
            await bot.send_message(user_id, msg)
        except Exception:
            pass
            
        return web.json_response({
            "success": True, 
            "reward_index": reward_idx, 
            "reward_text": reward_text,
            "reward_coins": reward_coins,
            "reward_item": reward_item
        })
    except Exception as e:
        logging.error(f"Error in wheel_spin_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

# --- Matchmaking Handlers ---
async def join_matchmake_handler(request):
    try:
        data = await request.json()
        user_id = int(data.get("user_id", 0))
        if not user_id:
            return web.json_response({"error": "user_id kiritilishi shart"}, status=400)
        
        active_game = await db.check_player_active_webapp_game(user_id)
        if active_game:
            return web.json_response({
                "success": False, 
                "error": "already_in_game", 
                "game_id": active_game["game_id"]
            })
            
        await db.join_queue(user_id)
        return web.json_response({"success": True})
    except Exception as e:
        logging.error(f"Error in join_matchmake_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def leave_matchmake_handler(request):
    try:
        data = await request.json()
        user_id = int(data.get("user_id", 0))
        if not user_id:
            return web.json_response({"error": "user_id kiritilishi shart"}, status=400)
        await db.leave_queue(user_id)
        return web.json_response({"success": True})
    except Exception as e:
        logging.error(f"Error in leave_matchmake_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def status_matchmake_handler(request):
    try:
        user_id = int(request.query.get("user_id", 0))
        if not user_id:
            return web.json_response({"error": "user_id kiritilishi shart"}, status=400)
            
        active_game = await db.check_player_active_webapp_game(user_id)
        if active_game:
            return web.json_response({
                "status": "matched",
                "game_id": active_game["game_id"]
            })
            
        queue = await db.get_queue()
        queue_len = len(queue)
        in_queue = user_id in queue
        
        return web.json_response({
            "status": "searching" if in_queue else "idle",
            "queue_length": queue_len,
            "position": queue.index(user_id) + 1 if in_queue else 0
        })
    except Exception as e:
        logging.error(f"Error in status_matchmake_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

# --- WebApp Game Room Handlers ---
async def get_webapp_game_status_handler(request):
    try:
        game_id = request.query.get("game_id", "").strip()
        user_id = int(request.query.get("user_id", 0))
        if not game_id or not user_id:
            return web.json_response({"error": "game_id va user_id kiritilishi shart"}, status=400)
            
        game = await db.get_webapp_game(game_id)
        if not game:
            return web.json_response({"error": "O'yin topilmadi"}, status=404)
            
        players = await db.get_webapp_game_players(game_id)
        
        seconds_left = 0
        if game.get("phase_ends_at"):
            ends_at = datetime.fromisoformat(game["phase_ends_at"])
            diff = ends_at - datetime.now()
            seconds_left = max(0, int(diff.total_seconds()))
            
        self_player = next((p for p in players if p["user_id"] == user_id), None)
        if not self_player:
            return web.json_response({"error": "Siz ushbu o'yin ishtirokchisi emassiz!"}, status=403)
            
        is_ended = game["phase"] == "ended"
        is_self_mafia = self_player["role"] in ["Mafia", "Don"]
        
        sanitized_players = []
        for p in players:
            role = p["role"]
            if not is_ended:
                is_other_mafia = p["role"] in ["Mafia", "Don"]
                if p["user_id"] != user_id and not (is_self_mafia and is_other_mafia):
                    role = "Unknown"
            sanitized_players.append({
                "user_id": p["user_id"],
                "username": p["username"],
                "first_name": p["first_name"],
                "role": role,
                "is_alive": bool(p["is_alive"]),
                "has_voted": bool(p["has_voted"]),
                "target_id": p["target_id"] if p["user_id"] == user_id else None
            })
            
        return web.json_response({
            "game_id": game["game_id"],
            "phase": game["phase"],
            "seconds_left": seconds_left,
            "self_role": self_player["role"],
            "self_is_alive": bool(self_player["is_alive"]),
            "players": sanitized_players
        })
    except Exception as e:
        logging.error(f"Error in get_webapp_game_status_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def get_webapp_game_messages_handler(request):
    try:
        game_id = request.query.get("game_id", "").strip()
        user_id = int(request.query.get("user_id", 0))
        if not game_id or not user_id:
            return web.json_response({"error": "game_id va user_id kiritilishi shart"}, status=400)
            
        game = await db.get_webapp_game(game_id)
        if not game:
            return web.json_response({"messages": []})
            
        players = await db.get_webapp_game_players(game_id)
        self_player = next((p for p in players if p["user_id"] == user_id), None)
        if not self_player:
            return web.json_response({"error": "Siz ushbu o'yin ishtirokchisi emassiz!"}, status=403)
            
        is_mafia = self_player["role"] in ["Mafia", "Don"]
        msgs = await db.get_webapp_messages(game_id, include_mafia_only=is_mafia)
        
        formatted = []
        for m in msgs:
            formatted.append({
                "sender": m["sender_name"],
                "text": m["message_text"],
                "is_mafia": bool(m["is_mafia_only"]),
                "timestamp": datetime.fromisoformat(m["sent_at"]).strftime("%H:%M") if m.get("sent_at") else ""
            })
        return web.json_response({"messages": formatted})
    except Exception as e:
        logging.error(f"Error in get_webapp_game_messages_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def post_webapp_game_chat_handler(request):
    try:
        data = await request.json()
        game_id = data.get("game_id", "").strip()
        user_id = int(data.get("user_id", 0))
        text = data.get("text", "").strip()
        if not game_id or not user_id or not text:
            return web.json_response({"error": "Ma'lumotlar chala"}, status=400)
            
        game = await db.get_webapp_game(game_id)
        if not game or game["phase"] == "ended":
            return web.json_response({"error": "O'yin faol emas"}, status=400)
            
        players = await db.get_webapp_game_players(game_id)
        self_player = next((p for p in players if p["user_id"] == user_id), None)
        if not self_player:
            return web.json_response({"error": "Siz ushbu o'yin ishtirokchisi emassiz!"}, status=403)
            
        is_mafia = self_player["role"] in ["Mafia", "Don"]
        is_mafia_only = 0
        
        if game["phase"] == "night":
            if not is_mafia:
                return web.json_response({"error": "Tunda faqat mafiya a'zolari chatda yozishi mumkin!"}, status=400)
            is_mafia_only = 1
        elif game["phase"] == "day_discussion" or game["phase"] == "voting":
            if not self_player["is_alive"]:
                return web.json_response({"error": "Vafot etgan o'yinchilar kunduzi yozisha olmaydi!"}, status=400)
                
        await db.send_webapp_message(game_id, user_id, self_player["first_name"], text, is_mafia_only)
        return web.json_response({"success": True})
    except Exception as e:
        logging.error(f"Error in post_webapp_game_chat_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def post_webapp_game_action_handler(request):
    try:
        data = await request.json()
        game_id = data.get("game_id", "").strip()
        user_id = int(data.get("user_id", 0))
        target_id = int(data.get("target_id", 0))
        if not game_id or not user_id or not target_id:
            return web.json_response({"error": "Ma'lumotlar chala"}, status=400)
            
        game = await db.get_webapp_game(game_id)
        if not game or game["phase"] != "night":
            return web.json_response({"error": "Hozir tungi faza emas!"}, status=400)
            
        players = await db.get_webapp_game_players(game_id)
        self_player = next((p for p in players if p["user_id"] == user_id), None)
        target_player = next((p for p in players if p["user_id"] == target_id), None)
        
        if not self_player or not self_player["is_alive"]:
            return web.json_response({"error": "Siz tirik emassiz!"}, status=400)
        if not target_player or not target_player["is_alive"]:
            return web.json_response({"error": "Nishon tirik emas!"}, status=400)
            
        await db.submit_webapp_action(game_id, user_id, target_id)
        return web.json_response({"success": True})
    except Exception as e:
        logging.error(f"Error in post_webapp_game_action_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

async def post_webapp_game_vote_handler(request):
    try:
        data = await request.json()
        game_id = data.get("game_id", "").strip()
        user_id = int(data.get("user_id", 0))
        target_id = int(data.get("target_id", 0))
        if not game_id or not user_id or not target_id:
            return web.json_response({"error": "Ma'lumotlar chala"}, status=400)
            
        game = await db.get_webapp_game(game_id)
        if not game or game["phase"] != "voting":
            return web.json_response({"error": "Hozir ovoz berish bosqichi emas!"}, status=400)
            
        players = await db.get_webapp_game_players(game_id)
        self_player = next((p for p in players if p["user_id"] == user_id), None)
        target_player = next((p for p in players if p["user_id"] == target_id), None)
        
        if not self_player or not self_player["is_alive"]:
            return web.json_response({"error": "Siz tirik emassiz!"}, status=400)
        if not target_player or not target_player["is_alive"]:
            return web.json_response({"error": "Nishon tirik emas!"}, status=400)
            
        await db.submit_webapp_vote(game_id, user_id, target_id)
        return web.json_response({"success": True})
    except Exception as e:
        logging.error(f"Error in post_webapp_game_vote_handler: {e}")
        return web.json_response({"error": "Ichki server xatosi"}, status=500)

# --- Matchmaking Background Loop ---
async def matchmaking_loop(bot: Bot):
    logging.info("Background matchmaking loop started.")
    while True:
        try:
            # 1. Match players in queue
            queue = await db.get_queue()
            if len(queue) >= 5:
                matched_players = queue[:5]
                import random
                roles = ["Mafia", "Detective", "Doctor", "Citizen", "Citizen"]
                random.shuffle(roles)
                
                players_list = []
                for i, uid in enumerate(matched_players):
                    players_list.append({"user_id": uid, "role": roles[i]})
                    
                import uuid
                game_id = f"wag_{uuid.uuid4().hex[:10]}"
                
                await db.create_webapp_game(game_id, players_list)
                await db.clear_queue(matched_players)
                
                logging.info(f"Matched WebApp Game created: {game_id} with players {matched_players}")
                
                # Lobby phase ends in 10 seconds
                ends_at = (datetime.now() + timedelta(seconds=10)).isoformat()
                await db.update_webapp_game_phase(game_id, "lobby", ends_at)
                
                for uid in matched_players:
                    try:
                        await bot.send_message(uid, "🎮 **Mini App Interaktiv O'yini boshlanmoqda!** Darhol Mini App-ni oching.")
                    except Exception:
                        pass
                        
            # 2. Process active WebApp games phase changes
            async with db.aiosqlite.connect(db.DB_PATH) as sqlite_db:
                sqlite_db.row_factory = db.aiosqlite.Row
                async with sqlite_db.execute("SELECT * FROM webapp_games WHERE phase != 'ended'") as cursor:
                    active_games = [dict(row) for row in await cursor.fetchall()]
                    
            for game in active_games:
                game_id = game["game_id"]
                phase = game["phase"]
                
                ends_at = datetime.fromisoformat(game["phase_ends_at"]) if game.get("phase_ends_at") else None
                if ends_at and datetime.now() >= ends_at:
                    await process_webapp_game_phase_change(bot, game_id, phase)
                    
        except Exception as e:
            logging.error(f"Error in matchmaking_loop: {e}")
            
        await asyncio.sleep(3)

async def process_webapp_game_phase_change(bot: Bot, game_id: str, current_phase: str):
    players = await db.get_webapp_game_players(game_id)
    alive_players = [p for p in players if p["is_alive"]]
    
    # Check win conditions first
    mafias = [p for p in alive_players if p["role"] in ["Mafia", "Don"]]
    citizens = [p for p in alive_players if p["role"] not in ["Mafia", "Don"]]
    
    if len(mafias) == 0:
        await db.update_webapp_game_phase(game_id, "ended", None)
        await notify_webapp_game_end(bot, players, "Tinch aholi")
        return
    elif len(mafias) >= len(citizens):
        await db.update_webapp_game_phase(game_id, "ended", None)
        await notify_webapp_game_end(bot, players, "Mafiya")
        return

    if current_phase == "lobby":
        ends_at = (datetime.now() + timedelta(seconds=30)).isoformat()
        await db.update_webapp_game_phase(game_id, "night", ends_at)
        await db.send_webapp_message(game_id, 0, "Tizim", "🌙 Qorong'u tushdi. Tungi harakatlarni tanlang!", 0)
        
    elif current_phase == "night":
        mafia_player = next((p for p in alive_players if p["role"] == "Mafia"), None)
        mafia_target = mafia_player["target_id"] if mafia_player else None
        
        doctor_player = next((p for p in alive_players if p["role"] == "Doctor"), None)
        doctor_target = doctor_player["target_id"] if doctor_player else None
        
        detective_player = next((p for p in alive_players if p["role"] == "Detective"), None)
        detective_target = detective_player["target_id"] if detective_player else None
        
        killed_id = None
        detective_report = ""
        
        if mafia_target:
            if mafia_target == doctor_target:
                pass
            else:
                killed_id = mafia_target
                
        if detective_target:
            det_target_player = next((p for p in players if p["user_id"] == detective_target), None)
            if det_target_player:
                is_mafia = det_target_player["role"] in ["Mafia", "Don"]
                status_text = "MAFIYA 🔴" if is_mafia else "TINCH AHOLI 🟢"
                detective_report = f"🔍 Tekshiruv: {det_target_player['first_name']} roli - {status_text}"
                try:
                    await bot.send_message(detective_player["user_id"], f"🕵️‍♂️ **Tungi tekshiruv natijasi:**\n\n{detective_report}")
                except Exception:
                    pass
                    
        announcement = "🌅 Kun boshlandi!"
        if killed_id:
            killed_player = next((p for p in players if p["user_id"] == killed_id), None)
            if killed_player:
                await db.update_webapp_player_status(game_id, killed_id, 0)
                announcement += f"\n\n☠️ Tunda **{killed_player['first_name']}** o'ldirildi. Uning roli: **{killed_player['role']}**"
                try:
                    await bot.send_message(killed_id, "💀 **Siz tunda o'ldirildingiz!**")
                except Exception:
                    pass
        else:
            announcement += "\n\n💚 Tunda hech kim o'ldirilmadi."
            
        await db.send_webapp_message(game_id, 0, "Tizim", announcement, 0)
        
        ends_at = (datetime.now() + timedelta(seconds=45)).isoformat()
        await db.update_webapp_game_phase(game_id, "day_discussion", ends_at)
        
    elif current_phase == "day_discussion":
        ends_at = (datetime.now() + timedelta(seconds=30)).isoformat()
        await db.update_webapp_game_phase(game_id, "voting", ends_at)
        await db.send_webapp_message(game_id, 0, "Tizim", "🗳️ Ovoz berish boshlandi! Gumondorni tanlang.", 0)
        
    elif current_phase == "voting":
        votes = {}
        for p in alive_players:
            tid = p["target_id"]
            if tid:
                votes[tid] = votes.get(tid, 0) + 1
                
        max_votes = 0
        lynched_id = None
        for pid, cnt in votes.items():
            if cnt > max_votes:
                max_votes = cnt
                lynched_id = pid
            elif cnt == max_votes:
                lynched_id = None
                
        announcement = "🗳️ Ovoz berish yakunlandi."
        if lynched_id:
            lynched_player = next((p for p in players if p["user_id"] == lynched_id), None)
            if lynched_player:
                await db.update_webapp_player_status(game_id, lynched_id, 0)
                announcement += f"\n\n⚖️ Ko'p ovoz bilan **{lynched_player['first_name']}** dorda osildi! Uning roli: **{lynched_player['role']}**"
                try:
                    await bot.send_message(lynched_id, "💀 **Siz ko'pchilik ovozi bilan osildingiz!**")
                except Exception:
                    pass
        else:
            announcement += "\n\n⚖️ Ovozlar teng keldi yoki hech kim ovoz bermadi. Hech kim osilmadi."
            
        await db.send_webapp_message(game_id, 0, "Tizim", announcement, 0)
        
        updated_players = await db.get_webapp_game_players(game_id)
        updated_alive = [p for p in updated_players if p["is_alive"]]
        updated_mafias = [p for p in updated_alive if p["role"] in ["Mafia", "Don"]]
        updated_citizens = [p for p in updated_alive if p["role"] not in ["Mafia", "Don"]]
        
        if len(updated_mafias) == 0:
            await db.update_webapp_game_phase(game_id, "ended", None)
            await notify_webapp_game_end(bot, updated_players, "Tinch aholi")
            return
        elif len(updated_mafias) >= len(updated_citizens):
            await db.update_webapp_game_phase(game_id, "ended", None)
            await notify_webapp_game_end(bot, updated_players, "Mafiya")
            return
            
        ends_at = (datetime.now() + timedelta(seconds=30)).isoformat()
        await db.update_webapp_game_phase(game_id, "night", ends_at)
        await db.send_webapp_message(game_id, 0, "Tizim", "🌙 Qorong'u tushdi. Tungi harakatlarni tanlang!", 0)

async def notify_webapp_game_end(bot: Bot, players: list, winner_faction: str):
    for p in players:
        uid = p["user_id"]
        role = p["role"]
        is_winner = False
        if winner_faction == "Mafiya" and role in ["Mafia", "Don"]:
            is_winner = True
        elif winner_faction == "Tinch aholi" and role not in ["Mafia", "Don"]:
            is_winner = True
            
        xp_gain = 100 if is_winner else 20
        coins_gain = 50 if is_winner else 10
        
        await db.add_rewards(uid, xp_gain, coins_gain)
        
        try:
            status_symbol = "🏆" if is_winner else "🎗️"
            result_text = "G'alaba!" if is_winner else "Mag'lubiyat."
            msg = (
                f"🎉 **Mini App O'yini Yakunlandi!**\n\n"
                f"G'olib tomon: **{winner_faction}**\n"
                f"Sizning natijangiz: **{status_symbol} {result_text}**\n\n"
                f"Mukofotlar: **+{xp_gain} XP** va **+{coins_gain} tanga**!"
            )
            await bot.send_message(uid, msg)
        except Exception:
            pass

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
    app.router.add_post("/api/profile/language", set_language_handler)
    app.router.add_post("/api/daily-claim", daily_claim_handler)
    app.router.add_post("/api/payment/checkout", checkout_handler)
    app.router.add_get("/payment/mock", mock_payment_handler)
    app.router.add_post("/api/payment/mock-success", mock_payment_success_handler)
    app.router.add_post("/api/game/ghost-chat/send", ghost_chat_send_handler)
    app.router.add_get("/api/game/ghost-chat/messages", ghost_chat_messages_handler)
    
    # Friends API
    app.router.add_get("/api/friends", get_friends_handler)
    app.router.add_post("/api/friends/add", add_friend_handler)
    app.router.add_post("/api/friends/accept", accept_friend_handler)
    
    # Wheel API
    app.router.add_post("/api/wheel/spin", wheel_spin_handler)
    
    # Matchmaking API
    app.router.add_post("/api/game/matchmake/join", join_matchmake_handler)
    app.router.add_post("/api/game/matchmake/leave", leave_matchmake_handler)
    app.router.add_get("/api/game/matchmake/status", status_matchmake_handler)
    
    # WebApp Game Room API
    app.router.add_get("/api/webapp-game/status", get_webapp_game_status_handler)
    app.router.add_get("/api/webapp-game/messages", get_webapp_game_messages_handler)
    app.router.add_post("/api/webapp-game/chat/send", post_webapp_game_chat_handler)
    app.router.add_post("/api/webapp-game/action", post_webapp_game_action_handler)
    app.router.add_post("/api/webapp-game/vote", post_webapp_game_vote_handler)
    
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
    
    # 4. Start Matchmaking Background Loop
    asyncio.create_task(matchmaking_loop(bot))
    
    # 5. Start Bot Polling
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
