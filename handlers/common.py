import logging
from aiogram import Router, F, types
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import db
from config import WEBAPP_URL, ADMIN_ID
from locales import get_text

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
    
    # Check referrals first (before get_user so add_referral registers them correctly)
    args = message.text.split()
    referred = False
    if len(args) > 1:
        ref_param = args[1]
        inviter_id = None
        if ref_param.startswith("ref_"):
            try:
                inviter_id = int(ref_param.replace("ref_", ""))
            except ValueError:
                pass
        else:
            try:
                inviter_id = int(ref_param)
            except ValueError:
                pass
                
        if inviter_id and inviter_id != user_id:
            referred = await db.add_referral(user_id, inviter_id)
            
    # Save/Get user from DB
    user = await db.get_user(user_id, username, first_name)
    lang = user.get('language', 'uz')
    
    # Notify referral rewards if referred successfully
    if referred:
        await message.answer(get_text(lang, "referral_welcome"), parse_mode="Markdown")
        try:
            inviter_id = user.get('referred_by')
            if inviter_id:
                inviter_lang = await db.get_user_language(inviter_id)
                await message.bot.send_message(
                    inviter_id,
                    get_text(inviter_lang, "referral_notification"),
                    parse_mode="Markdown"
                )
        except Exception as e:
            logging.error(f"Error notifying inviter: {e}")
            
    welcome_text = get_text(lang, "start_private", name=first_name)
    
    shield_status = "🛡️ Active" if user['shield_active'] else "❌ Inactive"
    if lang == "uz":
        shield_status = "🛡️ Faol" if user['shield_active'] else "❌ Faol emas"
    elif lang == "ru":
        shield_status = "🛡️ Активен" if user['shield_active'] else "❌ Неактивен"
    elif lang == "kz":
        shield_status = "🛡️ Белсенді" if user['shield_active'] else "❌ Белсенді емес"
        
    status_text = "\n\n" + get_text(
        lang, "profile_text",
        level=user['level'],
        xp=user['xp'],
        coins=user['coins'],
        shield=shield_status
    )
    
    await message.answer(welcome_text + status_text, reply_markup=get_start_keyboard(user_id, bot_user), parse_mode="Markdown")

@router.message(Command("profile", "profil"))
async def cmd_profile(message: types.Message):
    user_id = message.from_user.id
    user = await db.get_user(user_id, message.from_user.username, message.from_user.full_name)
    lang = user.get('language', 'uz')
    bot_user = (await message.bot.get_me()).username
    
    # Get stats
    stats = await db.get_user_stats(user_id)
    total_played = sum(s['games_played'] for s in stats)
    total_won = sum(s['games_won'] for s in stats)
    win_rate = (total_won / total_played * 100) if total_played > 0 else 0
    
    shield_status = "🛡️ Active" if user['shield_active'] else "❌ Inactive"
    if lang == "uz":
        shield_status = "🛡️ Faol" if user['shield_active'] else "❌ Faol emas"
    elif lang == "ru":
        shield_status = "🛡️ Активен" if user['shield_active'] else "❌ Неактивен"
    elif lang == "kz":
        shield_status = "🛡️ Белсенді" if user['shield_active'] else "❌ Белсенді емес"
        
    profile_text = get_text(
        lang, "profile_text",
        level=user['level'],
        xp=user['xp'],
        coins=user['coins'],
        shield=shield_status
    )
    
    # Append localized stats
    stats_text = ""
    if lang == "uz":
        stats_text = f"\n\n🎮 O'yinlar: **{total_played} ta**\n🏆 G'alabalar: **{total_won} ta** ({win_rate:.1f}%)"
    elif lang == "ru":
        stats_text = f"\n\n🎮 Игры: **{total_played}**\n🏆 Победы: **{total_won}** ({win_rate:.1f}%)"
    elif lang == "en":
        stats_text = f"\n\n🎮 Games: **{total_played}**\n🏆 Wins: **{total_won}** ({win_rate:.1f}%)"
    elif lang == "kz":
        stats_text = f"\n\n🎮 Ойындар: **{total_played}**\n🏆 Жеңістер: **{total_won}** ({win_rate:.1f}%)"
        
    await message.answer(profile_text + stats_text, reply_markup=get_start_keyboard(user_id, bot_user), parse_mode="Markdown")

@router.message(Command("leaderboard"))
async def cmd_leaderboard(message: types.Message):
    user_id = message.from_user.id
    lang = await db.get_user_language(user_id)
    leaders = await db.get_leaderboard(10)
    
    text = get_text(lang, "leaderboard_title")
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    
    for i, user in enumerate(leaders):
        username_part = f" (@{user['username']})" if user['username'] else ""
        text += f"{medals[i]} **{user['first_name']}**{username_part} — Level {user['level']} ({user['xp']} XP)\n"
        
    if not leaders:
        if lang == "uz":
            text += "Hozircha o'yinchilar yo'q."
        elif lang == "ru":
            text += "Игроков пока нет."
        elif lang == "en":
            text += "No players yet."
        elif lang == "kz":
            text += "Ойыншылар әлі жоқ."
        
    await message.answer(text, parse_mode="Markdown")

