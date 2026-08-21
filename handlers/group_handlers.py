import asyncio
import logging
from aiogram import Router, F, Bot, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from game.manager import game_manager
from game.loop import start_game_loop
from game.models import Player, Game
from database import db
from locales import get_text
from config import ADMIN_ID

router = Router()

# Only process group and supergroup messages
router.message.filter(F.chat.type.in_({"group", "supergroup"}))

@router.message(F.new_chat_members)
async def on_new_chat_members(message: types.Message, bot: Bot):
    inviter_id = message.from_user.id
    new_members = message.new_chat_members
    human_members = [m for m in new_members if not m.is_bot]
    if human_members and inviter_id:
        await db.track_group_invite(bot, inviter_id, len(human_members))

def get_lobby_keyboard(lang: str) -> types.InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.add(types.InlineKeyboardButton(
        text="📥 Join Game" if lang == "en" else "📥 Присоединиться" if lang == "ru" else "📥 Ойынға қосылу" if lang == "kz" else "📥 O'yinga qo'shilish", 
        callback_data="join_game"
    ))
    kb.add(types.InlineKeyboardButton(
        text="🚀 Start Game" if lang == "en" else "🚀 Начать игру" if lang == "ru" else "🚀 Ойынды бастау" if lang == "kz" else "🚀 O'yinni boshlash", 
        callback_data="lobby_start"
    ))
    kb.adjust(1)
    return kb.as_markup()

import random

MEMES_UZ = [
    "🎭 **Mafiya Memi**:\nTinch aholi birinchi kunda Komissarni osib yuborib, keyin: 'Nega mafiya yutyapti?' deb hayron bo'lishi... 🤡",
    "🎭 **Mafiya Memi**:\nDon birinchi tunda Shifokorni tekshirganida, Shifokor o'zini o'zi davolayotganini ko'rib: 'Aka, sal insof qiling' degan ekan... 😭",
    "🎭 **Mafiya Memi**:\nKomissar: 'Men uni tekshirdim, u MAFIYA!'\nTinch aholi: 'Ishonmaymiz, sening o'zing mafiyasan, osamiz!' 🤦‍♂️",
    "🎭 **Mafiya Memi**:\nShifokor birinchi tunda o'zini davolasa, ikkinchi tunda ham o'zini davolamoqchi bo'lganida bot: 'Aka, shaharliklarni ham o'ylang!' deb aytishi... 🩺🏥",
    "🎭 **Mafiya Memi**:\nO'yin boshlanganda botni shaxsiyda `/start` qilmagani uchun guruhda 'Nega men kira olmayapman?!' deb baqiradigan o'yinchilar... 🤫",
    "🎭 **Mafiya Memi**:\nTelba (Maniac) har kecha bir boshdan hammaga pichoq suqib, tongda: 'Men tinch aholiman, shunchaki ko'chada aylanib yurgandim' deyishi... 🔪☠️",
    "🎭 **Mafiya Memi**:\nTansoqchi (Bodyguard) o'zi himoya qilayotgan odamni o'ldirib qo'yganida: 'Akajon, uzr, shamol bo'lib ketdi' deb tushuntirishi... 🛡️😅"
]

MEMES_RU = [
    "🎭 **Мафия Мем**:\nМирные жители вешают Комиссара в первый день, а потом: 'Почему мафия побеждает?' 🤡",
    "🎭 **Мафия Мем**:\nДон проверяет Доктора в первую ночь, а Доктор лечит себя: 'Брат, имей совесть' 😭",
    "🎭 **Мафия Мем**:\nКомиссар: 'Я проверил его, он МАФИЯ!'\nМирные: 'Не верим, ты сам мафия, вешаем тебя!' 🤦‍♂️",
    "🎭 **Мафия Мем**:\nДоктор лечит себя в первую ночь, во вторую ночь тоже хочет лечить себя, а бот говорит: 'Брат, подумай о городе!' 🩺🏥",
    "🎭 **Мафия Мем**:\nИгроки, которые не нажали `/start` в личке бота перед игрой, а потом кричат в группе: 'Почему я не могу зайти?!' 🤫",
    "🎭 **Мафия Мем**:\nМаньяк каждую ночь режет кого-то, а утром пишет: 'Я мирный, просто гулял по ночному городу' 🔪☠️"
]

