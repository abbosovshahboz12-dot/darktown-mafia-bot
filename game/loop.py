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
    "Civilian": "🟢",
    "Detective": "🔵",
    "Doctor": "🟡",
    "Bodyguard": "🛡️",
    "Courtesan": "🌸",
    "Maniac": "🦹"
}

def get_role_details(role: str) -> str:
    details = {
        "Mafia": "🔴 **Mafiya**: Siz qorong'u kuchlar a'zosiz. Har kecha o'z sheriklaringiz bilan kelishgan holda shaharliklardan birini o'ldirishga ovoz berasiz.",
        "Don": "🕶️ **Don**: Mafiya yetakchisi. Har kecha Komissar (Detective) kimligini bilish uchun o'yinchilardan birini tekshirishingiz mumkin. Shuningdek, mafiya ovoz berishida ishtirok etasiz.",
        "Civilian": "🟢 **Tinch aholi**: Oddiy shahar fuqarosi. Maqsadingiz - kunduzi munozaralar orqali shubhali shaxslarni aniqlash va ularni dorda osish uchun ovoz berish.",
        "Detective": "🔵 **Komissar**: Qonun himoyachisi. Har kecha o'yinchilardan birini tekshirib, uning mafiya yoki tinch aholi ekanligini bilib olasiz.",
        "Doctor": "🟡 **Shifokor**: Har kecha bir o'yinchini davolaysiz. Agar u tunda hujumga uchrasa, tirik qoladi. Ketma-ket o'zini yoki bir odamni davolay olmaydi.",
        "Bodyguard": "🛡️ **Tansoqchi**: Har kecha bir o'yinchini himoya qilasiz. Agar unga hujum bo'lsa, siz uning o'rniga halok bo'lasiz.",
        "Courtesan": "🌸 **Kutizanka**: Har kecha bir o'yinchini jalb qilib, uning tungi qobiliyatini bloklaysiz. Bloklangan o'yinchi tunda hech qanday ish qila olmaydi.",
        "Maniac": "🦹 **Telba (Maniac)**: Yolg'iz qotil. Maqsadingiz - barcha o'yinchilarni o'ldirish va yagona tirik qolgan odam bo'lish. Tunda xohlagan odamingizni o'ldirasiz."
    }
    return details.get(role, "")

def distribute_roles(players_count: int) -> List[str]:
    # Custom role distribution logic based on player count (minimum 5)
    if players_count < 5:
        return ["Mafia", "Doctor", "Detective", "Civilian", "Civilian"]
    elif players_count == 5:
        return ["Mafia", "Doctor", "Detective", "Civilian", "Civilian"]
    elif players_count == 6:
        return ["Mafia", "Don", "Doctor", "Detective", "Civilian", "Civilian"]
    elif players_count == 7:
        return ["Mafia", "Don", "Doctor", "Detective", "Bodyguard", "Civilian", "Civilian"]
    elif players_count == 8:
        return ["Mafia", "Mafia", "Don", "Doctor", "Detective", "Bodyguard", "Civilian", "Civilian"]
    elif players_count == 9:
        return ["Mafia", "Mafia", "Don", "Doctor", "Detective", "Bodyguard", "Courtesan", "Civilian", "Civilian"]
    elif 10 <= players_count < 15:
        base = ["Mafia", "Mafia", "Don", "Maniac", "Doctor", "Detective", "Bodyguard", "Courtesan", "Civilian", "Civilian"]
        while len(base) < players_count:
            base.append("Civilian")
        return base
    else: # 15+ players: 3 Mafia, 1 Don, 1 Maniac, 1 Doctor, 1 Detective, 1 Bodyguard, 1 Courtesan, remaining Civilians
        base = ["Mafia", "Mafia", "Mafia", "Don", "Maniac", "Doctor", "Detective", "Bodyguard", "Courtesan", "Civilian", "Civilian", "Civilian", "Civilian", "Civilian", "Civilian"]
        while len(base) < players_count:
            base.append("Civilian")
        return base

async def assign_roles(game: Game, bot: Bot):
    players = list(game.players.values())
    num_players = len(players)
    roles_pool = distribute_roles(num_players)
    
    # Shuffle roles pool
    random.shuffle(roles_pool)
    
    # Assign based on boosters first
    assigned_players = set()
    for player in players:
        if player.role_booster and player.role_booster in roles_pool:
            player.role = player.role_booster
            roles_pool.remove(player.role_booster)
            assigned_players.add(player.user_id)
            # Remove booster card from database since they used it
            await db.use_item(player.user_id, f"booster_{player.role_booster.lower()}")
            
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

