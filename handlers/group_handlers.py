import asyncio
import logging
from aiogram import Router, F, Bot, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from game.manager import game_manager
from game.loop import start_game_loop
from game.models import Player
from database import db

router = Router()

# Only process group and supergroup messages
router.message.filter(F.chat.type.in_({"group", "supergroup"}))

def get_lobby_keyboard() -> types.InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.add(types.InlineKeyboardButton(text="📥 O'yinga qo'shilish", callback_data="join_game"))
    kb.add(types.InlineKeyboardButton(text="🚀 O'yinni boshlash", callback_data="lobby_start"))
    kb.adjust(1)
    return kb.as_markup()

@router.message(Command("newgame"))
async def cmd_newgame(message: types.Message, bot: Bot):
    chat_id = message.chat.id
    
    # Check if a game already exists
    existing = game_manager.get_game(chat_id)
    if existing:
        if existing.phase != "ended":
            await message.answer("⚠️ Ushbu guruhda allaqachon faol o'yin ketmoqda!")
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
        await message.answer(f"⚠️ Siz boshqa bir guruhda o'yindasiz! Undan chiqish uchun o'sha guruhda `/leave` yozing.")
        game_manager.remove_game(chat_id)
        return
        
    # Register in DB
    await db.get_user(user_id, username, name)
    
    player = Player(user_id, name, username)
    game.players[user_id] = player
    
    lobby_msg = await message.answer(
        f"🎮 **Darktown Mafiya O'yini**\n\n"
        f"Yangi o'yin yaratildi! Ishtirokchilar yig'ilmoqda.\n\n"
        f"👥 **O'yinchilar ro'yxati (1)**:\n"
        f"1. {name}\n\n"
        f"⚠️ **DIQQAT**: O'yinga qo'shilishdan oldin botga shaxsiy xabar yuborib `/start` ni bosganingizga ishonch hosil qiling!",
        reply_markup=get_lobby_keyboard(),
        parse_mode="Markdown"
    )
    game.lobby_message_id = lobby_msg.message_id

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
    players_list = "\n".join([f"{i}. {p.name}" for i, p in enumerate(game.players.values(), 1)])
    await cb.message.edit_text(
        f"🎮 **Darktown Mafiya O'yini**\n\n"
        f"Yangi o'yin yaratildi! Ishtirokchilar yig'ilmoqda.\n\n"
        f"👥 **O'yinchilar ro'yxati ({len(game.players)})**:\n"
        f"{players_list}\n\n"
        f"⚠️ **DIQQAT**: O'yinga qo'shilishdan oldin botga shaxsiy xabar yuborib `/start` ni bosganingizga ishonch hosil qiling!",
        reply_markup=get_lobby_keyboard(),
        parse_mode="Markdown"
    )
    await cb.answer("Siz muvaffaqiyatli qo'shildingiz!")

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
            
    if len(game.players) < 4:
        # For testing we can allow 3 players, but let's advise 4+
        await cb.answer("⚠️ O'yinni boshlash uchun kamida 4 ta o'yinchi bo'lishi kerak!", show_alert=True)
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
    
    game = game_manager.get_game(chat_id)
    if not game:
        await message.answer("Ushbu guruhda faol o'yin yo'q.")
        return
        
    if user_id not in game.players:
        await message.answer("Siz o'yin ishtirokchisi emassiz.")
        return
        
    if game.phase == "lobby":
        del game.players[user_id]
        if not game.players:
            game_manager.remove_game(chat_id)
            await message.answer("Lobby bo'shab qoldi. O'yin bekor qilindi.")
            return
            
        players_list = "\n".join([f"{i}. {p.name}" for i, p in enumerate(game.players.values(), 1)])
        # Update lobby message
        try:
            await message.bot.edit_message_text(
                chat_id=chat_id,
                message_id=game.lobby_message_id,
                text=f"🎮 **Darktown Mafiya O'yini**\n\n"
                     f"Yangi o'yin yaratildi! Ishtirokchilar yig'ilmoqda.\n\n"
                     f"👥 **O'yinchilar ro'yxati ({len(game.players)})**:\n"
                     f"{players_list}\n\n"
                     f"⚠️ **DIQQAT**: O'yinga qo'shilishdan oldin botga shaxsiy xabar yuborib `/start` ni bosganingizga ishonch hosil qiling!",
                reply_markup=get_lobby_keyboard(),
                parse_mode="Markdown"
            )
        except Exception:
            pass
        await message.answer(f"🚶 **{message.from_user.full_name}** lobby'dan chiqdi.")
        
    else:
        # Player quit during game
        player = game.players[user_id]
        if player.is_alive:
            player.is_alive = False
            await message.answer(f"💀 **{player.name}** o'yinni tark etdi va vafot etdi. Uning roli: **{player.role}**")
            
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
        text += f"- **{p.name}**: {votes_box} ({count})\n"
        
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
            
    if len(game.players) < 4:
        await message.answer("⚠️ O'yinni boshlash uchun kamida 4 ta o'yinchi bo'lishi kerak!")
        return
        
    await message.answer("O'yin boshlanmoqda...")
    await start_game_loop(bot, game)