async def send_random_lobby_meme(bot: Bot, chat_id: int, lang: str):
    try:
        memes = MEMES_RU if lang == "ru" else MEMES_UZ
        meme = random.choice(memes)
        await bot.send_message(chat_id, meme, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Error sending lobby meme: {e}")

async def lobby_timer(bot: Bot, game: Game):
    lang = await db.get_group_language(game.chat_id)
    try:
        for sec in range(120, 0, -1):
            await asyncio.sleep(1)
            if game.phase != "lobby":
                return
            if sec == 60:
                await send_random_lobby_meme(bot, game.chat_id, lang)
            if sec in [90, 60, 30, 15, 5]:
                try:
                    players_list = "\n".join([f"{i}. {p.name_escaped}" for i, p in enumerate(game.players.values(), 1)])
                    
                    if lang == "ru":
                        text = (
                            f"🎮 **Игра Мафия Darktown**\n\n"
                            f"Игроки собираются. До начала осталось **{sec} секунд**!\n\n"
                            f"👥 **Список игроков ({len(game.players)})**:\n"
                            f"{players_list}\n\n"
                            f"⚠️ **ВНИМАНИЕ**: Перед тем как присоединиться к игре, убедитесь, что вы запустили бота в личных сообщениях с помощью `/start`!"
                        )
                    elif lang == "en":
                        text = (
                            f"🎮 **Darktown Mafia Game**\n\n"
                            f"Players are gathering. **{sec} seconds** remaining!\n\n"
                            f"👥 **Player List ({len(game.players)})**:\n"
                            f"{players_list}\n\n"
                            f"⚠️ **ATTENTION**: Before joining the game, make sure you have started the bot in PM using `/start`!"
                        )
                    elif lang == "kz":
                        text = (
                            f"🎮 **Darktown Мафия Ойыны**\n\n"
                            f"Ойыншылар жиналуда. Ойынның басталуына **{sec} секунд** қалды!\n\n"
                            f"👥 **Ойыншылар тізімі ({len(game.players)})**:\n"
                            f"{players_list}\n\n"
                            f"⚠️ **НАЗАР АУДАРЫҢЫЗ**: Ойынға қосылмас бұрын, ботты жеке хабарламаларда `/start` арқылы іске қосқаныңызға көз жеткізіңіз!"
                        )
                    else:
                        text = (
                            f"🎮 **Darktown Mafiya O'yini**\n\n"
                            f"O'yinchilar yig'ilmoqda. Kirish tugashiga **{sec} soniya** qoldi!\n\n"
                            f"👥 **O'yinchilar ro'yxati ({len(game.players)})**:\n"
                            f"{players_list}\n\n"
                            f"⚠️ **DIQQAT**: O'yinga qo'shilishdan oldin botga shaxsiy xabar yuborib `/start` ni bosganingizga ishonch hosil qiling!"
                        )
                        
                    await bot.edit_message_text(
                        chat_id=game.chat_id,
                        message_id=game.lobby_message_id,
                        text=text,
                        reply_markup=get_lobby_keyboard(lang),
                        parse_mode="Markdown"
                    )
                except Exception as e:
                    if "message to edit not found" in str(e).lower() or "message can't be edited" in str(e).lower():
                        try:
                            new_msg = await bot.send_message(
                                chat_id=game.chat_id,
                                text=text,
                                reply_markup=get_lobby_keyboard(lang),
                                parse_mode="Markdown"
                            )
                            game.lobby_message_id = new_msg.message_id
                        except Exception:
                            pass
                    else:
                        pass
        if len(game.players) >= 5:
            try:
                await bot.edit_message_reply_markup(chat_id=game.chat_id, message_id=game.lobby_message_id, reply_markup=None)
            except Exception:
                pass
            
            start_msg = "⏰ Vaqt tugadi! O'yin avtomatik ravishda boshlanmoqda..."
            if lang == "ru":
                start_msg = "⏰ Время вышло! Игра начинается автоматически..."
            elif lang == "en":
                start_msg = "⏰ Time is up! The game is starting automatically..."
            elif lang == "kz":
                start_msg = "⏰ Уақыт бітті! Ойын автоматты түрде басталуда..."
                
            await bot.send_message(game.chat_id, start_msg)
            await start_game_loop(bot, game)
        else:
            try:
                await bot.edit_message_reply_markup(chat_id=game.chat_id, message_id=game.lobby_message_id, reply_markup=None)
            except Exception:
                pass
                
            cancel_msg = "⚠️ 2 daqiqa tugadi. O'yinchi soni yetarli emas (kamida 5 ta bo'lishi kerak). O'yin bekor qilindi."
            if lang == "ru":
                cancel_msg = "⚠️ 2 минуты истекли. Недостаточно игроков (необходимо минимум 5). Игра отменена."
            elif lang == "en":
                cancel_msg = "⚠️ 2 minutes expired. Not enough players (minimum 5 required). Game cancelled."
            elif lang == "kz":
                cancel_msg = "⚠️ 2 минут бітті. Ойыншылар саны жеткіліксіз (кемінде 5 қажет). Ойын тоқтатылды."
                
            await bot.send_message(game.chat_id, cancel_msg)
            game_manager.remove_game(game.chat_id)
    except asyncio.CancelledError:
        pass

@router.message(Command("newgame"))
async def cmd_newgame(message: types.Message, bot: Bot):
    chat_id = message.chat.id
    lang = await db.get_group_language(chat_id)
    
    # Check if bot is admin in the group
    try:
        bot_member = await bot.get_chat_member(chat_id, bot.id)
        if bot_member.status not in ["administrator", "creator"]:
            err_msg = (
                "⚠️ **Xatolik!** Bot ushbu guruhda o'yin boshlashi va tartibni saqlashi uchun guruhda **Admin** bo'lishi shart.\n\n"
                "Iltimos, botni guruhga admin qilib tayinlang va barcha huquqlarni (ayniqsa, xabarlarni o'chirish huquqini) bering!"
            )
            if lang == "ru":
                err_msg = (
                    "⚠️ **Ошибка!** Для запуска игры бот должен быть назначен **Администратором** группы.\n\n"
                    "Пожалуйста, сделайте бота администратором и предоставьте все права (особенно право на удаление сообщений)!"
                )
            elif lang == "en":
                err_msg = (
                    "⚠️ **Error!** The bot must be an **Administrator** in this group to start a game.\n\n"
                    "Please make the bot an administrator and grant all permissions (especially message deletion rights)!"
                )
            elif lang == "kz":
                err_msg = (
                    "⚠️ **Қате!** Ойынды бастау үшін бот топтың **Әкімшісі** (Администраторы) болуы тиіс.\n\n"
                    "Ботты әкімші етіп тағайындап, барлық рұқсаттарды (әсіресе хабарламаларды өшіру құқығын) беріңіз!"
                )
            await message.answer(err_msg, parse_mode="Markdown")
            return
    except Exception as e:
        logging.error(f"Error checking bot admin privileges: {e}")
        
    # Check if a game already exists
    existing = game_manager.get_game(chat_id)
    if existing:
        if existing.phase != "ended":
            err_msg = "⚠️ Ushbu guruhda allaqachon faol o'yin ketmoqda!"
            if lang == "ru":
                err_msg = "⚠️ В этой группе уже идет активная игра!"
            elif lang == "en":
                err_msg = "⚠️ An active game is already running in this group!"
            elif lang == "kz":
                err_msg = "⚠️ Бұл топта белсенді ойын жүріп жатыр!"
            await message.answer(err_msg)
            return
            
    # Create game
    game = game_manager.create_game(chat_id)
    game.phase = "lobby"
    
    # Register the creator
    user_id = message.from_user.id
    name = message.from_user.full_name
    username = message.from_user.username
    
    # Check if user is in another game
    other_game = game_manager.get_game_by_player(user_id)
    if other_game:
        err_msg = f"⚠️ Siz boshqa bir guruhda o'yindasiz! Undan chiqish uchun o'sha guruhda `/leave` yozing."
        if lang == "ru":
            err_msg = f"⚠️ Вы играете в другой группе! Чтобы выйти, напишите `/leave` в той группе."
        elif lang == "en":
            err_msg = f"⚠️ You are in a game in another group! Type `/leave` in that group to exit."
        elif lang == "kz":
            err_msg = f"⚠️ Сіз басқа топта ойындасыз! Одан шығу үшін сол топта `/leave` деп жазыңыз."
        await message.answer(err_msg)
        game_manager.remove_game(chat_id)
        return
        
    # Register in DB
    await db.get_user(user_id, username, name)
    
    player = Player(user_id, name, username)
    game.players[user_id] = player
    
    if lang == "ru":
        lobby_text = (
            f"🎮 **Игра Мафия Darktown**\n\n"
            f"Создана новая игра! Игроки собираются. До начала осталось **120 секунд**!\n\n"
            f"👥 **Список игроков (1)**:\n"
            f"1. {name}\n\n"
            f"⚠️ **ВНИМАНИЕ**: Перед тем как присоединиться к игре, убедитесь, что вы запустили бота в личных сообщениях с помощью `/start`!"
        )
    elif lang == "en":
        lobby_text = (
            f"🎮 **Darktown Mafia Game**\n\n"
            f"New game created! Players are gathering. **120 seconds** remaining!\n\n"
            f"👥 **Player List (1)**:\n"
            f"1. {name}\n\n"
            f"⚠️ **ATTENTION**: Before joining the game, make sure you have started the bot in PM using `/start`!"
        )
    elif lang == "kz":
        lobby_text = (
            f"🎮 **Darktown Мафия Ойыны**\n\n"
            f"Жаңа ойын құрылды! Ойыншылар жиналуда. Ойынның басталуына **120 секунд** қалды!\n\n"
            f"👥 **Ойыншылар тізімі (1)**:\n"
            f"1. {name}\n\n"
            f"⚠️ **НАЗАР АУДАРЫҢЫЗ**: Ойынға қосылмас бұрын, ботты жеке хабарламаларда `/start` арқылы іске қосқаныңызға көз жеткізіңіз!"
        )
    else:
        lobby_text = (
            f"🎮 **Darktown Mafiya O'yini**\n\n"
            f"Yangi o'yin yaratildi! Ishtirokchilar yig'ilmoqda. Kirish tugashiga **120 soniya** qoldi!\n\n"
            f"👥 **O'yinchilar ro'yxati (1)**:\n"
            f"1. {name}\n\n"
            f"⚠️ **DIQQAT**: O'yinga qo'shilishdan oldin botga shaxsiy xabar yuborib `/start` ni bosganingizga ishonch hosil qiling!"
        )
        
    lobby_msg = await message.answer(
        lobby_text,
        reply_markup=get_lobby_keyboard(lang),
        parse_mode="Markdown"
    )
    game.lobby_message_id = lobby_msg.message_id
    
    # Start lobby timer
    game.timer_task = asyncio.create_task(lobby_timer(bot, game))

@router.message(Command("tourneygame", "tournamentgame"))
async def cmd_tourneygame(message: types.Message, bot: Bot):
    chat_id = message.chat.id
    user_id = message.from_user.id
    name = message.from_user.full_name
    username = message.from_user.username
    
    game = game_manager.get_game(chat_id)
    if game:
        await message.answer("⚠️ Bu guruhda allaqachon faol o'yin mavjud!")
        return
        
    game = game_manager.create_game(chat_id)
    game.is_tournament = True
    lang = await db.get_group_language(chat_id)
    
    player = Player(user_id, name, username)
    game.players[user_id] = player
    await db.get_user(user_id, username, name)
    
    lobby_text = (
        f"🏆 **RASMIY TURNIR O'YINI LOBISI YARATILDI!** 🏆\n\n"
        f"Ushbu o'yinda faqat Mini App'da Turnirlar bo'limida ro'yxatdan o'tgan o'yinchilar qatnasha oladi.\n"
        f"⏳ O'yin boshlanishiga **120 soniya** qoldi.\n\n"
        f"👥 **O'yinchilar ro'yxati (1)**:\n1. {name}"
    )
    lobby_msg = await message.answer(
        lobby_text,
        reply_markup=get_lobby_keyboard(lang),
        parse_mode="Markdown"
    )
    game.lobby_message_id = lobby_msg.message_id
    game.timer_task = asyncio.create_task(lobby_timer(bot, game))

@router.callback_query(F.data == "join_game")
async def join_callback(cb: types.CallbackQuery, bot: Bot):
    chat_id = cb.message.chat.id
    user_id = cb.from_user.id
    name = cb.from_user.full_name
    username = cb.from_user.username
    
    game = game_manager.get_game(chat_id)
    if not game:
        await cb.answer("⚠️ O'yin topilmadi!", show_alert=True)
        return
        
    if game.phase != "lobby":
        await cb.answer("⚠️ O'yin allaqachon boshlangan!", show_alert=True)
        return
        
    if user_id in game.players:
        await cb.answer("Siz allaqachon qo'shilgansiz!", show_alert=True)
        return
        
    # Check if user is in another game
    other_game = game_manager.get_game_by_player(user_id)
    if other_game:
        await cb.answer("⚠️ Siz allaqachon boshqa guruhda o'yindasiz!", show_alert=True)
        return
        
    # Check tournament registration if tournament match
    chat_title = cb.message.chat.title or ""
    is_tourney = getattr(game, "is_tournament", False) or ("turnir" in chat_title.lower()) or ("tournament" in chat_title.lower())
    if is_tourney:
        is_registered = await db.is_user_registered_for_tournament(user_id)
        if not is_registered:
            kb = InlineKeyboardBuilder()
            kb.add(types.InlineKeyboardButton(text="🏆 Turnirga Ro'yxatdan O'tish", url="https://t.me/darktownuz_bot/app"))
            await cb.answer("⚠️ DIQQAT! Siz ushbu turnirga ro'yxatdan o'tmagansiz!", show_alert=True)
            await cb.message.answer(
                f"⚠️ **DIQQAT, {cb.from_user.full_name}!**\n\n"
                f"Ushbu guruhdagi turnir o'yinlarida faqat **Mini App'da ro'yxatdan o'tgan** o'yinchilar ishtirok eta oladi!\n"
                f"Turnirga ro'yxatdan o'tish uchun pastdagi tugmani bosing:",
                reply_markup=kb.as_markup(),
                parse_mode="Markdown"
            )
            return
        
    # Verify user has started private conversation with bot
    # We try to send a ping message
    try:
        ping = await bot.send_message(user_id, "⚙️ Siz Darktown Mafiya o'yiniga qo'shildingiz!")
        await bot.delete_message(user_id, ping.message_id)
    except Exception:
        await cb.answer("⚠️ Avval botning shaxsiy chatiga o'tib /start buyrug'ini bosing!", show_alert=True)
        return
        
    # Register in DB
    await db.get_user(user_id, username, name)
    
    # Add player
    player = Player(user_id, name, username)
    game.players[user_id] = player
    
    # Update lobby text
    lang = await db.get_group_language(chat_id)
    players_list = "\n".join([f"{i}. {p.name_escaped}" for i, p in enumerate(game.players.values(), 1)])
    
    if lang == "ru":
        lobby_text = (
            f"🎮 **Игра Мафия Darktown**\n\n"
            f"Создана новая игра! Игроки собираются.\n\n"
            f"👥 **Список игроков ({len(game.players)})**:\n"
            f"{players_list}\n\n"
            f"⚠️ **ВНИМАНИЕ**: Перед тем как присоединиться к игре, убедитесь, что вы запустили бота в личных сообщениях с помощью `/start`!"
        )
        join_confirm = "Вы успешно присоединились!"
    elif lang == "en":
        lobby_text = (
            f"🎮 **Darktown Mafia Game**\n\n"
            f"New game created! Players are gathering.\n\n"
            f"👥 **Player List ({len(game.players)})**:\n"
            f"{players_list}\n\n"
            f"⚠️ **ATTENTION**: Before joining the game, make sure you have started the bot in PM using `/start`!"
        )
        join_confirm = "You have joined successfully!"
    elif lang == "kz":
        lobby_text = (
            f"🎮 **Darktown Мафия Ойыны**\n\n"
            f"Жаңа ойын құрылды! Ойыншылар жиналуда.\n\n"
            f"👥 **Ойыншылар тізімі ({len(game.players)})**:\n"
            f"{players_list}\n\n"
            f"⚠️ **НАЗАР АУДАРЫҢЫЗ**: Ойынға қосылмас бұрын, ботты жеке хабарламаларда `/start` арқылы іске қосқаныңызға көз жеткізіңіз!"
        )
        join_confirm = "Сіз ойынға сәтті қосылдыңыз!"
    else:
        lobby_text = (
            f"🎮 **Darktown Mafiya O'yini**\n\n"
            f"Yangi o'yin yaratildi! Ishtirokchilar yig'ilmoqda.\n\n"
            f"👥 **O'yinchilar ro'yxati ({len(game.players)})**:\n"
            f"{players_list}\n\n"
            f"⚠️ **DIQQAT**: O'yinga qo'shilishdan oldin botga shaxsiy xabar yuborib `/start` ni bosganingizga ishonch hosil qiling!"
        )
        join_confirm = "Siz muvaffaqiyatli qo'shildingiz!"
        
    await cb.message.edit_text(
        lobby_text,
        reply_markup=get_lobby_keyboard(lang),
        parse_mode="Markdown"
    )
    await cb.answer(join_confirm)

@router.callback_query(F.data == "lobby_start")
async def lobby_start_callback(cb: types.CallbackQuery, bot: Bot):
    chat_id = cb.message.chat.id
    user_id = cb.from_user.id
    
    game = game_manager.get_game(chat_id)
    if not game:
        await cb.answer("⚠️ O'yin topilmadi!", show_alert=True)
        return
        
    if game.phase != "lobby":
        await cb.answer("⚠️ O'yin allaqachon boshlangan!", show_alert=True)
        return
        
    # Only allow the creator (first player) or admin to start
    # Creators is players[0]
    creator_id = list(game.players.keys())[0]
    if user_id != creator_id:
        # Check if user is group admin
        try:
            member = await bot.get_chat_member(chat_id, user_id)
            if member.status not in ["creator", "administrator"]:
                await cb.answer("⚠️ Faqat o'yin yaratuvchisi yoki guruh admini o'yinni boshlay oladi!", show_alert=True)
                return
        except Exception:
            await cb.answer("⚠️ Faqat o'yin yaratuvchisi o'yinni boshlay oladi!", show_alert=True)
            return
            
    if len(game.players) < 5:
        await cb.answer("⚠️ O'yinni boshlash uchun kamida 5 ta o'yinchi bo'lishi kerak!", show_alert=True)
        return
        
    # Remove lobby keyboard and start game
    try:
        await cb.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
        
    await cb.answer("O'yin boshlanmoqda...")
    await start_game_loop(bot, game)

@router.message(Command("leave"))
async def cmd_leave(message: types.Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    lang = await db.get_group_language(chat_id)
    
    game = game_manager.get_game(chat_id)
    if not game:
        err_msg = "Ushbu guruhda faol o'yin yo'q."
        if lang == "ru":
            err_msg = "В этой группе нет активной игры."
        elif lang == "en":
            err_msg = "No active game in this group."
        elif lang == "kz":
            err_msg = "Бұл топта белсенді ойын жоқ."
        await message.answer(err_msg)
        return
        
    if user_id not in game.players:
        err_msg = "Siz o'yin ishtirokchisi emassiz."
        if lang == "ru":
            err_msg = "Вы не являетесь участником игры."
        elif lang == "en":
            err_msg = "You are not a participant of this game."
        elif lang == "kz":
            err_msg = "Сіз ойынның қатысушысы емессіз."
        await message.answer(err_msg)
        return
        
    if game.phase == "lobby":
        del game.players[user_id]
        if not game.players:
            game_manager.remove_game(chat_id)
            cancel_msg = "Lobby bo'shab qoldi. O'yin bekor qilindi."
            if lang == "ru":
                cancel_msg = "Лобби опустело. Игра отменена."
            elif lang == "en":
                cancel_msg = "Lobby is empty. Game cancelled."
            elif lang == "kz":
                cancel_msg = "Лобби бос қалды. Ойын тоқтатылды."
            await message.answer(cancel_msg)
            return
            
        players_list = "\n".join([f"{i}. {p.name_escaped}" for i, p in enumerate(game.players.values(), 1)])
        
        if lang == "ru":
            lobby_text = (
                f"🎮 **Игра Мафия Darktown**\n\n"
                f"Создана новая игра! Игроки собираются.\n\n"
                f"👥 **Список игроков ({len(game.players)})**:\n"
                f"{players_list}\n\n"
                f"⚠️ **ВНИМАНИЕ**: Перед тем как присоединиться к игре, убедитесь, что вы запустили бота в личных сообщениях с помощью `/start`!"
            )
            leave_confirm = f"🚶 **{message.from_user.full_name}** вышел из лобби."
        elif lang == "en":
            lobby_text = (
                f"🎮 **Darktown Mafia Game**\n\n"
                f"New game created! Players are gathering.\n\n"
                f"👥 **Player List ({len(game.players)})**:\n"
                f"{players_list}\n\n"
                f"⚠️ **ATTENTION**: Before joining the game, make sure you have started the bot in PM using `/start`!"
            )
            leave_confirm = f"🚶 **{message.from_user.full_name}** left the lobby."
        elif lang == "kz":
            lobby_text = (
                f"🎮 **Darktown Мафия Ойыны**\n\n"
                f"Жаңа ойын құрылды! Ойыншылар жиналуда.\n\n"
                f"👥 **Ойыншыlar тізімі ({len(game.players)})**:\n"
                f"{players_list}\n\n"
                f"⚠️ **НАЗАР АУДАРЫҢЫЗ**: Ойынға қосылмас бұрын, ботты жеке хабарламаларда `/start` арқылы іске qosqańyzǵa kóz jetkizińiz!"
            )
            leave_confirm = f"🚶 **{message.from_user.full_name}** лоббиден шықты."
        else:
            lobby_text = (
                f"🎮 **Darktown Mafiya O'yini**\n\n"
                f"Yangi o'yin yaratildi! Ishtirokchilar yig'ilmoqda.\n\n"
                f"👥 **O'yinchilar ro'yxati ({len(game.players)})**:\n"
                f"{players_list}\n\n"
                f"⚠️ **DIQQAT**: O'yinga qo'shilishdan oldin botga shaxsiy xabar yuborib `/start` ni bosganingizga ishonch hosil qiling!"
            )
            leave_confirm = f"🚶 **{message.from_user.full_name}** lobby'dan chiqdi."

        try:
            await message.bot.edit_message_text(
                chat_id=chat_id,
                message_id=game.lobby_message_id,
                text=lobby_text,
                reply_markup=get_lobby_keyboard(lang),
                parse_mode="Markdown"
            )
        except Exception:
            pass
        await message.answer(leave_confirm)
        
    else:
        # Player quit during game
        player = game.players[user_id]
        if player.is_alive:
            player.is_alive = False
            
            leave_msg = f"💀 **{player.name_escaped}** o'yinni tark etdi va vafot etdi. Uning roli: **{player.role}**"
            if lang == "ru":
                leave_msg = f"💀 **{player.name_escaped}** покинул игру и погиб. Его роль: **{player.role}**"
            elif lang == "en":
                leave_msg = f"💀 **{player.name_escaped}** left the game and died. His role: **{player.role}**"
            elif lang == "kz":
                leave_msg = f"💀 **{player.name_escaped}** ойыннан шығып, қайтыс болды. Оның рөлі: **{player.role}**"
                
            await message.answer(leave_msg, parse_mode="Markdown")
            
            # Check win conditions
            from game.loop import check_win_conditions, end_game
            ended, winner = check_win_conditions(game)
            if ended:
                await end_game(message.bot, game, winner)

# Handle live voting callback
@router.callback_query(F.data.startswith("vote_"))
async def vote_callback(cb: types.CallbackQuery, bot: Bot):
    chat_id = cb.message.chat.id
    voter_id = cb.from_user.id
    game = game_manager.get_game(chat_id)
    
    if not game or game.phase != "voting":
        await cb.answer("⚠️ Hozir ovoz berish fazasi emas!", show_alert=True)
        return
        
    # Check if voter is alive
    if voter_id not in game.players or not game.players[voter_id].is_alive:
        await cb.answer("⚠️ Faqat tirik o'yinchilar ovoz bera oladi!", show_alert=True)
        return
        
    target_data = cb.data.replace("vote_", "")
    
    if target_data == "skip":
        game.votes[voter_id] = "skip"
    else:
        target_id = int(target_data)
        if target_id not in game.players or not game.players[target_id].is_alive:
            await cb.answer("⚠️ Bu o'yinchi tirik emas yoki o'yinda yo'q!", show_alert=True)
            return
        game.votes[voter_id] = target_id
        
    await cb.answer("Ovozingiz qabul qilindi!")
    
    # Edit the voting message to show live vote counts (Design Aesthetic #3: Dynamic UI)
    alive = game.get_alive_players()
    vote_counts = {}
    for target in game.votes.values():
        vote_counts[target] = vote_counts.get(target, 0) + 1
        
    # Build list text
    text = "🗳️ **Ovoz berish boshlandi!**\nKimni dorda osmoqchisiz? Quyidagi tugmalardan birini tanlang.\n\n"
    for p in alive:
        count = vote_counts.get(p.user_id, 0)
        votes_box = "🗳️" * count if count > 0 else ""
        text += f"- **{p.name_escaped}**: {votes_box} ({count})\n"
        
    skip_count = vote_counts.get("skip", 0)
    skip_box = "🗳️" * skip_count if skip_count > 0 else ""
    text += f"- Hech kimga: {skip_box} ({skip_count})\n\n"
    text += f"Ovoz berganlar: {len(game.votes)} / {len(alive)}"
    
    # Rebuild keyboard
    kb = InlineKeyboardBuilder()
    for p in alive:
        kb.add(types.InlineKeyboardButton(text=p.name, callback_data=f"vote_{p.user_id}"))
    kb.add(types.InlineKeyboardButton(text="⏩ Hech kimga", callback_data="vote_skip"))
    kb.adjust(2)
    
    try:
        await cb.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="Markdown")
    except Exception as e:
        # Ignore "message is not modified" errors
        logging.warning(f"Error updating live voting: {e}")

@router.message(Command("start", "startgame"))
async def cmd_start_game(message: types.Message, bot: Bot):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    game = game_manager.get_game(chat_id)
    if not game:
        await message.answer("⚠️ Guruhda faol o'yin yo'q. Yangi o'yin boshlash uchun `/newgame` yozing.")
        return
        
    if game.phase != "lobby":
        await message.answer("⚠️ O'yin allaqachon boshlangan!")
        return
        
    # Check if they are the creator (first player) or admin
    creator_id = list(game.players.keys())[0]
    if user_id != creator_id:
        try:
            member = await bot.get_chat_member(chat_id, user_id)
            if member.status not in ["creator", "administrator"]:
                await message.answer("⚠️ Faqat o'yin yaratuvchisi yoki guruh admini o'yinni boshlay oladi!")
                return
        except Exception:
            await message.answer("⚠️ Faqat o'yin yaratuvchisi o'yinni boshlay oladi!")
            return
            
    if len(game.players) < 5:
        await message.answer("⚠️ O'yinni boshlash uchun kamida 5 ta o'yinchi bo'lishi kerak!")
        return
        
    await message.answer("O'yin boshlanmoqda...")
    await start_game_loop(bot, game)

@router.message(Command("help"))
async def cmd_group_help(message: types.Message):
    lang = await db.get_group_language(message.chat.id)
    await message.answer(get_text(lang, "group_help_text"), parse_mode="Markdown")

@router.message(Command("rules", "qoidalar"))
async def cmd_group_rules(message: types.Message):
    lang = await db.get_group_language(message.chat.id)
    await message.answer(get_text(lang, "rules_text"), parse_mode="Markdown")

@router.message(Command("friend", "friends"))
async def cmd_group_friend(message: types.Message):
    lang = await db.get_group_language(message.chat.id)
    
    kb = InlineKeyboardBuilder()
    kb.add(types.InlineKeyboardButton(text="🎮 Rasmiy O'yin Guruhi" if lang=="uz" else "🎮 Официальная группа" if lang=="ru" else "🎮 Official Game Group" if lang=="en" else "🎮 Ресми ойын тобы", url="https://t.me/+OHOeijnLYglkOTli"))
    kb.add(types.InlineKeyboardButton(text="📢 Admin Kanali" if lang=="uz" else "📢 Канал Админа" if lang=="ru" else "📢 Admin Channel" if lang=="en" else "📢 Админ арнасы", url="https://t.me/sh_abbosov"))
    kb.adjust(1)
    
    await message.answer(
        get_text(lang, "friend_text"),
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )

@router.message(Command("lang", "language"))
async def cmd_group_lang(message: types.Message, bot: Bot):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    # Check if sender is group admin or bot admin
    try:
        chat_member = await bot.get_chat_member(chat_id, user_id)
        is_admin = chat_member.status in ["administrator", "creator"] or user_id == ADMIN_ID
    except Exception:
        is_admin = user_id == ADMIN_ID
        
    group_lang = await db.get_group_language(chat_id)
    
    if not is_admin:
        await message.answer(get_text(group_lang, "only_admin_lang"))
        return
        
    kb = InlineKeyboardBuilder()
    kb.add(types.InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data=f"grplang_{chat_id}_uz"))
    kb.add(types.InlineKeyboardButton(text="🇷🇺 Русский", callback_data=f"grplang_{chat_id}_ru"))
    kb.add(types.InlineKeyboardButton(text="🇺🇸 English", callback_data=f"grplang_{chat_id}_en"))
    kb.add(types.InlineKeyboardButton(text="🇰🇿 Қазақша", callback_data=f"grplang_{chat_id}_kz"))
    kb.adjust(2)
    
    await message.answer(
        get_text(group_lang, "lang_select"),
        reply_markup=kb.as_markup()
    )

