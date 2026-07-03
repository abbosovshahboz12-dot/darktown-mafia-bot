import logging
from aiogram import Router, F, types
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import db
from config import WEBAPP_URL, ADMIN_ID

router = Router()
router.message.filter(F.chat.type == "private")

def get_start_keyboard(user_id: int, bot_username: str = "darktownuz_bot") -> types.InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    # WebApp URL must contain user_id to load their profile
    url = f"{WEBAPP_URL}?user_id={user_id}"
    kb.add(types.InlineKeyboardButton(
        text="🎮 Darktown Mini App", 
        web_app=types.WebAppInfo(url=url)
    ))
    kb.add(types.InlineKeyboardButton(
        text="🌐 Guruhga qo'shish",
        url=f"https://t.me/{bot_username}?startgroup=true"
    ))
    kb.adjust(1)
    return kb.as_markup()

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.full_name
    bot_user = (await message.bot.get_me()).username
    
    # Save/Get user from DB
    user = await db.get_user(user_id, username, first_name)
    
    welcome_text = (
        f"🕵️‍♂️ **Darktown-ga xush kelibsiz, {first_name}!**\n\n"
        f"Siz hozirgina qonun va jinoyat to'qnash keladigan shafqatsiz shaharga qadam qo'ydingiz.\n\n"
        f"📊 **Sizning statsingiz**:\n"
        f"👑 Darajangiz: {user['level']}-Level\n"
        f"✨ XP: {user['xp']} / {user['level'] * 500}\n"
        f"💰 Tangalar: {user['coins']} Dark Coins\n\n"
        f"O'yin statistikasini ko'rish, yangi rollar/qalqonlar sotib olish va global reytingda o'rningizni ko'rish uchun **Darktown Mini App** ni oching!"
    )
    
    await message.answer(welcome_text, reply_markup=get_start_keyboard(user_id, bot_user), parse_mode="Markdown")

@router.message(Command("profile"))
async def cmd_profile(message: types.Message):
    user_id = message.from_user.id
    user = await db.get_user(user_id, message.from_user.username, message.from_user.full_name)
    bot_user = (await message.bot.get_me()).username
    
    # Get stats
    stats = await db.get_user_stats(user_id)
    total_played = sum(s['games_played'] for s in stats)
    total_won = sum(s['games_won'] for s in stats)
    win_rate = (total_won / total_played * 100) if total_played > 0 else 0
    
    shield_status = "🛡️ Faol" if user['shield_active'] else "❌ Faol emas"
    
    profile_text = (
        f"👤 **{message.from_user.full_name} Profili**\n\n"
        f"🎖️ Daraja: **{user['level']}**\n"
        f"✨ XP: **{user['xp']} / {user['level'] * 500}**\n"
        f"💰 Balans: **{user['coins']} Dark Coins**\n"
        f"🛡️ XP Himoyasi: **{shield_status}**\n\n"
        f"🎮 O'yinlar: **{total_played} ta**\n"
        f"🏆 G'alabalar: **{total_won} ta** ({win_rate:.1f}%)\n"
    )
    
    await message.answer(profile_text, reply_markup=get_start_keyboard(user_id, bot_user), parse_mode="Markdown")

@router.message(Command("leaderboard"))
async def cmd_leaderboard(message: types.Message):
    leaders = await db.get_leaderboard(10)
    
    text = "🏆 **Darktown Global Top 10 O'yinchilari**\n\n"
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    
    for i, user in enumerate(leaders):
        username_part = f" (@{user['username']})" if user['username'] else ""
        text += f"{medals[i]} **{user['first_name']}**{username_part} — Level {user['level']} ({user['xp']} XP)\n"
        
    if not leaders:
        text += "Hozircha o'yinchilar yo'q."
        
    await message.answer(text, parse_mode="Markdown")

