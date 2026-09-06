import asyncio
import random
import logging
from typing import List, Optional
from aiogram import Bot, types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from game.models import Game, Player
from game.events import get_random_event
from game.manager import game_manager
from database import db

# Role emojis
ROLE_EMOJIS = {
    "Mafia": "🔴",
    "Don": "🕶️",
    "Lawyer": "⚖️",
    "Civilian": "🟢",
    "Detective": "🔵",
    "Sergeant": "🎖️",
    "Doctor": "🟡",
    "Bodyguard": "🛡️",
    "Witch": "🧹",
    "Maniac": "🦹",
    "Jester": "🃏"
}

def get_role_details(role: str) -> str:
    details = {
        "Mafia": "🔴 **Mafiya**: Siz qorong'u kuchlar a'zosiz. Har kecha o'z sheriklaringiz bilan kelishgan holda shaharliklardan birini o'ldirishga ovoz berasiz.",
        "Don": "🕶️ **Don**: Mafiya yetakchisi. Har kecha Komissar kimligini bilish uchun o'yinchilardan birini tekshirishingiz mumkin.",
        "Lawyer": "⚖️ **Advokat**: Mafiya tarafdori. Har kecha bir o'yinchini (mafiyani) tanlaysiz. Komissar uni tekshirganda 'Tinch aholi' bo'lib ko'rinadi.",
        "Civilian": "🟢 **Tinch aholi**: Oddiy shahar fuqarosi. Maqsadingiz - kunduzi munozaralar orqali shubhali shaxslarni aniqlash va ularni dorda osish uchun ovoz berish.",
        "Detective": "🔵 **Komissar**: Qonun himoyachisi. Har kecha o'yinchilardan birini tekshirib, uning mafiya yoki tinch aholi ekanligini bilib olasiz.",
        "Sergeant": "🎖️ **Serjant**: Komissarning yordamchisi. Komissar halok bo'lgach, siz uning o'rniga yangi Komissar bo'lib o'yinchilarni tekshirishni davom ettirasiz.",
        "Doctor": "🟡 **Shifokor**: Har kecha bir o'yinchini davolaysiz. Agar u tunda hujumga uchrasa, tirik qoladi.",
        "Bodyguard": "🛡️ **Tansoqchi**: Har kecha bir o'yinchini himoya qilasiz. Agar unga hujum bo'lsa, siz uning o'rniga halok bo'lasiz.",
        "Witch": "🧹 **Jodugar**: Har kecha bir o'yinchini afsunlab, uning tungi qobiliyatini bloklaysiz.",
        "Maniac": "🦹 **Telba (Maniac)**: Yolg'iz qotil. Maqsadingiz - barcha o'yinchilarni o'ldirish va yagona tirik qolgan odam bo'lish.",
        "Jester": "🃏 **Mazxaraboz (Jester)**: Yolg'iz o'yinchi. Maqsadingiz - shaharni aldab, kunduzgi ovoz berishda o'zingizni dorda osishlariga erishish. Dorda osilsangiz g'olib bo'lasiz!"
    }
    return details.get(role, "")

def distribute_roles(players_count: int) -> List[str]:
    if players_count <= 5:
        return ["Don", "Doctor", "Detective", "Civilian", "Civilian"]
    elif players_count == 6:
        return ["Don", "Doctor", "Detective", "Civilian", "Civilian", "Civilian"]
    elif players_count == 7:
        return ["Don", "Mafia", "Doctor", "Detective", "Civilian", "Civilian", "Civilian"]
    elif players_count == 8:
        return ["Don", "Mafia", "Doctor", "Detective", "Bodyguard", "Civilian", "Civilian", "Civilian"]
    elif players_count == 9:
        return ["Don", "Mafia", "Doctor", "Detective", "Bodyguard", "Maniac", "Civilian", "Civilian", "Civilian"]
    elif players_count == 10:
        return ["Don", "Mafia", "Doctor", "Detective", "Bodyguard", "Witch", "Maniac", "Civilian", "Civilian", "Civilian"]
    elif players_count == 11:
        return ["Don", "Mafia", "Mafia", "Doctor", "Detective", "Sergeant", "Bodyguard", "Witch", "Maniac", "Civilian", "Civilian"]
    elif players_count == 12:
        return ["Don", "Mafia", "Mafia", "Lawyer", "Doctor", "Detective", "Sergeant", "Bodyguard", "Witch", "Maniac", "Jester", "Civilian"]
    else: # 13+ players
        base = ["Don", "Mafia", "Mafia", "Lawyer", "Doctor", "Detective", "Sergeant", "Bodyguard", "Witch", "Maniac", "Jester", "Bodyguard"]
        while len(base) < players_count:
            base.append("Civilian")
        return base