@router.callback_query(F.data.startswith("grplang_"))
async def cb_group_setlang(cb: types.CallbackQuery, bot: Bot):
    parts = cb.data.split("_")
    chat_id = int(parts[1])
    lang = parts[2]
    
    # Check if the user clicking is still an admin
    try:
        chat_member = await bot.get_chat_member(chat_id, cb.from_user.id)
        is_admin = chat_member.status in ["administrator", "creator"] or cb.from_user.id == ADMIN_ID
    except Exception:
        is_admin = cb.from_user.id == ADMIN_ID
        
    if not is_admin:
        await cb.answer(get_text(lang, "only_admin_lang"), show_alert=True)
        return
        
    await db.set_group_language(chat_id, lang)
    await cb.answer(get_text(lang, "lang_changed"), show_alert=True)
    await cb.message.edit_text(get_text(lang, "lang_changed"))

@router.message(Command("forceclose", "stopgame"))
async def cmd_forceclose(message: types.Message, bot: Bot):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    # Check if sender is group administrator or bot admin
    try:
        chat_member = await bot.get_chat_member(chat_id, user_id)
        is_admin = chat_member.status in ["administrator", "creator"] or user_id == ADMIN_ID
    except Exception:
        is_admin = user_id == ADMIN_ID
        
    if not is_admin:
        await message.answer("⚠️ Ushbu buyruq faqat guruh adminlari yoki bot admini uchun!")
        return
        
    game = game_manager.get_game(chat_id)
    if not game:
        await message.answer("⚠️ Ushbu guruhda faol o'yin topilmadi.")
        return
        
    # Unmute chat and release player restrictions
    from game.loop import try_mute_chat, try_restrict_user
    await try_mute_chat(bot, chat_id, False)
    for p in game.players.values():
        await try_restrict_user(bot, chat_id, p.user_id, False)
        
    # Delete room from DB if it is a room game
    room_id = getattr(game, 'room_id', None)
    if room_id:
        import aiosqlite
        try:
            async with aiosqlite.connect(db.DB_PATH) as conn:
                await conn.execute("UPDATE rooms SET status = 'finished' WHERE room_id = ?", (room_id,))
                await conn.execute("DELETE FROM room_players WHERE room_id = ?", (room_id,))
                await conn.commit()
        except Exception as e:
            logging.error(f"Error closing DB room in group forceclose: {e}")
            
    # Delete from manager
    game_manager.remove_game(chat_id)
    
    await message.answer("🚨 **O'yin majburan to'xtatildi!** Barcha cheklovlar bekor qilindi va guruh ochildi.")