@router.message(Command("boost"))
async def cmd_boost(message: types.Message):
    user_id = message.from_user.id
    inventory = await db.get_inventory(user_id)
    bot_user = (await message.bot.get_me()).username
    
    # Check if they have boosters
    boosters = {k: v for k, v in inventory.items() if k.startswith("booster_") and v > 0}
    
    if not boosters:
        await message.answer(
            "⚠️ Sizda faol rol boosterlari yo'q.\n"
            "Ularni Mini App do'konidan sotib olishingiz mumkin!",
            reply_markup=get_start_keyboard(user_id, bot_user)
        )
        return
        
    kb = InlineKeyboardBuilder()
    for item_key, qty in boosters.items():
        role_name = item_key.replace("booster_", "").capitalize()
        kb.add(types.InlineKeyboardButton(
            text=f"🎭 {role_name} ({qty} dona)", 
            callback_data=f"activate_{item_key}"
        ))
    kb.adjust(1)
    
    await message.answer(
        "🎭 **Rol Boosterini Faollashtirish**\n\n"
        "Keyingi o'yinda qaysi rolni olish ehtimolini oshirmoqchisiz? Tanlang:\n"
        "_(O'yin boshlanganda 1 ta booster sarflanadi)_",
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("activate_"))
async def cb_activate_booster(cb: types.CallbackQuery):
    user_id = cb.from_user.id
    item_key = cb.data.replace("activate_", "")
    role_name = item_key.replace("booster_", "").capitalize()
    
    # We find if they are in lobby
    from game.manager import game_manager
    game = game_manager.get_game_by_player(user_id)
    if not game:
        await cb.answer("⚠️ Avval guruhda /newgame yozib, o'yinga qo'shiling!", show_alert=True)
        return
        
    if game.phase != "lobby":
        await cb.answer("⚠️ O'yin boshlanib ketgan, endi booster faollashtirib bo'lmaydi!", show_alert=True)
        return
        
    player = game.players.get(user_id)
    if player:
        player.role_booster = role_name
        await cb.message.edit_text(f"🎭 Siz keyingi o'yin uchun **{role_name}** boosterini faollashtirdingiz! O'yin boshlanganda u sarflanadi.")
        await cb.answer("Booster faollashtirildi!")
    else:
        await cb.answer("Siz o'yin ishtirokchisi emassiz!", show_alert=True)

@router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        await message.answer(f"⚠️ Ushbu buyruq faqat bot admini uchun!\nSizning ID: `{user_id}`\nConfigdagi Admin ID: `{ADMIN_ID}`\n\nAgar mos kelmasa, Railway Variables bo'limida `ADMIN_ID` ni to'g'ri o'rnating.", parse_mode="Markdown")
        return
        
    stats = await db.get_global_stats()
    from game.manager import game_manager
    active_games = len(game_manager.games)
    
    text = (
        f"👑 **Darktown Bot - Admin Paneli**\n\n"
        f"👥 Ro'yxatdan o'tgan o'yinchilar: **{stats['total_users']} ta**\n"
        f"🎮 Umumiy o'yinlar soni: **{stats['total_plays']} ta**\n"
        f"⚡ Hozirgi faol o'yinlar: **{active_games} ta**\n\n"
        f"**Buyruqlar**:\n"
        f"`/givecoins <user_id> <miqdor>` - Foydalanuvchiga tanga berish\n"
        f"`/givexp <user_id> <miqdor>` - Foydalanuvchiga XP berish"
    )
    await message.answer(text, parse_mode="Markdown")

@router.message(Command("givecoins"))
async def cmd_givecoins(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⚠️ Ushbu buyruq faqat bot admini uchun!")
        return
        
    args = message.text.split()
    if len(args) < 3:
        await message.answer("Format: `/givecoins <user_id> <miqdor>`", parse_mode="Markdown")
        return
        
    try:
        target_uid = int(args[1])
        amount = int(args[2])
        await db.add_xp_and_coins(target_uid, 0, amount)
        await message.answer(f"✅ O'yinchi {target_uid} ga **{amount}** Dark Coins berildi!")
    except Exception as e:
        await message.answer(f"Xato: {e}")

@router.message(Command("givexp"))
async def cmd_givexp(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⚠️ Ushbu buyruq faqat bot admini uchun!")
        return
        
    args = message.text.split()
    if len(args) < 3:
        await message.answer("Format: `/givexp <user_id> <miqdor>`", parse_mode="Markdown")
        return
        
    try:
        target_uid = int(args[1])
        amount = int(args[2])
        await db.add_xp_and_coins(target_uid, amount, 0)
        await message.answer(f"✅ O'yinchi {target_uid} ga **{amount}** XP berildi!")
    except Exception as e:
        await message.answer(f"Xato: {e}")