@router.message(Command("boost"))
async def cmd_boost(message: types.Message):
    user_id = message.from_user.id
    lang = await db.get_user_language(user_id)
    inventory = await db.get_inventory(user_id)
    bot_user = (await message.bot.get_me()).username
    
    boosters = {k: v for k, v in inventory.items() if k.startswith("booster_") and v > 0}
    
    if not boosters:
        no_boosters_text = "⚠️ Sizda faol rol boosterlari yo'q.\nUlarni Mini App do'konidan sotib olishingiz mumkin!"
        if lang == "ru":
            no_boosters_text = "⚠️ У вас нет активных бустеров ролей.\nВы можете купить их в магазине Mini App!"
        elif lang == "en":
            no_boosters_text = "⚠️ You have no active role boosters.\nYou can buy them in the Mini App shop!"
        elif lang == "kz":
            no_boosters_text = "⚠️ Сізде белсенді рөлдік бустерлер жоқ.\nОларды Mini App дүкенінен сатып алуға болады!"
            
        await message.answer(
            no_boosters_text,
            reply_markup=get_start_keyboard(user_id, bot_user)
        )
        return
        
    kb = InlineKeyboardBuilder()
    for item_key, qty in boosters.items():
        role_name = item_key.replace("booster_", "").capitalize()
        kb.add(types.InlineKeyboardButton(
            text=f"🎭 {role_name} ({qty} dona)" if lang == "uz" else f"🎭 {role_name} ({qty} шт)" if lang == "ru" else f"🎭 {role_name} ({qty} pcs)" if lang == "en" else f"🎭 {role_name} ({qty} дана)", 
            callback_data=f"activate_{item_key}"
        ))
    kb.adjust(1)
    
    boost_title = "🎭 **Rol Boosterini Faollashtirish**\n\nKeyingi o'yinda qaysi rolni olish ehtimolini oshirmoqchisiz? Tanlang:\n_(O'yin boshlanganda 1 ta booster sarflanadi)_"
    if lang == "ru":
        boost_title = "🎭 **Активация Бустера Роли**\n\nКакую роль вы хотите получить с большей вероятностью в следующей игре? Выберите:\n_(1 бустер будет потрачен при старте игры)_"
    elif lang == "en":
        boost_title = "🎭 **Activate Role Booster**\n\nWhich role do you want to have a higher chance of getting in the next game? Choose:\n_(1 booster will be consumed when the game starts)_"
    elif lang == "kz":
        boost_title = "🎭 **Рөлдік Бустерді Белсендіру**\n\nКелесі ойында қай рөлді алу ықтималдығын арттырғыңыз келеді? Таңдаңыз:\n_(Ойын басталғанда 1 бустер жұмсалады)_"
        
    await message.answer(
        boost_title,
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("activate_"))
async def cb_activate_booster(cb: types.CallbackQuery):
    user_id = cb.from_user.id
    lang = await db.get_user_language(user_id)
    item_key = cb.data.replace("activate_", "")
    role_name = item_key.replace("booster_", "").capitalize()
    
    from game.manager import game_manager
    game = game_manager.get_game_by_player(user_id)
    if not game:
        err_msg = "⚠️ Avval guruhda /newgame yozib, o'yinga qo'shiling!"
        if lang == "ru":
            err_msg = "⚠️ Сначала присоединитесь к игре, написав /newgame в группе!"
        elif lang == "en":
            err_msg = "⚠️ First join the game by typing /newgame in the group!"
        elif lang == "kz":
            err_msg = "⚠️ Алдымен топта /newgame деп жазып, ойынға қосылыңыз!"
        await cb.answer(err_msg, show_alert=True)
        return
        
    if game.phase != "lobby":
        err_msg = "⚠️ O'yin boshlanib ketgan, endi booster faollashtirib bo'lmaydi!"
        if lang == "ru":
            err_msg = "⚠️ Игра уже началась, бустер активировать нельзя!"
        elif lang == "en":
            err_msg = "⚠️ The game has already started, cannot activate booster!"
        elif lang == "kz":
            err_msg = "⚠️ Ойын басталып кетті, бустерді белсендіру мүмкін емес!"
        await cb.answer(err_msg, show_alert=True)
        return
        
    player = game.players.get(user_id)
    if player:
        player.role_booster = role_name
        success_text = f"🎭 Siz keyingi o'yin uchun **{role_name}** boosterini faollashtirdingiz! O'yin boshlanganda u sarflanadi."
        alert_text = "Booster faollashtirildi!"
        if lang == "ru":
            success_text = f"🎭 Вы активировали бустер **{role_name}** на следующую игру! Он будет потрачен при старте."
            alert_text = "Бустер активирован!"
        elif lang == "en":
            success_text = f"🎭 You activated the **{role_name}** booster for the next game! It will be consumed on start."
            alert_text = "Booster activated!"
        elif lang == "kz":
            success_text = f"🎭 Келесі ойын үшін **{role_name}** бустерін белсендірдіңіз! Ол ойын басталғанда жұмсалады."
            alert_text = "Бустер белсендірілді!"
            
        await cb.message.edit_text(success_text)
        await cb.answer(alert_text)
    else:
        err_msg = "Siz o'yin ishtirokchisi emassiz!"
        if lang == "ru":
            err_msg = "Вы не являетесь участником игры!"
        elif lang == "en":
            err_msg = "You are not a player in the game!"
        elif lang == "kz":
            err_msg = "Сіз ойын қатысушысы емессіз!"
        await cb.answer(err_msg, show_alert=True)

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
        target_uid = int(args[1].strip("<>"))
        amount = int(args[2].strip("<>"))
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
        target_uid = int(args[1].strip("<>"))
        amount = int(args[2].strip("<>"))
        await db.add_xp_and_coins(target_uid, amount, 0)
        await message.answer(f"✅ O'yinchi {target_uid} ga **{amount}** XP berildi!")
    except Exception as e:
        await message.answer(f"Xato: {e}")

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    user_id = message.from_user.id
    lang = await db.get_user_language(user_id)
    await message.answer(get_text(lang, "help_text"), parse_mode="Markdown")