@router.message(Command("groupboard", "gtop"))
async def cmd_groupboard(message: types.Message):
    chat_id = message.chat.id
    lang = await db.get_group_language(chat_id)
    
    leaders = await db.get_group_leaderboard(chat_id, 10)
    
    if not leaders:
        if lang == "ru":
            await message.answer("📊 В этой группе пока нет сыгранных игр.")
        elif lang == "en":
            await message.answer("📊 No games have been played in this group yet.")
        elif lang == "kz":
            await message.answer("📊 Бұл топта әлі ешқандай ойын ойналмады.")
        else:
            await message.answer("📊 Ushbu guruhda hali o'yinlar o'ynalmagan.")
        return
        
    title = "🏆 **Guruh Top 10 O'yinchilari**:\n\n"
    if lang == "ru":
        title = "🏆 **Топ-10 игроков этой группы**:\n\n"
    elif lang == "en":
        title = "🏆 **Top 10 Players of This Group**:\n\n"
    elif lang == "kz":
        title = "🏆 **Бұл топтың таңдаулы 10 ойыншысы**:\n\n"
        
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    
    text = title
    for i, row in enumerate(leaders):
        medal = medals[i] if i < len(medals) else f"{i+1}."
        name = row['first_name']
        username_str = f" (@{row['username']})" if row['username'] else ""
        
        # Escape markdown characters in name
        escaped_name = name
        for char in ['_', '*', '[', '`']:
            escaped_name = escaped_name.replace(char, f"\\{char}")
            
        played = row['games_played']
        won = row['games_won']
        
        if lang == "ru":
            text += f"{medal} **{escaped_name}**{username_str}: Победил **{won}** из **{played}** игр\n"
        elif lang == "en":
            text += f"{medal} **{escaped_name}**{username_str}: Won **{won}** out of **{played}** games\n"
        elif lang == "kz":
            text += f"{medal} **{escaped_name}**{username_str}: **{played}** ойыннан **{won}** жеңіс\n"
        else:
            text += f"{medal} **{escaped_name}**{username_str}: **{played}** tadan **{won}** ta g'alaba\n"
            
    await message.answer(text, parse_mode="Markdown")

# Enforce group chat rules (mute on night phase, silence dead players)
@router.message()
async def handle_group_chat_rules(message: types.Message, bot: Bot):
    # Ignore commands
    if message.text and message.text.startswith("/"):
        return
        
    chat_id = message.chat.id
    game = game_manager.get_game(chat_id)
    if not game or game.phase == "ended" or game.phase == "lobby":
        return
        
    user_id = message.from_user.id
    player = game.players.get(user_id)
    
    # 1. If player is dead, delete their message (dead players don't talk)
    if player and not player.is_alive:
        try:
            await bot.delete_message(chat_id, message.message_id)
        except Exception:
            pass
        return
        
    # 2. If user is NOT in the game (spectator), delete their message to prevent game disruption
    if not player:
        try:
            await bot.delete_message(chat_id, message.message_id)
        except Exception:
            pass
        return
        
    # 3. If phase is night, delete players' messages (city is asleep)
    if game.phase == "night":
        try:
            await bot.delete_message(chat_id, message.message_id)
        except Exception:
            pass
        return