async def assign_roles(game: Game, bot: Bot):
    players = list(game.players.values())
    num_players = len(players)
    roles_pool = distribute_roles(num_players)
    
    # Shuffle roles pool
    random.shuffle(roles_pool)
    
    # Non-civilian active roles
    active_roles = [r for r in roles_pool if r != "Civilian"]
    assigned_players = set()
    
    # Assign based on boosters first
    for player in players:
        booster = getattr(player, "role_booster", None)
        if booster:
            if booster in ["Active", "Faol", "ActiveRole", "active"] and active_roles:
                chosen = active_roles.pop(0)
                roles_pool.remove(chosen)
                player.role = chosen
                assigned_players.add(player.user_id)
                await db.use_item(player.user_id, "booster_active")
            elif booster in roles_pool:
                player.role = booster
                roles_pool.remove(booster)
                if booster in active_roles:
                    active_roles.remove(booster)
                assigned_players.add(player.user_id)
                await db.use_item(player.user_id, f"booster_{booster.lower()}")
            
    # Assign remaining
    for player in players:
        if player.user_id not in assigned_players:
            player.role = roles_pool.pop()
            
    # Send roles to players privately
    for player in players:
        role_emoji = ROLE_EMOJIS.get(player.role, "")
        message_text = (
            f"🎭 **Sizning rolingiz**: {role_emoji} **{player.role}**\n\n"
            f"{get_role_details(player.role)}\n\n"
            f"O'yin tez orada boshlanadi. Tungi harakatlarga tayyor turing!"
        )
        try:
            await bot.send_message(player.user_id, message_text, parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Could not send role to user {player.user_id}: {e}")

def log_game_event(game: Game, text: str):
    if not hasattr(game, "logs"):
        game.logs = []
    game.logs.append(text)
    if len(game.logs) > 30:
        game.logs.pop(0)

async def try_mute_chat(bot: Bot, chat_id: int, mute: bool):
    try:
        if mute:
            permissions = types.ChatPermissions(can_send_messages=False)
        else:
            permissions = types.ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
        await bot.set_chat_permissions(chat_id, permissions)
    except Exception as e:
        logging.warning(f"Could not set chat permissions (mute={mute}): {e}")

async def try_restrict_user(bot: Bot, chat_id: int, user_id: int, mute: bool):
    if chat_id >= 0:
        return
    try:
        if mute:
            permissions = types.ChatPermissions(can_send_messages=False)
        else:
            permissions = types.ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
        await bot.restrict_chat_member(chat_id, user_id, permissions)
    except Exception as e:
        logging.warning(f"Could not restrict user {user_id} (mute={mute}): {e}")

async def send_game_gif(bot: Bot, chat_id: int, event_type: str):
    from config import WEBAPP_URL
    gifs = {
        "start": "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExMzM2MWF6bWdkZno4bmx4d3V1MW01ajBhMmhrbjR5MGw4NGZ3MGNtaSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/3o7TKrE1xs1sA5yyZ2/giphy.gif",
        "night": "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExM3ZkMnJid2tmbjI5M2t3MHU4b3M2Yzg5dHc1Y293YTFtMWZhbzJ0NiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/3o7TKrE1xs1sA5yyZ2/giphy.gif",
        "day": "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExbDV2bGNmMTBrOWUxeDVwNDNqMzdrbXh3OTN2c2U5cGRxNWlzNm9jMiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/5tq3c6tZ30c8F7lS8a/giphy.gif",
        "death": "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExM3N2cWw2MzJrMmtnbjVwM2s0a3MxMGFtMTVnNTR5MXplM2MzaDJlYSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/h5NLPXL6M3FQPv805H/giphy.gif",
        "hang": "https://media.giphy.com/media/3o7TKxOzwhg1VBU5y0/giphy.gif",
        "win_mafia": "https://media.giphy.com/media/l0HlTL9EubJ7kL2g0/giphy.gif",
        "win_civilian": "https://media.giphy.com/media/l0HG0bS8u6r5VwAhy/giphy.gif",
        "win_jester": "https://media.giphy.com/media/3o7TKSx0g7u5oWf3S0/giphy.gif",
        "win_maniac": "https://media.giphy.com/media/h5NLPXL6M3FQPv805H/giphy.gif"
    }
    url = gifs.get(event_type)
    if url:
        try:
            await bot.send_animation(chat_id, url)
        except Exception:
            try:
                await bot.send_photo(chat_id, url)
            except Exception as e:
                logging.warning(f"Could not send game GIF ({event_type}): {e}")

async def start_game_loop(bot: Bot, game: Game):
    try:
        # Cancel any active lobby timer
        if game.timer_task and not game.timer_task.done():
            game.timer_task.cancel()
            game.timer_task = None
            
        game.phase = "starting"
        
        # Load group settings for custom timers & rules
        if game.chat_id < 0:
            try:
                g_settings = await db.get_group_settings(game.chat_id)
                game.day_time = int(g_settings.get("day_time", 60))
                game.night_time = int(g_settings.get("night_time", 45))
                game.voting_time = int(g_settings.get("voting_time", 45))
                game.mute_night = bool(g_settings.get("mute_night", 1))
                game.secret_voting = bool(g_settings.get("secret_voting", 0))
                
                chat_info = await bot.get_chat(game.chat_id)
                g_title = chat_info.title or ""
                g_uname = chat_info.username or ""
                await db.update_group_setting(game.chat_id, "title", g_title, title=g_title, username=g_uname)
            except Exception as ex:
                logging.warning(f"Error loading group settings for chat {game.chat_id}: {ex}")

        # Assign roles
        await assign_roles(game, bot)
        log_game_event(game, "🎭 O'yin boshlandi. Rollar taqsimlandi.")
        
        try:
            await send_game_gif(bot, game.chat_id, "start")
        except Exception as e:
            logging.warning(f"Could not send start GIF: {e}")
            
        from collections import Counter
        role_counts = Counter([p.role for p in game.players.values()])
        roles_summary_list = []
        for role_name, count in role_counts.items():
            emoji = ROLE_EMOJIS.get(role_name, "👤")
            roles_summary_list.append(f"{emoji} {role_name}: **{count}** ta")
        roles_summary_text = " | ".join(roles_summary_list)

        await bot.send_message(
            game.chat_id,
            f"🎭 **Rollar taqsimlandi!** Har bir o'yinchiga o'z roli shaxsiy chatda yuborildi.\n\n"
            f"📋 **Ushbu o'yindagi rollar tarkibi**:\n{roles_summary_text}\n\n"
            f"🌙 **Qorong'u tushmoqda... Tun boshlandi!**\n"
            f"Barcha faol rollar shaxsiy chatda bot yuborgan xabarlarga qarab harakat qilsin."
        )
        await night_phase(bot, game)
    except Exception as e:
        logging.error(f"CRITICAL ERROR in start_game_loop: {e}", exc_info=True)
        try:
            await bot.send_message(game.chat_id, f"⚠️ O'yinni boshlashda xatolik yuz berdi. Iltimos, qaytadan `/newgame` yozing.")
        except Exception:
            pass

async def night_phase(bot: Bot, game: Game):
    game.phase = "night"
    log_game_event(game, "🌙 Tun boshlandi. Rollar tungi harakatda.")
    try:
        await send_game_gif(bot, game.chat_id, "night")
    except Exception as e:
        logging.warning(f"Could not send night GIF: {e}")
    
    # Send group night announcement
    msg = await bot.send_message(
        game.chat_id,
        "🌙 **Shahar uzra tun cho'kdi... Barcha tinch aholi shirin uyquda. Mafiya va faol rollar tunda uyg'onmoqda.**\n\n"
        "_(Harakatlarni bajarish uchun shaxsiy chatga o'ting yoki Mini App-ni oching!)_"
    )
    game.night_message_id = msg.message_id
    
    # Mute group chat if enabled
    if getattr(game, "mute_night", True):
        await try_mute_chat(bot, game.chat_id, True)
    
    # Reset statuses
    for p in game.players.values():
        p.reset_night_status()
        
    game.night_actions = {
        "mafia": {},
        "don": None,
        "detective_check": None,
        "detective_shoot": None,
        "doctor": None,
        "bodyguard": None,
        "courtesan": None,
        "maniac": None
    }
    
    # Send action keyboards in private message
    alive_players = game.get_alive_players()
    
    # Build list of targets
    def target_keyboard(action_prefix: str, exclude_id: int = None, prevent_self: bool = False, last_target: int = None) -> types.InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()
        for p in alive_players:
            if exclude_id and p.user_id == exclude_id:
                continue
            if prevent_self and p.user_id == exclude_id:
                continue
            if last_target and p.user_id == last_target:
                continue
            kb.add(types.InlineKeyboardButton(text=p.name, callback_data=f"{action_prefix}_{p.user_id}"))
        kb.adjust(2)
        return kb.as_markup()

    # Send messages to active roles
    for player in alive_players:
        try:
            if player.role == "Mafia":
                # Mafia targets (exclude other mafias/don)
                mafia_and_don = [m.user_id for m in game.get_players_by_role("Mafia") + game.get_players_by_role("Don")]
                kb = InlineKeyboardBuilder()
                for p in alive_players:
                    if p.user_id not in mafia_and_don:
                        kb.add(types.InlineKeyboardButton(text=p.name, callback_data=f"mafia_{p.user_id}"))
                kb.adjust(2)
                await bot.send_message(player.user_id, "🔴 **Mafiya ovoz berishi**: Bugun tunda kimni yo'qotmoqchisiz?", reply_markup=kb.as_markup())
                
            elif player.role == "Don":
                # Don looks for detective
                mafia_and_don = [m.user_id for m in game.get_players_by_role("Mafia") + game.get_players_by_role("Don")]
                
                # 1. Don Check Keyboard
                kb_check = InlineKeyboardBuilder()
                for p in alive_players:
                    if p.user_id not in mafia_and_don:
                        kb_check.add(types.InlineKeyboardButton(text=p.name, callback_data=f"don_{p.user_id}"))
                kb_check.adjust(2)
                await bot.send_message(player.user_id, "🕶️ **Don tekshiruvi**: Komissarni topish uchun kimni tekshirmoqchisiz?", reply_markup=kb_check.as_markup())
                
                # 2. Mafia Voting Keyboard
                kb_mafia = InlineKeyboardBuilder()
                for p in alive_players:
                    if p.user_id not in mafia_and_don:
                        kb_mafia.add(types.InlineKeyboardButton(text=p.name, callback_data=f"mafia_{p.user_id}"))
                kb_mafia.adjust(2)
                await bot.send_message(player.user_id, "🔴 **Mafiya ovoz berishi**: Bugun tunda kimni yo'qotmoqchisiz?", reply_markup=kb_mafia.as_markup())
                
            elif player.role == "Detective":
                # Check option choice keyboard
                kb = InlineKeyboardBuilder()
                kb.add(types.InlineKeyboardButton(text="🔍 Tekshirish (Check)", callback_data="det_choice_check"))
                kb.add(types.InlineKeyboardButton(text="🔫 Otib yuborish (Shoot)", callback_data="det_choice_shoot"))
                kb.adjust(1)
                
                await bot.send_message(
                    player.user_id,
                    "🔵 **Komissar harakati**:\n"
                    "Bugun tunda nima qilmoqchisiz? Tanlang:\n"
                    "_(Tekshirish majburiy: yoki tekshiring, yoki otib yuboring)_",
                    reply_markup=kb.as_markup()
                )
                    
            elif player.role == "Doctor":
                # Heal target (cannot heal same target unless event epidemic)
                allow_self = True
                last_tgt = game.last_doctor_target
                if game.event and game.event["key"] == "epidemic":
                    last_tgt = None # Allow healing same person
                kb = target_keyboard("doc", exclude_id=(None if allow_self else player.user_id), last_target=last_tgt)
                await bot.send_message(player.user_id, "🟡 **Shifokor davolashi**: Kimni o'limdan qutqarmoqchisiz?", reply_markup=kb)
                
            elif player.role == "Bodyguard":
                # Protect target (not self, not same target)
                kb = target_keyboard("guard", exclude_id=player.user_id, last_target=game.last_bodyguard_target)
                await bot.send_message(player.user_id, "🛡️ **Tansoqchi himoyasi**: Kimni himoya qilmoqchisiz?", reply_markup=kb)
                
            elif player.role == "Witch":
                # Block target (not self)
                kb = target_keyboard("block", exclude_id=player.user_id)
                await bot.send_message(player.user_id, "🧹 **Jodugar afsuni**: Tungi qobiliyatini bloklamoqchi bo'lgan o'yinchini tanlang:", reply_markup=kb)
                
            elif player.role == "Lawyer":
                mafia_allies = [m for m in alive_players if m.role in ["Mafia", "Don", "Lawyer"]]
                kb = InlineKeyboardBuilder()
                for p in mafia_allies:
                    kb.add(types.InlineKeyboardButton(text=p.name, callback_data=f"lawyer_{p.user_id}"))
                kb.adjust(2)
                await bot.send_message(player.user_id, "⚖️ **Advokat himoyasi**: Komissardan yashirmoqchi bo'lgan Mafiya a'zosini tanlang:", reply_markup=kb.as_markup())

            elif player.role == "Sergeant":
                detectives = [p for p in alive_players if p.role == "Detective"]
                if not detectives:
                    kb = InlineKeyboardBuilder()
                    kb.add(types.InlineKeyboardButton(text="🔍 Tekshirish (Check)", callback_data="det_choice_check"))
                    kb.add(types.InlineKeyboardButton(text="🔫 Otib yuborish (Shoot)", callback_data="det_choice_shoot"))
                    kb.adjust(1)
                    await bot.send_message(
                        player.user_id,
                        "🎖️ **Serjant harakati (Komissar vafot etdi, o'rnini egalladingiz!)**:\n"
                        "Bugun tunda nima qilmoqchisiz?",
                        reply_markup=kb.as_markup()
                    )
            elif player.role == "Maniac":
                # Kill target (not self)
                if game.event and game.event["key"] == "curfew":
                    await bot.send_message(player.user_id, "🚨 **Komendantlik soati tufayli bugun ko'chaga chiqa olmaysiz va o'ldirolmaysiz!**")
                else:
                    kb = target_keyboard("maniac", exclude_id=player.user_id)
                    await bot.send_message(player.user_id, "🦹 **Telba (Maniac) qotilligi**: Bugun kimni qurbon qilmoqchisiz?", reply_markup=kb)
        except Exception as e:
            logging.error(f"Error sending night action keyboard to user {player.user_id}: {e}")

    # Set timer for night actions
    night_sec = getattr(game, "night_time", 45)
    game.timer_task = asyncio.create_task(night_timer(bot, game, night_sec))

async def night_timer(bot: Bot, game: Game, seconds: int):
    # Wait for actions or timeout
    for sec in range(seconds, 0, -1):
        if sec % 10 == 0 or sec in [5, 3, 2, 1]:
            try:
                await bot.edit_message_text(
                    chat_id=game.chat_id,
                    message_id=game.night_message_id,
                    text=f"🌙 **Shahar uzra tun cho'kdi... Barcha tinch aholi shirin uyquda. Mafiya va faol rollar tunda uyg'onmoqda.**\n\n"
                         f"_(Harakatlarni bajarish uchun shaxsiy chatga o'ting yoki Mini App-ni oching!)_\n\n"
                         f"⏳ **Tun tugashiga {sec} soniya qoldi...**"
                )
            except Exception:
                pass
        
        # Check if all active players have finished their turns
        # To speed up the night phase
        if all_active_roles_acted(game):
            break
        await asyncio.sleep(1)
        
    await process_night(bot, game)

def all_active_roles_acted(game: Game) -> bool:
    alive_players = game.get_alive_players()
    
    # 1. Mafia & Don vote check
    mafia_count = len([p for p in alive_players if p.role in ["Mafia", "Don"]])
    if mafia_count > 0 and len(game.night_actions["mafia"]) < mafia_count:
        return False
        
    # 2. Don check
    if any(p.role == "Don" for p in alive_players) and game.night_actions.get("don") is None:
        return False
        
    # 3. Detective / Sergeant check or shoot (if not Fog event)
    is_fog = bool(game.event and game.event.get("key") == "fog")
    dets = [p for p in alive_players if p.role == "Detective"]
    if not dets:
        dets = [p for p in alive_players if p.role == "Sergeant"]
    if dets and not is_fog:
        if not game.night_actions.get("detective_check") and not game.night_actions.get("detective_shoot"):
            return False
            
    # 4. Doctor check
    if any(p.role == "Doctor" for p in alive_players) and not game.night_actions.get("doctor"):
        return False
        
    # 5. Bodyguard check
    if any(p.role == "Bodyguard" for p in alive_players) and not game.night_actions.get("bodyguard"):
        return False
        
    # 6. Witch check
    if any(p.role == "Witch" for p in alive_players) and not game.night_actions.get("courtesan"):
        return False
        
    # 7. Lawyer check
    if any(p.role == "Lawyer" for p in alive_players) and not game.night_actions.get("lawyer"):
        return False
        
    # 8. Maniac check (if not Curfew event)
    is_curfew = bool(game.event and game.event.get("key") == "curfew")
    if any(p.role == "Maniac" for p in alive_players) and not is_curfew and not game.night_actions.get("maniac"):
        return False
        
    return True

async def check_and_advance_night_if_ready(bot: Bot, game: Game):
    if game.phase == "night" and all_active_roles_acted(game):
        if game.timer_task and not game.timer_task.done():
            game.timer_task.cancel()
            game.timer_task = None
        await process_night(bot, game)


async def process_night(bot: Bot, game: Game):
    if game.timer_task:
        game.timer_task.cancel()
        game.timer_task = None
        
    # Unmute chat
    await try_mute_chat(bot, game.chat_id, False)
    
    # Initialize victims list at the start of night processing
    victims = []
    
    # Check AFK for active roles
    afk_killed = []
    for player in game.get_alive_players():
        if player.role == "Civilian":
            continue
            
        acted = True
        if player.role == "Mafia" and player.user_id not in game.night_actions["mafia"]:
            acted = False
        elif player.role == "Don" and not game.night_actions["don"]:
            acted = False
        elif player.role == "Detective" and not game.night_actions["detective_check"] and not game.night_actions["detective_shoot"]:
            acted = False
        elif player.role == "Doctor" and not game.night_actions["doctor"]:
            acted = False
        elif player.role == "Bodyguard" and not game.night_actions["bodyguard"]:
            acted = False
        elif player.role == "Witch" and not game.night_actions["courtesan"]:
            acted = False
        elif player.role == "Maniac" and not game.night_actions["maniac"] and not (game.event and game.event["key"] == "curfew"):
            acted = False
            
        if acted:
            player.afk_streak = 0
        else:
            player.afk_streak = getattr(player, "afk_streak", 0) + 1
            if player.afk_streak >= 2:
                player.is_alive = False
                afk_killed.append(player)
                await try_restrict_user(bot, game.chat_id, player.user_id, True)
                
    if afk_killed:
        afk_text = "🚶 **AFK (Faolsizlik) tufayli o'yindan chetlashtirilganlar**:\n"
        for p in afk_killed:
            role_emoji = ROLE_EMOJIS.get(p.role, "")
            afk_text += f"- {p.name_escaped} ({role_emoji} {p.role}): 2 ta bosqichda faolsiz bo'lgani sababli o'yindan chetlashtirildi!\n"
            log_game_event(game, f"🚶 {p.name} AFK sababli chetlashtirildi.")
        await bot.send_message(game.chat_id, afk_text, parse_mode="Markdown")
        
        # Check win conditions immediately
        ended, winner = check_win_conditions(game)
        if ended:
            await end_game(bot, game, winner)
            return
    
    # 1. Apply Witch Block
    blocked_user = game.night_actions["courtesan"]
    if blocked_user:
        # Check if courtesan is alive and not blocked herself (if there could be two courtesans, but we have 1)
        courtesans = game.get_players_by_role("Witch")
        if courtesans and courtesans[0].is_alive:
            target_player = game.players.get(blocked_user)
            if target_player:
                target_player.is_blocked = True
                try:
                    await bot.send_message(target_player.user_id, "🧹 Sizni Jodugar afsunladi, bugungi tungi harakatlaringiz bekor bo'ldi!")
                except Exception:
                    pass
                
    # If blocked, cancel their night actions
    for role_name in ["detective", "doctor", "bodyguard", "maniac", "don"]:
        role_players = game.get_players_by_role(role_name.capitalize())
        if role_players and role_players[0].is_blocked:
            if role_name == "detective":
                game.night_actions["detective_check"] = None
                game.night_actions["detective_shoot"] = None
            else:
                game.night_actions[role_name] = None
    # For mafia (if a mafia member is blocked, they can't vote, but we just check if all are blocked)
    # Actually, we will just filter out votes from blocked mafias
    mafia_members = game.get_players_by_role("Mafia") + game.get_players_by_role("Don")
    blocked_mafia_ids = [m.user_id for m in mafia_members if m.is_blocked]
    
    # 2. Process Doctor Healing
    healed_user = game.night_actions["doctor"]
    if healed_user and not any(p.role == "Doctor" and p.is_blocked for p in game.get_alive_players()):
        healed_player = game.players.get(healed_user)
        if healed_player:
            healed_player.is_healed = True
            game.last_doctor_target = healed_user
    else:
        game.last_doctor_target = None
            
    # 3. Process Bodyguard Protection
    guarded_user = game.night_actions["bodyguard"]
    if guarded_user and not any(p.role == "Bodyguard" and p.is_blocked for p in game.get_alive_players()):
        guarded_player = game.players.get(guarded_user)
        if guarded_player:
            guarded_player.is_guarded = True
            game.last_bodyguard_target = guarded_user
    else:
        game.last_bodyguard_target = None
            
    # 4. Process Detective/Sergeant Check & Shoot
    detective_check = game.night_actions["detective_check"]
    detective_shoot = game.night_actions["detective_shoot"]
    active_det = None
    detectives = [p for p in game.get_alive_players() if p.role == "Detective" and not p.is_blocked]
    if detectives:
        active_det = detectives[0]
    else:
        sergeants = [p for p in game.get_alive_players() if p.role == "Sergeant" and not p.is_blocked]
        if sergeants:
            active_det = sergeants[0]
    
    if active_det:
        # Check action
        if detective_check:
            checked_player = game.players.get(detective_check)
            if checked_player:
                lawyer_target = game.night_actions.get("lawyer")
                lawyers = [p for p in game.get_alive_players() if p.role == "Lawyer" and not p.is_blocked]
                
                if lawyers and checked_player.user_id == lawyer_target:
                    side = "Tinch aholi"
                    show_role = "Civilian"
                else:
                    side = "Mafiya" if checked_player.role in ["Mafia", "Don", "Lawyer"] else "Tinch aholi"
                    if checked_player.role == "Maniac":
                        side = "Telba (Maniac)"
                    show_role = checked_player.role
                    if checked_player.role in ["Mafia", "Don", "Lawyer", "Maniac"]:
                        game.add_mvp_points(active_det.user_id, 20)
                try:
                    await bot.send_message(
                        active_det.user_id,
                        f"🔍 **Tekshiruv natijasi**:\n{checked_player.name_escaped} roli - {ROLE_EMOJIS.get(show_role, '')} **{show_role}** ({side})"
                    )
                except Exception:
                    pass
        # Shoot action
        elif detective_shoot:
            shoot_player = game.players.get(detective_shoot)
            if shoot_player:
                if shoot_player.is_healed:
                    docs = game.get_players_by_role("Doctor")
                    if docs and docs[0].is_alive:
                        game.add_mvp_points(docs[0].user_id, 35)
                elif shoot_player.is_guarded and any(b.is_alive for b in game.get_players_by_role("Bodyguard")):
                    # Bodyguard dies instead
                    bodyguards = game.get_players_by_role("Bodyguard")
                    alive_guards = [b for b in bodyguards if b.is_alive]
                    if alive_guards:
                        bg = alive_guards[0]
                        bg.is_alive = False
                        game.add_mvp_points(bg.user_id, 30)
                        victims.append((bg, "Tansoqchi Komissar o'qidan o'zini fido qildi."))
                else:
                    shoot_player.is_alive = False
                    if shoot_player.role in ["Mafia", "Don", "Lawyer", "Maniac"]:
                        game.add_mvp_points(active_det.user_id, 30)
                    else:
                        game.add_mvp_points(active_det.user_id, -10)
                    victims.append((shoot_player, f"Tunda Komissar to'pponchasidan otib o'ldirildi. Rol: **{shoot_player.role}**"))

    # 5. Process Don Check
    don_check = game.night_actions["don"]
    if don_check:
        dons = game.get_players_by_role("Don")
        if dons and dons[0].is_alive and not dons[0].is_blocked:
            checked_player = game.players.get(don_check)
            if checked_player:
                is_det = checked_player.role in ["Detective", "Sergeant"]
                if is_det:
                    game.add_mvp_points(dons[0].user_id, 25)
                result_text = "Komissar (Detective)!" if is_det else "Komissar emas."
                try:
                    await bot.send_message(
                        dons[0].user_id,
                        f"🔍 **Don tekshiruvi natijasi**:\n{checked_player.name_escaped} - {result_text}"
                    )
                except Exception:
                    pass

    # 6. Calculate Mafia Kill
    mafia_votes = {}
    for voter_id, target_id in game.night_actions["mafia"].items():
        if voter_id not in blocked_mafia_ids:
            mafia_votes[target_id] = mafia_votes.get(target_id, 0) + 1
            
    mafia_kill_target = None
    if mafia_votes:
        max_votes = max(mafia_votes.values())
        mafia_kill_target = random.choice([k for k, v in mafia_votes.items() if v == max_votes])
        
    # 7. Calculate Maniac Kill
    maniac_kill_target = game.night_actions["maniac"]
    
    # Process Mafia Homicide
    if mafia_kill_target:
        victim = game.players.get(mafia_kill_target)
        if victim:
            if victim.is_healed:
                docs = game.get_players_by_role("Doctor")
                if docs and docs[0].is_alive:
                    game.add_mvp_points(docs[0].user_id, 35)
            elif victim.is_guarded and any(b.is_alive for b in game.get_players_by_role("Bodyguard")):
                # Saved by bodyguard, but bodyguard dies instead!
                bodyguards = game.get_players_by_role("Bodyguard")
                alive_guards = [b for b in bodyguards if b.is_alive]
                if alive_guards:
                    bg = alive_guards[0]
                    bg.is_alive = False
                    game.add_mvp_points(bg.user_id, 30)
                    victims.append((bg, "Tansoqchi o'z jonini fido qilib, o'yinchi himoyasida halok bo'ldi."))
            else:
                victim.is_alive = False
                for m in mafia_members:
                    if m.is_alive and not m.is_blocked:
                        game.add_mvp_points(m.user_id, 10)
                victims.append((victim, f"Shafqatsiz mafiya tomonidan o'ldirildi. Rol: **{victim.role}**"))
                
    # Process Maniac Homicide
    if maniac_kill_target:
        victim = game.players.get(maniac_kill_target)
        if victim and victim.is_alive: # If not already killed by Mafia
            if victim.is_healed:
                docs = game.get_players_by_role("Doctor")
                if docs and docs[0].is_alive:
                    game.add_mvp_points(docs[0].user_id, 35)
            elif victim.is_guarded and any(b.is_alive for b in game.get_players_by_role("Bodyguard")):
                bodyguards = game.get_players_by_role("Bodyguard")
                alive_guards = [b for b in bodyguards if b.is_alive]
                if alive_guards:
                    bg = alive_guards[0]
                    bg.is_alive = False
                    game.add_mvp_points(bg.user_id, 30)
                    victims.append((bg, "Tansoqchi Telbaga (Maniac) qarshi kurashib halok bo'ldi."))
            else:
                victim.is_alive = False
                maniacs = game.get_players_by_role("Maniac")
                if maniacs and maniacs[0].is_alive:
                    game.add_mvp_points(maniacs[0].user_id, 20)
                victims.append((victim, f"Maniakning qo'lida jon berdi. Rol: **{victim.role}**"))

    # Mute all night victims
    for vic, _ in victims:
        await try_restrict_user(bot, game.chat_id, vic.user_id, True)

    # Prompt victims for last words
    victim_users = [vic for vic, _ in victims]
    if victim_users:
        # Wait message in group
        await bot.send_message(game.chat_id, "🌅 **Tong otmoqda... Shahar aholisi tungi voqealardan xabar kutmoqda.**\n_(Tunda vafot etganlarning oxirgi so'zlari kutilmoqda...)_")
        
        for vic in victim_users:
            game.waiting_last_words[vic.user_id] = True
            game.last_words[vic.user_id] = None
            try:
                await bot.send_message(
                    vic.user_id,
                    "💀 **Siz bugun tunda halok bo'ldingiz!**\n"
                    "Shahar ahlisiga o'z vasiyatingizni (so'nggi so'zingizni) yozib yuboring.\n"
                    "Sizda **30 soniya** vaqt bor. Yozgan xatingiz guruhda e'lon qilinadi:"
                )
            except Exception as e:
                logging.error(f"Could not send last words prompt to {vic.user_id}: {e}")
                game.waiting_last_words[vic.user_id] = False
                
        # Wait loop (max 30 seconds)
        for _ in range(30):
            still_waiting = [uid for uid, waiting in game.waiting_last_words.items() if waiting]
            if not still_waiting:
                break
            await asyncio.sleep(1)
            
        # Clean up
        for uid in list(game.waiting_last_words.keys()):
            game.waiting_last_words[uid] = False

    # Send Day/Death GIF
    if victims:
        await send_game_gif(bot, game.chat_id, "death")
    else:
        await send_game_gif(bot, game.chat_id, "day")

    # Day announcement text
    day_text = "🌅 **Tong otdi! Darktown shahri uyg'ondi...**\n\n"
    log_game_event(game, "🌅 Kun boshlandi.")
    
    # Check if there is a random event
    game.event = get_random_event()
    if game.event:
        day_text += f"📣 **Bugungi Shahar Hodisasi**:\n**{game.event['name']}**\n_{game.event['description']}_\n\n"
        log_game_event(game, f"📣 Hodisa: {game.event['name']}")
        
    if not victims:
        day_text += "✨ **Ajoyib yangilik! Bugun tunda hech kim halok bo'lmadi.**\n\n"
        log_game_event(game, "✨ Tunda talofatlar bo'lmadi.")
    else:
        day_text += "💀 **Tungi yo'qotishlar**:\n"
        for vic, details in victims:
            role_emoji = ROLE_EMOJIS.get(vic.role, "")
            day_text += f"- {vic.name_escaped} ({role_emoji} {vic.role}): {details}\n"
            log_game_event(game, f"💀 {vic.name} o'ldirildi ({vic.role}).")
        day_text += "\n"
        
        # Add last words
        day_text += "✍️ **Vasiyatnomalar (So'nggi so'zlar)**:\n"
        for vic in victim_users:
            words = game.last_words.get(vic.user_id)
            if words:
                day_text += f"- **{vic.name_escaped}**: _\"{words}\"_\n"
            else:
                day_text += f"- **{vic.name_escaped}**: _(vasiyat qoldirmadi)_\n"
        day_text += "\n"
        
    # Add alive players grid (Tirik o'yinchilar jadvali)
    alive_players = game.get_alive_players()
    day_text += f"👥 **Tirik qolgan o'yinchilar ro'yxati ({len(alive_players)})**:\n"
    for p in alive_players:
        day_text += f"- {p.name_escaped}\n"
            
    await bot.send_message(game.chat_id, day_text, parse_mode="Markdown")
    
    # Check if game ended
    ended, winner = check_win_conditions(game)
    if ended:
        await end_game(bot, game, winner)
    else:
        # Move to discussion phase
        await day_phase(bot, game)

def check_win_conditions(game: Game) -> tuple[bool, Optional[str]]:
    alive = game.get_alive_players()
    mafia = [p for p in alive if p.role in ["Mafia", "Don", "Lawyer"]]
    maniac = [p for p in alive if p.role == "Maniac"]
    jester = [p for p in alive if p.role == "Jester"]
    civilians = [p for p in alive if p.role not in ["Mafia", "Don", "Lawyer", "Maniac", "Jester"]]
    
    # Maniac win condition: Maniac is the last one standing, or only 1 civilian/mafia and 1 maniac left
    if len(maniac) > 0 and len(mafia) == 0 and len(civilians) == 0 and len(jester) == 0:
        return True, "Maniac"
    if len(maniac) == 1 and len(alive) == 2:
        return True, "Maniac"
        
    # Mafia win condition: Mafia count >= Civilian + Maniac + Jester count
    if len(mafia) >= (len(civilians) + len(maniac) + len(jester)):
        return True, "Mafia"
        
    # Civilian win condition: No mafia and no maniac left
    if len(mafia) == 0 and len(maniac) == 0:
        return True, "Civilian"
        
    return False, None

async def day_phase(bot: Bot, game: Game):
    game.phase = "day"
    await try_mute_chat(bot, game.chat_id, False)
    await send_game_gif(bot, game.chat_id, "day")
    day_sec = getattr(game, "day_time", 60)
    msg = await bot.send_message(
        game.chat_id,
        "💬 **Shahar uyg'ondi! Kun boshlandi. Munozara maydoni ochiq.**\n"
        "Shubha ostidagilarni aniqlang, munozara qiling va gumondorlarni o'rtaga chiqaring.\n"
        f"⏳ Ovoz berish bosqichi boshlanishiga **{day_sec} soniya** qoldi."
    )
    game.day_message_id = msg.message_id
    game.timer_task = asyncio.create_task(discussion_timer(bot, game, day_sec))

async def discussion_timer(bot: Bot, game: Game, seconds: int):
    for sec in range(seconds, 0, -1):
        if sec % 10 == 0 or sec in [5, 3, 2, 1]:
            try:
                await bot.edit_message_text(
                    chat_id=game.chat_id,
                    message_id=game.day_message_id,
                    text=f"💬 **Shahar uyg'ondi! Kun boshlandi. Munozara maydoni ochiq.**\n"
                         f"Shubha ostidagilarni aniqlang, munozara qiling va gumondorlarni o'rtaga chiqaring.\n\n"
                         f"⏳ Ovoz berish bosqichi boshlanishiga **{sec} soniya** qoldi."
                )
            except Exception:
                pass
        await asyncio.sleep(1)
    await start_voting_phase(bot, game)

async def start_voting_phase(bot: Bot, game: Game):
    game.phase = "voting"
    game.votes = {}
    await try_mute_chat(bot, game.chat_id, True)
    
    alive = game.get_alive_players()
    
    # Build inline keyboard for voting
    kb = InlineKeyboardBuilder()
    for p in alive:
        kb.add(types.InlineKeyboardButton(text=p.name, callback_data=f"vote_{p.user_id}"))
    kb.add(types.InlineKeyboardButton(text="⏩ Hech kimga", callback_data="vote_skip"))
    kb.adjust(2)
    
    voting_sec = getattr(game, "voting_time", 45)
    vote_msg = await bot.send_message(
        game.chat_id,
        "🗳️ **Ovoz berish boshlandi!**\n"
        "Kimni dorda osmoqchisiz? Quyidagi tugmalardan birini tanlang.\n"
        f"Ovoz berish {voting_sec} soniya davom etadi.",
        reply_markup=kb.as_markup()
    )
    game.vote_message_id = vote_msg.message_id
    game.timer_task = asyncio.create_task(voting_timer(bot, game, voting_sec))

async def voting_timer(bot: Bot, game: Game, seconds: int):
    # Wait for all alive players to vote or timer timeout
    for sec in range(seconds, 0, -1):
        alive_ids = [p.user_id for p in game.get_alive_players()]
        if len(game.votes) >= len(alive_ids):
            break
            
        if sec % 5 == 0 or sec in [5, 3, 2, 1]:
            try:
                # Re-fetch keyboard to preserve it
                alive = game.get_alive_players()
                kb = InlineKeyboardBuilder()
                for p in alive:
                    kb.add(types.InlineKeyboardButton(text=p.name, callback_data=f"vote_{p.user_id}"))
                kb.add(types.InlineKeyboardButton(text="⏩ Hech kimga", callback_data="vote_skip"))
                kb.adjust(2)
                
                await bot.edit_message_text(
                    chat_id=game.chat_id,
                    message_id=game.vote_message_id,
                    text=f"🗳️ **Ovoz berish boshlandi!**\n"
                         f"Kimni dorda osmoqchisiz? Quyidagi tugmalardan birini tanlang.\n\n"
                         f"⏳ **Ovoz berish tugashiga {sec} soniya qoldi...**",
                    reply_markup=kb.as_markup()
                )
            except Exception:
                pass
        await asyncio.sleep(1)
        
    await process_voting(bot, game)

async def process_voting(bot: Bot, game: Game):
    if game.timer_task:
        game.timer_task.cancel()
        game.timer_task = None
        
    # Check AFK for all alive players
    afk_killed = []
    for player in game.get_alive_players():
        voted = player.user_id in game.votes
        if voted:
            player.afk_streak = 0
        else:
            player.afk_streak = getattr(player, "afk_streak", 0) + 1
            if player.afk_streak >= 2:
                player.is_alive = False
                afk_killed.append(player)
                await try_restrict_user(bot, game.chat_id, player.user_id, True)
                
    if afk_killed:
        afk_text = "🚶 **AFK (Faolsizlik) tufayli o'yindan chetlashtirilganlar**:\n"
        for p in afk_killed:
            role_emoji = ROLE_EMOJIS.get(p.role, "")
            afk_text += f"- {p.name} ({role_emoji} {p.role}): 2 ta bosqichda faolsiz bo'lgani sababli o'yindan chetlashtirildi!\n"
            log_game_event(game, f"🚶 {p.name} AFK sababli chetlashtirildi.")
        await bot.send_message(game.chat_id, afk_text, parse_mode="Markdown")
        
        # Check win conditions immediately
        ended, winner = check_win_conditions(game)
        if ended:
            await end_game(bot, game, winner)
            return

    # Remove voting keyboard
    try:
        await bot.edit_message_reply_markup(game.chat_id, game.vote_message_id, reply_markup=None)
    except Exception:
        pass
        
    # Count votes
    # Voter ID -> Target ID
    vote_tally = {}
    for target_id in game.votes.values():
        if target_id != "skip":
            vote_tally[target_id] = vote_tally.get(target_id, 0) + 1
            
    skip_votes = len([v for v in game.votes.values() if v == "skip"])
    
    # Announce results
    result_text = "🗳️ **Ovoz berish natijalari**:\n"
    
    # Group results
    for target_id, count in vote_tally.items():
        tgt_player = game.players.get(target_id)
        if tgt_player:
            result_text += f"- {tgt_player.name}: {count} ta ovoz\n"
    if skip_votes:
        result_text += f"- Hech kimga: {skip_votes} ta ovoz\n"
        
    if not vote_tally:
        result_text += "\n🤷‍♂️ Hech kim ovoz bermadi. Bugun hech kim osilmaydi."
        log_game_event(game, "🤷‍♂️ Ovozlar berilmadi, hech kim osilmadi.")
        await bot.send_message(game.chat_id, result_text)
        # Go to next night
        await start_next_night(bot, game)
        return
        
    # Find max votes
    max_votes = max(vote_tally.values())
    
    if game.event and game.event["key"] == "election":
        vote_tally = {}
        for voter_id, target_id in game.votes.items():
            if target_id != "skip":
                voter_p = game.players.get(voter_id)
                power = 2 if (voter_p and voter_p.role == "Civilian") else 1
                vote_tally[target_id] = vote_tally.get(target_id, 0) + power
        if vote_tally:
            max_votes = max(vote_tally.values())
            
    top_candidates = [k for k, v in vote_tally.items() if v == max_votes]
    
    if len(top_candidates) > 1:
        if game.event and game.event["key"] == "anarchy":
            hanged_id = random.choice(top_candidates)
            hanged_player = game.players[hanged_id]
            hanged_player.is_alive = False
            await try_restrict_user(bot, game.chat_id, hanged_player.user_id, True)
            await send_game_gif(bot, game.chat_id, "hang")
            role_emoji = ROLE_EMOJIS.get(hanged_player.role, "")
            result_text += (
                f"\n🔥 **Anarxiya voqeasi sababli ovozlar teng bo'lsa-da, tasodifiy ravishda {hanged_player.name_escaped} osildi!**\n"
                f"Uning roli: {role_emoji} **{hanged_player.role}**"
            )
        else:
            result_text += "\n⚖️ Ovozlar teng bo'lib qoldi. Bugun hech kim osilmaydi."
            log_game_event(game, "⚖️ Ovozlar teng, hech kim osilmadi.")
    else:
        hanged_id = top_candidates[0]
        if skip_votes >= max_votes:
            result_text += "\n⏩ Ko'pchilik ovoz bermaslikni tanladi. Bugun hech kim osilmaydi."
            log_game_event(game, "⏩ Ovoz berilmaslik tanlandi, hech kim osilmadi.")
        else:
            hanged_player = game.players[hanged_id]
            hanged_player.is_alive = False
            await try_restrict_user(bot, game.chat_id, hanged_player.user_id, True)
            await send_game_gif(bot, game.chat_id, "hang")
            role_emoji = ROLE_EMOJIS.get(hanged_player.role, "")
            
            if hanged_player.role == "Jester":
                game.add_mvp_points(hanged_player.user_id, 100)
                result_text += (
                    f"\n⚖️ Ko'pchilikning qarori bilan **{hanged_player.name_escaped}** dorga osildi!\n\n"
                    f"🃏 **DORGA OSILGAN SHAXS — MAZXARABOZ (JESTER)!**\n"
                    f"U shaharni aldashga erishdi va **yagona g'olib**ga aylandi! 🎉"
                )
                log_game_event(game, f"🃏 Mazxaraboz {hanged_player.name} dorda osilib g'olib bo'ldi!")
                await bot.send_message(game.chat_id, result_text, parse_mode="Markdown")
                await end_game(bot, game, "Jester")
                return
            else:
                if hanged_player.role in ["Mafia", "Don", "Lawyer", "Maniac"]:
                    for voter_id, target_id in game.votes.items():
                        if target_id == hanged_id:
                            game.add_mvp_points(voter_id, 15)
                result_text += (
                    f"\n⚖️ Ko'pchilikning qarori bilan **{hanged_player.name_escaped}** dorga osildi!\n"
                    f"Uning roli: {role_emoji} **{hanged_player.role}**"
                )
                log_game_event(game, f"⚖️ {hanged_player.name} dorda osildi ({hanged_player.role}).")
            
    await bot.send_message(game.chat_id, result_text, parse_mode="Markdown")
    
    # Check if game ended
    ended, winner = check_win_conditions(game)
    if ended:
        await end_game(bot, game, winner)
    else:
        await start_next_night(bot, game)

async def start_next_night(bot: Bot, game: Game):
    await bot.send_message(game.chat_id, "🌙 **Tungi sokinlik qaytmoqda...** Tun boshlanmoqda.")
    await asyncio.sleep(5)
    await night_phase(bot, game)

async def end_game(bot: Bot, game: Game, winning_faction: str):
    game.phase = "ended"
    log_game_event(game, f"🏁 O'yin yakunlandi! G'olib: {winning_faction}")
    await try_mute_chat(bot, game.chat_id, False)
    
    # Unmute all players individually (remove restrictions)
    for p in game.players.values():
        await try_restrict_user(bot, game.chat_id, p.user_id, False)
        
    await send_game_gif(bot, game.chat_id, f"win_{winning_faction.lower()}")
    
    faction_emojis = {
        "Mafia": "🔴 Mafiya",
        "Civilian": "🟢 Tinch Aholi",
        "Maniac": "🦹 Telba (Maniac)",
        "Jester": "🃏 Mazxaraboz (Jester)"
    }
    
    event_coins = 0
    rewards_text = "💰 **Mukofotlar (XP & Tangalar)**:\n"
    
    # Calculate MVP (Most Valuable Player)
    mvp_user_id = None
    if hasattr(game, "mvp_points") and game.mvp_points:
        best_id = max(game.mvp_points, key=game.mvp_points.get)
        if game.mvp_points[best_id] > 0:
            mvp_user_id = best_id
    
    for player in game.players.values():
        is_winner = False
        if winning_faction == "Mafia" and player.role in ["Mafia", "Don", "Lawyer"]:
            is_winner = True
        elif winning_faction == "Civilian" and player.role not in ["Mafia", "Don", "Lawyer", "Maniac", "Jester"]:
            is_winner = True
        elif winning_faction == "Maniac" and player.role == "Maniac":
            is_winner = True
        elif winning_faction == "Jester" and player.role == "Jester":
            is_winner = True
            
        # Standard reward
        if is_winner:
            if player.role in ["Maniac", "Jester"]:
                xp = 200
                coins = 100
            else:
                xp = 100
                coins = 50
        else:
            xp = 20
            coins = 10
            
        # Add event bonus
        coins += event_coins
        
        # Add MVP bonus
        is_mvp = (player.user_id == mvp_user_id)
        if is_mvp:
            xp += 50
            coins += 25
            
        user_db = await db.get_user(player.user_id)
        if not is_winner and user_db.get("shield_active", 0) == 1:
            xp += 30
            await db.set_shield(player.user_id, False) # Consume shield
            if is_mvp:
                rewards_text += f"- 🌟 **{player.name_escaped}** (👑 MVP): +{xp} XP (🛡️ Qalqon + MVP), +{coins} tanga\n"
            else:
                rewards_text += f"- {player.name_escaped}: +{xp} XP (🛡️ Qalqon ishlatildi), +{coins} tanga\n"
        else:
            if is_mvp:
                rewards_text += f"- 🌟 **{player.name_escaped}** (👑 MVP): +{xp} XP (+50 MVP), +{coins} tanga (+25 MVP)\n"
            else:
                rewards_text += f"- {player.name_escaped}: +{xp} XP, +{coins} tanga\n"
            
        # Save to DB
        leveled_up, new_level = await db.add_xp_and_coins(player.user_id, xp, coins)
        if leveled_up:
            try:
                await bot.send_message(player.user_id, f"🎉 **Tabriklaymiz!** Siz {new_level}-darajaga (Level) ko'tarildingiz!")
            except Exception:
                pass
            
        # Update Role stats
        await db.update_stats(player.user_id, player.role.lower(), is_winner)

        # Save Game History & Update Achievements/Quests
        try:
            win_val = 1 if is_winner else 0
            await db.save_game_history(player.user_id, str(game.chat_id), player.role, win_val, winning_faction)
            await db.increment_daily_games(player.user_id)
            if is_winner:
                await db.unlock_achievement(player.user_id, "first_win")
                if player.role not in ["Mafia", "Don", "Maniac"]:
                    await db.increment_daily_mafia_killed(player.user_id)
            
            await db.add_clan_points(player.user_id, points=(25 if is_winner else 5), is_win=is_winner)
            
            is_tourney = getattr(game, "is_tournament", False)
            if is_tourney or await db.is_user_registered_for_tournament(player.user_id):
                t_points = 100 if is_winner else 20
                if player.role in ["Don", "Detective"]:
                    t_points += 50
                await db.add_tournament_points(player.user_id, t_points)
            
            await db.add_battle_pass_xp(player.user_id, xp_gain=(50 if is_winner else 15))
        except Exception as ex:
            logging.error(f"Error saving game history/achievements: {ex}")

    # Record group statistics for leaderboard
    if game.chat_id < 0:
        try:
            chat_info = await bot.get_chat(game.chat_id)
            await db.record_group_game(
                chat_id=game.chat_id,
                title=chat_info.title or "",
                username=chat_info.username or "",
                players_count=len(game.players)
            )
        except Exception as ex:
            logging.warning(f"Could not update group stats for chat {game.chat_id}: {ex}")
        
    recap_kb = InlineKeyboardBuilder()
    recap_kb.add(types.InlineKeyboardButton(text="🔄 Yana o'ynash (/newgame)", callback_data="replay_newgame"))
    recap_kb.adjust(1)
    
    mvp_banner = ""
    if mvp_user_id and mvp_user_id in game.players:
        mvp_p = game.players[mvp_user_id]
        role_emoji = ROLE_EMOJIS.get(mvp_p.role, "")
        mvp_banner = f"👑 **O'YIN QAHRAMONI (MVP):** {mvp_p.name_escaped} ({role_emoji} {mvp_p.role}) — +50 XP va +25 Tanga!\n\n"

    final_text = (
        f"🎉 **O'yin yakunlandi!**\n\n"
        f"🏆 G'olib tomon: **{faction_emojis.get(winning_faction, winning_faction)}**\n\n"
        f"{mvp_banner}"
        f"🎭 **Barcha o'yinchilarning rollari**:\n"
    )
    for p in game.players.values():
        status = "🟢 Tirik" if p.is_alive else "💀 Halok bo'lgan"
        role_emoji = ROLE_EMOJIS.get(p.role, "")
        final_text += f"- **{p.name_escaped}**: {role_emoji} {p.role} ({status})\n"
        
    final_text += f"\n{rewards_text}\n"
    final_text += "🔥 Keyingi o'yinni boshlash uchun pastdagi tugmani bosing!"
    
    await bot.send_message(game.chat_id, final_text, reply_markup=recap_kb.as_markup(), parse_mode="Markdown")
    
    # Reset room in DB back to lobby and schedule 5-minute auto-close timer
    room_id = getattr(game, 'room_id', None)
    if room_id:
        async def reset_room_to_lobby():
            try:
                import aiosqlite
                # Reset room status to lobby in SQLite
                async with aiosqlite.connect(db.DB_PATH) as conn:
                    await conn.execute("UPDATE rooms SET status = 'lobby' WHERE room_id = ?", (room_id,))
                    await conn.execute("UPDATE room_players SET role = 'Civilian', is_alive = 1, afk_streak = 0 WHERE room_id = ?", (room_id,))
                    await conn.commit()
                
                # Sleep for 5 minutes (300 seconds)
                await asyncio.sleep(300)
                
                # Check if still in lobby and auto-close if inactive
                async with aiosqlite.connect(db.DB_PATH) as conn:
                    conn.row_factory = aiosqlite.Row
                    async with conn.execute("SELECT status FROM rooms WHERE room_id = ?", (room_id,)) as cursor:
                        row = await cursor.fetchone()
                        if row and row['status'] == 'lobby':
                            await conn.execute("UPDATE rooms SET status = 'finished' WHERE room_id = ?", (room_id,))
                            await conn.execute("DELETE FROM room_players WHERE room_id = ?", (room_id,))
                            await conn.commit()
                            logging.info(f"Room {room_id} auto-closed after 5 minutes of inactivity.")
            except Exception as e:
                logging.error(f"Error resetting room {room_id} to lobby: {e}")
                
        asyncio.create_task(reset_room_to_lobby())
        
    # Trigger DB backup to Telegram channel
    asyncio.create_task(db.save_db_backup(bot))
    
    # Remove game
    game_manager.remove_game(game.chat_id)