async def start_game_loop(bot: Bot, game: Game):
    # Assign roles
    await assign_roles(game, bot)
    await bot.send_message(
        game.chat_id,
        "🎭 **Rollar taqsimlandi!** Har bir o'yinchiga o'z roli shaxsiy chatda yuborildi.\n\n"
        "🌙 **Qorong'u tushmoqda... Tun boshlandi!**\n"
        "Barcha o'yinchilar shaxsiy chatda bot yuborgan xabarlarga qarab harakat qilsin."
    )
    await night_phase(bot, game)

async def night_phase(bot: Bot, game: Game):
    game.phase = "night"
    
    # Send group night announcement
    await bot.send_message(
        game.chat_id,
        "🌙 **Shahar uzra tun cho'kdi... Barcha tinch aholi shirin uyquda. Mafiya va faol rollar tunda uyg'onmoqda.**\n\n"
        "_(Harakatlarni bajarish uchun shaxsiy chatga o'ting yoki Mini App-ni oching!)_"
    )
    
    # Mute group chat
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
                kb = InlineKeyboardBuilder()
                for p in alive_players:
                    if p.user_id not in mafia_and_don:
                        kb.add(types.InlineKeyboardButton(text=p.name, callback_data=f"don_{p.user_id}"))
                kb.adjust(2)
                await bot.send_message(player.user_id, "🕶️ **Don tekshiruvi**: Komissarni topish uchun kimni tekshirmoqchisiz?", reply_markup=kb.as_markup())
                
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
                
            elif player.role == "Courtesan":
                # Block target (not self)
                kb = target_keyboard("block", exclude_id=player.user_id)
                await bot.send_message(player.user_id, "🌸 **Kutizanka jalb qilishi**: Tungi qobiliyatini cheklamoqchi bo'lgan o'yinchini tanlang:", reply_markup=kb)
                
            elif player.role == "Maniac":
                # Kill target (not self)
                # Curfew event check
                if game.event and game.event["key"] == "curfew":
                    await bot.send_message(player.user_id, "🚨 **Komendantlik soati tufayli bugun ko'chaga chiqa olmaysiz va o'ldirolmaysiz!**")
                else:
                    kb = target_keyboard("maniac", exclude_id=player.user_id)
                    await bot.send_message(player.user_id, "🦹 **Telba (Maniac) qotilligi**: Bugun kimni qurbon qilmoqchisiz?", reply_markup=kb)
        except Exception as e:
            logging.error(f"Error sending night action keyboard to user {player.user_id}: {e}")

    # Set timer for night actions (60 seconds)
    game.timer_task = asyncio.create_task(night_timer(bot, game, 60))

async def night_timer(bot: Bot, game: Game, seconds: int):
    # Wait for actions or timeout
    for sec in range(seconds, 0, -1):
        # We can optionally edit a message in group with the remaining time
        # E.g. every 15 seconds
        if sec in [45, 30, 15, 5]:
            await bot.send_message(game.chat_id, f"🌙 Tun tugashiga {sec} soniya qoldi...")
        
        # Check if all active players have finished their turns
        # To speed up the night phase
        if all_active_roles_acted(game):
            break
        await asyncio.sleep(1)
        
    await process_night(bot, game)

def all_active_roles_acted(game: Game) -> bool:
    alive_players = game.get_alive_players()
    mafia_count = len([p for p in alive_players if p.role in ["Mafia", "Don"]])
    doctor_alive = any(p.role == "Doctor" for p in alive_players)
    detective_alive = any(p.role == "Detective" for p in alive_players)
    guard_alive = any(p.role == "Bodyguard" for p in alive_players)
    courtesan_alive = any(p.role == "Courtesan" for p in alive_players)
    maniac_alive = any(p.role == "Maniac" for p in alive_players)

    # Check if they have chosen
    if len(game.night_actions["mafia"]) < mafia_count:
        return False
    if detective_alive and not game.night_actions["detective_check"] and not game.night_actions["detective_shoot"]:
        return False
    if don_alive := any(p.role == "Don" for p in alive_players):
        if not game.night_actions["don"]:
            return False
    if doctor_alive and not game.night_actions["doctor"]:
        return False
    if guard_alive and not game.night_actions["bodyguard"]:
        return False
    if courtesan_alive and not game.night_actions["courtesan"]:
        return False
    if maniac_alive and not game.night_actions["maniac"] and not (game.event and game.event["key"] == "curfew"):
        return False
        
    return True