@router.message(Command("rules", "qoidalar"))
async def cmd_rules(message: types.Message):
    user_id = message.from_user.id
    lang = await db.get_user_language(user_id)
    await message.answer(get_text(lang, "rules_text"), parse_mode="Markdown")

@router.message(Command("friend"))
async def cmd_friend(message: types.Message):
    user_id = message.from_user.id
    lang = await db.get_user_language(user_id)
    
    kb = InlineKeyboardBuilder()
    kb.add(types.InlineKeyboardButton(text="🎮 Rasmiy O'yin Guruhi" if lang=="uz" else "🎮 Официальная группа" if lang=="ru" else "🎮 Official Game Group" if lang=="en" else "🎮 Ресми ойын тобы", url="https://t.me/+jJAWhi60hLxjZjI6"))
    kb.add(types.InlineKeyboardButton(text="📢 Admin Kanali" if lang=="uz" else "📢 Канал Админа" if lang=="ru" else "📢 Admin Channel" if lang=="en" else "📢 Админ арнасы", url="https://t.me/sh_abbosov"))
    kb.adjust(1)
    
    await message.answer(
        get_text(lang, "friend_text"),
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )

@router.message(Command("lang", "language"))
async def cmd_lang(message: types.Message):
    user_id = message.from_user.id
    user = await db.get_user(user_id, message.from_user.username, message.from_user.full_name)
    lang = user.get('language', 'uz')
    
    kb = InlineKeyboardBuilder()
    kb.add(types.InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="setlang_uz"))
    kb.add(types.InlineKeyboardButton(text="🇷🇺 Русский", callback_data="setlang_ru"))
    kb.add(types.InlineKeyboardButton(text="🇺🇸 English", callback_data="setlang_en"))
    kb.add(types.InlineKeyboardButton(text="🇰🇿 Қазақша", callback_data="setlang_kz"))
    kb.adjust(2)
    
    await message.answer(
        get_text(lang, "lang_select"),
        reply_markup=kb.as_markup()
    )

@router.callback_query(F.data.startswith("setlang_"))
async def cb_setlang(cb: types.CallbackQuery):
    lang = cb.data.replace("setlang_", "")
    await db.set_user_language(cb.from_user.id, lang)
    
    await cb.answer(get_text(lang, "lang_changed"), show_alert=True)
    await cb.message.edit_text(get_text(lang, "lang_changed"))

@router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: types.PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

@router.message(F.successful_payment)
async def successful_payment_handler(message: types.Message):
    payment = message.successful_payment
    payload = payment.invoice_payload
    
    coins = 0
    if payload.startswith("coins_"):
        try:
            coins = int(payload.replace("coins_", ""))
        except ValueError:
            pass
            
    if coins > 0:
        await db.add_xp_and_coins(message.from_user.id, 0, coins)
        lang = await db.get_user_language(message.from_user.id)
        
        success_msg = f"🎉 **Xarid muvaffaqiyatli yakunlandi!** Hisobingizga **{coins}** tanga qo'shildi."
        if lang == "ru":
            success_msg = f"🎉 **Покупка успешно завершена!** На ваш баланс зачислено **{coins}** монет."
        elif lang == "en":
            success_msg = f"🎉 **Purchase completed successfully!** **{coins}** coins have been added to your balance."
        elif lang == "kz":
            success_msg = f"🎉 **Сатып алу сәтті аяқталды!** Балансыңызға **{coins}** монета қосылды."
            
        await message.answer(success_msg, parse_mode="Markdown")