async def process_night(bot: Bot, game: Game):
    if game.timer_task:
        game.timer_task.cancel()
        game.timer_task = None
        
    # Unmute chat
    await try_mute_chat(bot, game.chat_id, False)
    
    # 1. Apply Courtesan Block
    blocked_user = game.night_actions["courtesan"]
    if blocked_user:
        # Check if courtesan is alive and not blocked herself (if there could be two courtesans, but we have 1)
        courtesans = game.get_players_by_role("Courtesan")
        if courtesans and courtesans[0].is_alive:
            target_player = game.players.get(blocked_user)
            if target_player:
                target_player.is_blocked = True
                try:
                    await bot.send_message(target_player.user_id, "🌸 Sizni Kutizanka jalb qildi, bugungi tungi harakatlaringiz bekor bo'ldi!")
                except Exception:
                    pass
                
    # If blocked, cancel their night actions
    for role_name in ["detective", "doctor", "bodyguard", "maniac", "don"]:
        role_players = game.get_players_by_role(role_name.capitalize())
        if role_players and role_players[0].is_blocked:
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
            
    # 4. Process Detective Check & Shoot
    detective_check = game.night_actions["detective_check"]
    detective_shoot = game.night_actions["detective_shoot"]
    detectives = game.get_players_by_role("Detective")
    
    if detectives and detectives[0].is_alive and not detectives[0].is_blocked:
        # Check action
        if detective_check:
            checked_player = game.players.get(detective_check)
            if checked_player:
                side = "Mafiya" if checked_player.role in ["Mafia", "Don"] else "Tinch aholi"
                if checked_player.role == "Maniac":
                    side = "Telba (Maniac)"
                try:
                    await bot.send_message(
                        detectives[0].user_id,
                        f"🔍 **Tekshiruv natijasi**:\n{checked_player.name} roli - {ROLE_EMOJIS.get(checked_player.role, '')} **{checked_player.role}** ({side})"
                    )
                except Exception:
                    pass
        # Shoot action
        elif detective_shoot:
            shoot_player = game.players.get(detective_shoot)
            if shoot_player:
                if shoot_player.is_healed:
                    pass # Saved by doctor
                elif shoot_player.is_guarded:
                    # Bodyguard dies instead
                    bodyguards = game.get_players_by_role("Bodyguard")
                    alive_guards = [b for b in bodyguards if b.is_alive]
                    if alive_guards:
                        bg = alive_guards[0]
                        bg.is_alive = False
                        victims.append((bg, "Tansoqchi Komissar o'qidan o'zini fido qildi."))
                else:
                    shoot_player.is_alive = False
                    victims.append((shoot_player, f"Tunda Komissar to'pponchasidan otib o'ldirildi. Rol: **{shoot_player.role}**"))

    # 5. Process Don Check
    don_check = game.night_actions["don"]
    if don_check:
        dons = game.get_players_by_role("Don")
        if dons and dons[0].is_alive and not dons[0].is_blocked:
            checked_player = game.players.get(don_check)
            if checked_player:
                is_det = checked_player.role == "Detective"
                result_text = "Komissar (Detective)!" if is_det else "Komissar emas."
                try:
                    await bot.send_message(
                        dons[0].user_id,
                        f"🔍 **Don tekshiruvi natijasi**:\n{checked_player.name} - {result_text}"
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
    
    # Process victims
    victims = []
    
    # Process Mafia Homicide
    if mafia_kill_target:
        victim = game.players.get(mafia_kill_target)
        if victim:
            if victim.is_healed:
                pass # Saved by doctor
            elif victim.is_guarded:
                # Saved by bodyguard, but bodyguard dies instead!
                bodyguards = game.get_players_by_role("Bodyguard")
                alive_guards = [b for b in bodyguards if b.is_alive]
                if alive_guards:
                    bg = alive_guards[0]
                    bg.is_alive = False
                    victims.append((bg, "Tansoqchi o'z jonini fido qilib, o'yinchi himoyasida halok bo'ldi."))
            else:
                victim.is_alive = False
                victims.append((victim, f"Shafqatsiz mafiya tomonidan o'ldirildi. Rol: **{victim.role}**"))
                
    # Process Maniac Homicide
    if maniac_kill_target:
        victim = game.players.get(maniac_kill_target)
        if victim and victim.is_alive: # If not already killed by Mafia
            if victim.is_healed:
                pass
            elif victim.is_guarded:
                bodyguards = game.get_players_by_role("Bodyguard")
                alive_guards = [b for b in bodyguards if b.is_alive]
                if alive_guards:
                    bg = alive_guards[0]
                    bg.is_alive = False
                    victims.append((bg, "Tansoqchi Telbaga (Maniac) qarshi kurashib halok bo'ldi."))
            else:
                victim.is_alive = False
                victims.append((victim, f"Maniakning qo'lida jon berdi. Rol: **{victim.role}**"))

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

    # Day announcement text
    day_text = "🌅 **Tong otdi! Darktown shahri uyg'ondi...**\n\n"
    
    # Check if there is a random event
    game.event = get_random_event()
    if game.event:
        day_text += f"📣 **Bugungi Shahar Hodisasi**:\n**{game.event['name']}**\n_{game.event['description']}_\n\n"
        
    if not victims:
        day_text += "✨ **Ajoyib yangilik! Bugun tunda hech kim halok bo'lmadi.**\n\n"
    else:
        day_text += "💀 **Tungi yo'qotishlar**:\n"
        for vic, details in victims:
            role_emoji = ROLE_EMOJIS.get(vic.role, "")
            day_text += f"- {vic.name} ({role_emoji} {vic.role}): {details}\n"
        day_text += "\n"
        
        # Add last words
        day_text += "✍️ **Vasiyatnomalar (So'nggi so'zlar)**:\n"
        for vic in victim_users:
            words = game.last_words.get(vic.user_id)
            if words:
                day_text += f"- **{vic.name}**: _\"{words}\"_\n"
            else:
                day_text += f"- **{vic.name}**: _(vasiyat qoldirmadi)_\n"
        day_text += "\n"
        
    # Add alive players grid (Tirik o'yinchilar jadvali)
    alive_players = game.get_alive_players()
    day_text += f"👥 **Tirik qolgan o'yinchilar ro'yxati ({len(alive_players)})**:\n"
    for p in alive_players:
        day_text += f"- {p.name}\n"
            
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
    mafia = [p for p in alive if p.role in ["Mafia", "Don"]]
    maniac = [p for p in alive if p.role == "Maniac"]
    civilians = [p for p in alive if p.role not in ["Mafia", "Don", "Maniac"]]
    
    # Maniac win condition: Maniac is the last one standing, or only 1 civilian/mafia and 1 maniac left
    if len(maniac) > 0 and len(mafia) == 0 and len(civilians) == 0:
        return True, "Maniac"
    if len(maniac) == 1 and len(alive) == 2:
        return True, "Maniac"
        
    # Mafia win condition: Mafia count >= Civilian + Maniac count
    if len(mafia) >= (len(civilians) + len(maniac)):
        return True, "Mafia"
        
    # Civilian win condition: No mafia and no maniac left
    if len(mafia) == 0 and len(maniac) == 0:
        return True, "Civilian"
        
    return False, None

async def day_phase(bot: Bot, game: Game):
    game.phase = "day"
    await try_mute_chat(bot, game.chat_id, False)
    await bot.send_message(
        game.chat_id,
        "💬 **Shahar uyg'ondi! Kun boshlandi. Munozara maydoni ochiq.**\n"
        "Shubha ostidagilarni aniqlang, munozara qiling va gumondorlarni o'rtaga chiqaring.\n"
        "⏳ Ovoz berish bosqichi boshlanishiga **60 soniya** qoldi."
    )
    game.timer_task = asyncio.create_task(discussion_timer(bot, game, 60))

async def discussion_timer(bot: Bot, game: Game, seconds: int):
    await asyncio.sleep(seconds)
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
    
    vote_msg = await bot.send_message(
        game.chat_id,
        "🗳️ **Ovoz berish boshlandi!**\n"
        "Kimni dorda osmoqchisiz? Quyidagi tugmalardan birini tanlang.\n"
        "Ovoz berish 45 soniya davom etadi.",
        reply_markup=kb.as_markup()
    )
    game.vote_message_id = vote_msg.message_id
    game.timer_task = asyncio.create_task(voting_timer(bot, game, 45))

async def voting_timer(bot: Bot, game: Game, seconds: int):
    # Wait for all alive players to vote or timer timeout
    for sec in range(seconds, 0, -1):
        alive_ids = [p.user_id for p in game.get_alive_players()]
        if len(game.votes) >= len(alive_ids):
            break
        await asyncio.sleep(1)
        
    await process_voting(bot, game)

async def process_voting(bot: Bot, game: Game):
    if game.timer_task:
        game.timer_task.cancel()
        game.timer_task = None
        
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
        await bot.send_message(game.chat_id, result_text)
        # Go to next night
        await start_next_night(bot, game)
        return
        
    # Find max votes
    max_votes = max(vote_tally.values())
    
    # Event check: election (civilians double vote power)
    # Actually, we can implement it by recalculating votes if event election:
    if game.event and game.event["key"] == "election":
        # Recalculate tally with double power for Civilians
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
        # Tie!
        if game.event and game.event["key"] == "anarchy":
            # Randomly hang one of them
            hanged_id = random.choice(top_candidates)
            hanged_player = game.players[hanged_id]
            hanged_player.is_alive = False
            role_emoji = ROLE_EMOJIS.get(hanged_player.role, "")
            result_text += (
                f"\n🔥 **Anarxiya voqeasi sababli ovozlar teng bo'lsa-da, tasodifiy ravishda {hanged_player.name} osildi!**\n"
                f"Uning roli: {role_emoji} **{hanged_player.role}**"
            )
        else:
            result_text += "\n⚖️ Ovozlar teng bo'lib qoldi. Bugun hech kim osilmaydi."
    else:
        hanged_id = top_candidates[0]
        # Check if skip votes are greater than candidate votes
        if skip_votes >= max_votes:
            result_text += "\n⏩ Ko'pchilik ovoz bermaslikni tanladi. Bugun hech kim osilmaydi."
        else:
            hanged_player = game.players[hanged_id]
            hanged_player.is_alive = False
            role_emoji = ROLE_EMOJIS.get(hanged_player.role, "")
            result_text += (
                f"\n⚖️ Ko'pchilikning qarori bilan **{hanged_player.name}** dorga osildi!\n"
                f"Uning roli: {role_emoji} **{hanged_player.role}**"
            )
            
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
    await try_mute_chat(bot, game.chat_id, False)
    
    faction_emojis = {
        "Mafia": "🔴 Mafiya",
        "Civilian": "🟢 Tinch Aholi",
        "Maniac": "🦹 Telba (Maniac)"
    }
    
    win_text = f"🎉 **O'yin yakunlandi!**\n\nG'olib tomon: **{faction_emojis.get(winning_faction, winning_faction)}**\n\n"
    
    win_text += "📋 **O'yinchilar rollari**:\n"
    for p in game.players.values():
        status = "🟢 Tirik" if p.is_alive else "💀 O'lik"
        role_emoji = ROLE_EMOJIS.get(p.role, "")
        win_text += f"- {p.name}: {role_emoji} {p.role} ({status})\n"
        
    await bot.send_message(game.chat_id, win_text, parse_mode="Markdown")
    
    # Calculate XP and Coins
    # Yarmarka event bonus
    event_coins = 30 if (game.event and game.event["key"] == "fair") else 0
    
    rewards_text = "💰 **Mukofotlar (XP & Tangalar)**:\n"
    
    for player in game.players.values():
        is_winner = False
        if winning_faction == "Mafia" and player.role in ["Mafia", "Don"]:
            is_winner = True
        elif winning_faction == "Civilian" and player.role not in ["Mafia", "Don", "Maniac"]:
            is_winner = True
        elif winning_faction == "Maniac" and player.role == "Maniac":
            is_winner = True
            
        # Standard reward
        if is_winner:
            if player.role == "Maniac":
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
        
        # Check shield if user lost
        # If user has active shield, and they lost, they don't lose anything (actually we don't deduct XP on loss anyway, but shield saves them from losing streaks or could double rewards, let's say shield doubles coins for winner, or shields losses)
        # Actually, let's implement shield: if they lost, they get +30 XP bonus (saving them from loss disappointment)
        user_db = await db.get_user(player.user_id)
        if not is_winner and user_db.get("shield_active", 0) == 1:
            xp += 30
            await db.set_shield(player.user_id, False) # Consume shield
            rewards_text += f"- {player.name}: +{xp} XP (🛡️ Qalqon ishlatildi), +{coins} tanga\n"
        else:
            rewards_text += f"- {player.name}: +{xp} XP, +{coins} tanga\n"
            
        # Save to DB
        leveled_up, new_level = await db.add_xp_and_coins(player.user_id, xp, coins)
        if leveled_up:
            await bot.send_message(player.user_id, f"🎉 **Tabriklaymiz!** Siz {new_level}-darajaga (Level) ko'tarildingiz!")
            
        # Update Role stats
        await db.update_stats(player.user_id, player.role.lower(), is_winner)
        
    await bot.send_message(game.chat_id, rewards_text, parse_mode="Markdown")
    
    # Remove game
    game_manager.remove_game(game.chat_id)
