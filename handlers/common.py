import logging
import csv
import io
import asyncio
from datetime import datetime
from aiogram import Router, F, types, Bot
from aiogram.types import BufferedInputFile
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import db
from config import (
    WEBAPP_URL, ADMIN_ID,
    FEATURE_WEBAPP, FEATURE_SHOP, FEATURE_REFERRAL, FEATURE_LEADERBOARD
)
from locales import get_text

router = Router()
router.message.filter(F.chat.type == "private")

def generate_users_csv(users_data: list[dict]) -> bytes:
    output = io.StringIO()
    # Write UTF-8-SIG BOM so Microsoft Excel and Google Sheets render Uzbek/Cyrillic characters properly
    output.write('\ufeff')
    writer = csv.writer(output, delimiter=';')
    
    # Header row
    writer.writerow([
        "№",
        "Telegram ID",
        "Ism (First Name)",
        "Username",
        "Daraja (Level)",
        "XP Ballari",
        "Tangalar (Coins)",
        "Jami O'yinlar",
        "G'alabalar",
        "G'alaba Foizi (Winrate %)",
        "Qalqon",
        "Bloklanganmi",
        "Til",
        "Ro'yxatdan O'tgan",
        "So'nggi Faollik"
    ])
    
    for i, u in enumerate(users_data, 1):
        total = u.get("total_games", 0)
        wins = u.get("total_wins", 0)
        winrate = f"{(wins / total * 100):.1f}%" if total > 0 else "0%"
        shield = "Faol" if u.get("shield_active") else "Yo'q"
        banned = "Ha (Bloklangan)" if u.get("banned") else "Yo'q"
        
        writer.writerow([
            i,
            u.get("user_id", ""),
            u.get("first_name", ""),
            f"@{u['username']}" if u.get("username") else "",
            u.get("level", 1),
            u.get("xp", 0),
            u.get("coins", 0),
            total,
            wins,
            winrate,
            shield,
            banned,
            u.get("language", "uz"),
            u.get("created_at") or "-",
            u.get("last_active") or "-"
        ])
        
    return output.getvalue().encode('utf-8-sig')

def escape_markdown(text: str) -> str:
    if not text:
        return ""
    for char in ['_', '*', '[', '`']:
        text = text.replace(char, f"\\{char}")
    return text

def get_start_keyboard(user_id: int, bot_username: str = "darktownuz_bot", lang: str = "uz", bonus_claimed: bool = False) -> types.InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    
    # 1. Agar WebApp yoqilgan bo'lsa (Phase 3)
    if FEATURE_WEBAPP:
        url = f"{WEBAPP_URL}?user_id={user_id}"
        kb.add(types.InlineKeyboardButton(
            text="🎮 Darktown Mini App", 
            web_app=types.WebAppInfo(url=url)
        ))
    
    # 2. Asosiy MVP tugmalari
    if FEATURE_SHOP:
        shop_btn = "🛒 Do'kon" if lang == "uz" else "🛒 Магазин" if lang == "ru" else "🛒 Shop" if lang == "en" else "🛒 Дүкен"
        kb.add(types.InlineKeyboardButton(text=shop_btn, callback_data="menu_shop"))
        
    if FEATURE_REFERRAL:
        ref_btn = "🎁 Do'stlarni taklif qilish" if lang == "uz" else "🎁 Пригласить друзей" if lang == "ru" else "🎁 Invite Friends" if lang == "en" else "🎁 Достарды шақыру"
        kb.add(types.InlineKeyboardButton(text=ref_btn, callback_data="menu_ref"))
        
    profile_btn = "👤 Profil" if lang == "uz" else "👤 Профиль" if lang == "ru" else "👤 Profile" if lang == "en" else "👤 Профиль"
    kb.add(types.InlineKeyboardButton(text=profile_btn, callback_data="menu_profile"))
    
    if FEATURE_LEADERBOARD:
        top_btn = "🏆 Reyting" if lang == "uz" else "🏆 Топ игроков" if lang == "ru" else "🏆 Leaderboard" if lang == "en" else "🏆 Рейтинг"
        kb.add(types.InlineKeyboardButton(text=top_btn, callback_data="menu_top"))
        
    boost_btn = "🎭 Rol Busterlari" if lang == "uz" else "🎭 Бустеры Ролей" if lang == "ru" else "🎭 Role Boosters" if lang == "en" else "🎭 Бустерлер"
    kb.add(types.InlineKeyboardButton(text=boost_btn, callback_data="menu_boosters"))
    
    # Kanalga a'zo bo'lib bonus olish tugmasi (agar hali olmagan bo'lsa)
    from config import REQUIRED_CHANNEL
    if not bonus_claimed:
        bonus_btn = "🎁 +100 Tanga olish" if lang == "uz" else "🎁 Получить +100 монет" if lang == "ru" else "🎁 Claim +100 Coins" if lang == "en" else "🎁 +100 монета алу"
        kb.add(types.InlineKeyboardButton(text=bonus_btn, callback_data="claim_channel_bonus"))
    elif REQUIRED_CHANNEL:
        chan_btn = "📢 Rasmiy Kanal" if lang == "uz" else "📢 Наш Канал" if lang == "ru" else "📢 Official Channel" if lang == "en" else "📢 Ресми Арна"
        kb.add(types.InlineKeyboardButton(text=chan_btn, url=f"https://t.me/{REQUIRED_CHANNEL.replace('@', '')}"))
    
    add_group_btn = "🌐 Guruhga qo'shish" if lang == "uz" else "🌐 Добавить в группу" if lang == "ru" else "🌐 Add to Group" if lang == "en" else "🌐 Топқа қосу"
    kb.add(types.InlineKeyboardButton(
        text=add_group_btn,
        url=f"https://t.me/{bot_username}?startgroup=true"
    ))
    
    # Faqat Bot Admini uchun alohida Admin Panel tugmasi
    if ADMIN_ID and user_id == ADMIN_ID:
        kb.add(types.InlineKeyboardButton(text="👑 Admin Panel", callback_data="admin_panel"))
    
    kb.adjust(2, 2, 1, 1, 1)
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
    bonus_claimed = bool(user.get('channel_bonus_claimed', 0))
    
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
    
    if not bonus_claimed:
        bonus_hint = "\n\n🎁 **Maxsus Sovg'a**: Rasmiy kanalimizga a'zo bo'ling va **+100 Dark Coins** bonusga ega bo'ling!"
        if lang == "ru":
            bonus_hint = "\n\n🎁 **Бонус**: Подпишитесь на наш канал и получите **+100 Dark Coins**!"
        elif lang == "en":
            bonus_hint = "\n\n🎁 **Bonus**: Subscribe to our channel to claim **+100 Dark Coins**!"
        elif lang == "kz":
            bonus_hint = "\n\n🎁 **Бонус**: Ресми арнамызға жазылып, **+100 Dark Coins** алыңыз!"
        status_text += bonus_hint
        
    await message.answer(welcome_text + status_text, reply_markup=get_start_keyboard(user_id, bot_user, lang, bonus_claimed), parse_mode="Markdown")

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
        
    await message.answer(profile_text + stats_text, reply_markup=get_start_keyboard(user_id, bot_user, lang), parse_mode="Markdown")

@router.message(Command("quests", "vazifalar"))
async def cmd_quests_pm(message: types.Message):
    user_id = message.from_user.id
    user = await db.get_user(user_id, message.from_user.username, message.from_user.full_name)
    lang = user.get('language', 'uz')
    user_quests = await db.get_daily_quests(user_id)
    
    title = "📜 **Bugungi Kunlik Vazifalaringiz**:\n\n"
    if lang == "ru":
        title = "📜 **Ваши ежедневные задания на сегодня**:\n\n"
    elif lang == "en":
        title = "📜 **Your Daily Quests for Today**:\n\n"
    elif lang == "kz":
        title = "📜 **Бүгінгі күнделікті тапсырмаларыңыз**:\n\n"
        
    text = title
    if not user_quests:
        text += "Hozircha vazifalar mavjud emas."
    else:
        for q in user_quests:
            status = "✅ Bajarildi" if q.get("completed") else f"⏳ {q.get('progress', 0)}/{q.get('target', 1)}"
            name = q.get(f"name_{lang}", q.get("name_uz", "Vazifa"))
            reward = q.get("reward", 50)
            text += f"• **{name}**: {status} (+{reward} 🪙)\n"
            
    await message.answer(text, parse_mode="Markdown")

SHOP_ITEMS = {
    "shield": {
        "name_uz": "🛡️ XP Qalqoni",
        "name_ru": "🛡️ Щит опыта",
        "name_en": "🛡️ XP Shield",
        "name_kz": "🛡️ Қалқан",
        "cost": 150,
        "desc_uz": "Tunda o'ldirilganda XP va tangalarni yo'qotishdan himoyalaydi",
        "desc_ru": "Защищает от потери XP при ночном убийстве",
        "desc_en": "Protects XP and coins on night death",
        "desc_kz": "Түнде өлтірілгенде XP қорғайды"
    },
    "booster_mafia": {
        "name_uz": "🔴 Mafiya Boosteri",
        "name_ru": "🔴 Бустер Мафии",
        "name_en": "🔴 Mafia Booster",
        "name_kz": "🔴 Мафия бустері",
        "cost": 250,
        "desc_uz": "Keyingi o'yinda Mafiya jamoasiga tushish ehtimolini keskin oshiradi!",
        "desc_ru": "Значительно увеличивает шанс стать Мафией в следующей игре!",
        "desc_en": "Greatly increases the chance of becoming Mafia in the next game!",
        "desc_kz": "Келесі ойында Мафия болу мүмкіндігін арттырады!"
    },
    "booster_detective": {
        "name_uz": "🔵 Komissar Boosteri",
        "name_ru": "🔵 Бустер Комиссара",
        "name_en": "🔵 Detective Booster",
        "name_kz": "🔵 Комиссар бустері",
        "cost": 250,
        "desc_uz": "Keyingi o'yinda Komissar (Sherif) roliga tushish imkoniyati!",
        "desc_ru": "Шанс получить роль Комиссара (Шерифа) в следующей игре!",
        "desc_en": "High chance to get the Detective role in the next game!",
        "desc_kz": "Келесі ойында Комиссар рөлін алу мүмкіндігі!"
    },
    "booster_doctor": {
        "name_uz": "🟡 Shifokor Boosteri",
        "name_ru": "🟡 Бустер Доктора",
        "name_en": "🟡 Doctor Booster",
        "name_kz": "🟡 Дәрігер бустері",
        "cost": 200,
        "desc_uz": "Keyingi o'yinda Shifokor (Doctor) roliga tushish imkoniyati!",
        "desc_ru": "Шанс получить роль Доктора в следующей игре!",
        "desc_en": "High chance to get the Doctor role in the next game!",
        "desc_kz": "Келесі ойында Дәрігер рөлін алу мүмкіндігі!"
    },
    "booster_maniac": {
        "name_uz": "🦹 Telba Boosteri",
        "name_ru": "🦹 Бустер Маньяка",
        "name_en": "🦹 Maniac Booster",
        "name_kz": "🦹 Маньяк бустері",
        "cost": 300,
        "desc_uz": "Keyingi o'yinda yolg'iz qotil — Maniac (Telba) roliga tushish imkoniyati!",
        "desc_ru": "Шанс получить опасную роль Маньяка в следующей игре!",
        "desc_en": "High chance to get the solo Maniac role in the next game!",
        "desc_kz": "Келесі ойында Маньяк рөлін алу мүмкіндігі!"
    }
}

def get_shop_keyboard(lang: str = "uz") -> types.InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    
    # Stars button at the top of the shop
    stars_btn = "⭐️ Tanga sotib olish (Stars)" if lang == "uz" else "⭐️ Купить Монеты (Stars)" if lang == "ru" else "⭐️ Buy Coins (Stars)" if lang == "en" else "⭐️ Монета алу (Stars)"
    kb.add(types.InlineKeyboardButton(text=stars_btn, callback_data="shop_stars_menu"))
    
    for key, item in SHOP_ITEMS.items():
        name = item.get(f"name_{lang}", item["name_uz"])
        cost = item["cost"]
        kb.add(types.InlineKeyboardButton(text=f"{name} — {cost} 🪙", callback_data=f"buy_shop_{key}"))
        
    back_text = "◀️ Orqaga" if lang == "uz" else "◀️ Назад" if lang == "ru" else "◀️ Back" if lang == "en" else "◀️ Артқа"
    kb.add(types.InlineKeyboardButton(text=back_text, callback_data="menu_back"))
    kb.adjust(1)
    return kb.as_markup()

def get_stars_shop_keyboard(lang: str = "uz") -> types.InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    
    c50 = "⭐️ 50 Coins (Starter Pack) — 10 Stars"
    c100 = "⭐️ 100 Coins — 25 Stars"
    c500 = "⭐️ 500 Coins (+50 Bonus) — 99 Stars"
    c1000 = "⭐️ 1000 Coins (+200 Bonus) — 179 Stars"
    
    kb.add(types.InlineKeyboardButton(text=c50, callback_data="buy_stars_coins_50"))
    kb.add(types.InlineKeyboardButton(text=c100, callback_data="buy_stars_coins_100"))
    kb.add(types.InlineKeyboardButton(text=c500, callback_data="buy_stars_coins_500"))
    kb.add(types.InlineKeyboardButton(text=c1000, callback_data="buy_stars_coins_1000"))
    
    back_text = "◀️ Do'konga qaytish" if lang == "uz" else "◀️ В магазин" if lang == "ru" else "◀️ Back to Shop" if lang == "en" else "◀️ Дүкенге қайту"
    kb.add(types.InlineKeyboardButton(text=back_text, callback_data="menu_shop"))
    kb.adjust(1)
    return kb.as_markup()

@router.message(Command("shop", "dokon", "market"))
async def cmd_shop(message: types.Message):
    user_id = message.from_user.id
    user = await db.get_user(user_id, message.from_user.username, message.from_user.full_name)
    lang = user.get('language', 'uz')
    
    if not FEATURE_SHOP:
        await message.answer("⚠️ Do'kon hozirda texnik ta'mirda.")
        return
        
    coins = user.get('coins', 0)
    
    title = f"🛒 **Darktown Do'koni**\n💰 Sizning balansingiz: **{coins} Dark Coins**\n\nQuyidagi buyumlardan birini sotib olishingiz mumkin:\n"
    if lang == "ru":
        title = f"🛒 **Магазин Darktown**\n💰 Ваш баланс: **{coins} Dark Coins**\n\nВыберите предмет для покупки:\n"
    elif lang == "en":
        title = f"🛒 **Darktown Shop**\n💰 Your balance: **{coins} Dark Coins**\n\nChoose an item to purchase:\n"
    elif lang == "kz":
        title = f"🛒 **Darktown Дүкені**\n💰 Сіздің балансыңыз: **{coins} Dark Coins**\n\nСатып алу үшін таңдаңыз:\n"
        
    for item in SHOP_ITEMS.values():
        name = item.get(f"name_{lang}", item["name_uz"])
        desc = item.get(f"desc_{lang}", item["desc_uz"])
        title += f"\n• **{name}** ({item['cost']} 🪙)\n  _{desc}_\n"
        
    await message.answer(title, reply_markup=get_shop_keyboard(lang), parse_mode="Markdown")

@router.callback_query(F.data.startswith("buy_shop_"))
async def cb_buy_shop(cb: types.CallbackQuery):
    if not FEATURE_SHOP:
        await cb.answer("⚠️ Do'kon hozirda mavjud emas.", show_alert=True)
        return
        
    user_id = cb.from_user.id
    lang = await db.get_user_language(user_id)
    item_key = cb.data.replace("buy_shop_", "")
    
    if item_key not in SHOP_ITEMS:
        await cb.answer("⚠️ Buyum topilmadi!", show_alert=True)
        return
        
    item = SHOP_ITEMS[item_key]
    cost = item["cost"]
    
    success, msg = await db.buy_item(user_id, item_key, cost)
    if success:
        user = await db.get_user(user_id)
        name = item.get(f"name_{lang}", item["name_uz"])
        alert_msg = f"🎉 {name} muvaffaqiyatli xarid qilindi!\nQoldiq: {user['coins']} 🪙" if lang == "uz" else f"🎉 {name} успешно куплен!\nБаланс: {user['coins']} 🪙" if lang == "ru" else f"🎉 {name} purchased successfully!\nBalance: {user['coins']} 🪙" if lang == "en" else f"🎉 {name} сәтті сатып алынды!\nҚалдық: {user['coins']} 🪙"
        await cb.answer(alert_msg, show_alert=True)
        
        # Update shop view
        title = f"🛒 **Darktown Do'koni**\n💰 Sizning balansingiz: **{user['coins']} Dark Coins**\n\nQuyidagi buyumlardan birini sotib olishingiz mumkin:\n"
        if lang == "ru":
            title = f"🛒 **Магазин Darktown**\n💰 Ваш баланс: **{user['coins']} Dark Coins**\n\nВыберите предмет для покупки:\n"
        elif lang == "en":
            title = f"🛒 **Darktown Shop**\n💰 Your balance: **{user['coins']} Dark Coins**\n\nChoose an item to purchase:\n"
        elif lang == "kz":
            title = f"🛒 **Darktown Дүкені**\n💰 Сіздің балансыңыз: **{user['coins']} Dark Coins**\n\nСатып алу үшін таңдаңыз:\n"
            
        for it in SHOP_ITEMS.values():
            name_str = it.get(f"name_{lang}", it["name_uz"])
            desc_str = it.get(f"desc_{lang}", it["desc_uz"])
            title += f"\n• **{name_str}** ({it['cost']} 🪙)\n  _{desc_str}_\n"
            
        try:
            await cb.message.edit_text(title, reply_markup=get_shop_keyboard(lang), parse_mode="Markdown")
        except Exception:
            pass
    else:
        err_msg = "⚠️ Tangalaringiz yetarli emas!" if lang == "uz" else "⚠️ Недостаточно монет!" if lang == "ru" else "⚠️ Not enough coins!" if lang == "en" else "⚠️ Монеталар жеткіліксіз!"
        await cb.answer(err_msg, show_alert=True)

@router.callback_query(F.data == "shop_stars_menu")
async def cb_shop_stars_menu(cb: types.CallbackQuery):
    user_id = cb.from_user.id
    lang = await db.get_user_language(user_id)
    user = await db.get_user(user_id)
    coins = user.get('coins', 0)
    
    text = (
        f"⭐️ **Telegram Stars orqali Tanga xarid qilish**\n\n"
        f"💰 Hozirgi balansingiz: **{coins} Dark Coins**\n\n"
        f"Kerakli paketni tanlang va to'g'ridan-to'g'ri Telegram Stars yordamida to'lov qiling:"
    )
    if lang == "ru":
        text = (
            f"⭐️ **Покупка Монет через Telegram Stars**\n\n"
            f"💰 Ваш баланс: **{coins} Dark Coins**\n\n"
            f"Выберите нужный пакет и оплатите напрямую через Telegram Stars:"
        )
    elif lang == "en":
        text = (
            f"⭐️ **Buy Coins with Telegram Stars**\n\n"
            f"💰 Your balance: **{coins} Dark Coins**\n\n"
            f"Choose a package and pay directly with Telegram Stars:"
        )
    elif lang == "kz":
        text = (
            f"⭐️ **Telegram Stars арқылы Монета сатып алу**\n\n"
            f"💰 Балансыңыз: **{coins} Dark Coins**\n\n"
            f"Қажетті топтаманы таңдап, Telegram Stars арқылы төлем жасаңыз:"
        )
    await cb.message.edit_text(text, reply_markup=get_stars_shop_keyboard(lang), parse_mode="Markdown")
    await cb.answer()

@router.callback_query(F.data.startswith("buy_stars_"))
async def cb_buy_stars(cb: types.CallbackQuery):
    pkg = cb.data.replace("buy_stars_", "")
    user_id = cb.from_user.id
    lang = await db.get_user_language(user_id)
    
    packages = {
        "coins_50": {
            "title": "50 Dark Coins (Starter Pack)",
            "desc": "Darktown Mafiya o'yini uchun 50 ta Dark Coins (Sinov paketi)",
            "stars": 10,
            "payload": "coins_50"
        },
        "coins_100": {
            "title": "100 Dark Coins",
            "desc": "Darktown Mafiya o'yini uchun 100 ta Dark Coins",
            "stars": 25,
            "payload": "coins_100"
        },
        "coins_500": {
            "title": "500 Dark Coins (+50 Bonus)",
            "desc": "Darktown Mafiya o'yini uchun 550 ta Dark Coins",
            "stars": 99,
            "payload": "coins_500"
        },
        "coins_1000": {
            "title": "1000 Dark Coins (+200 Bonus)",
            "desc": "Darktown Mafiya o'yini uchun 1200 ta Dark Coins",
            "stars": 179,
            "payload": "coins_1000"
        }
    }
    
    if pkg not in packages:
        await cb.answer("⚠️ Paket topilmadi!", show_alert=True)
        return
        
    p = packages[pkg]
    try:
        await cb.bot.send_invoice(
            chat_id=user_id,
            title=p["title"],
            description=p["desc"],
            payload=p["payload"],
            currency="XTR",
            prices=[types.LabeledPrice(label=p["title"], amount=p["stars"])],
            provider_token=""
        )
        await cb.answer("⭐️ To'lov schyoti yuborildi!")
    except Exception as e:
        logging.error(f"Error sending stars invoice: {e}")
        await cb.answer("⚠️ To'lov schyotini yaratishda xatolik yuz berdi.", show_alert=True)

@router.message(Command("ref", "referral", "taklif"))
async def cmd_referral(message: types.Message):
    user_id = message.from_user.id
    user = await db.get_user(user_id, message.from_user.username, message.from_user.full_name)
    lang = user.get('language', 'uz')
    bot_user = (await message.bot.get_me()).username
    ref_count = await db.get_referral_count(user_id)
    earned_coins = ref_count * 50
    ref_link = f"https://t.me/{bot_user}?start=ref_{user_id}"
    
    share_url = f"https://t.me/share/url?url={ref_link}&text=Darktown%20Mafiya%20o%27yiniga%20qo%27shiling%20va%20+50%20tanga%20bonus%20oling!"
    
    kb = InlineKeyboardBuilder()
    share_text = "📤 Do'stlarga ulashish" if lang == "uz" else "📤 Поделиться с друзьями" if lang == "ru" else "📤 Share with Friends" if lang == "en" else "📤 Достармен бөлісу"
    back_text = "◀️ Orqaga" if lang == "uz" else "◀️ Назад" if lang == "ru" else "◀️ Back" if lang == "en" else "◀️ Артқа"
    kb.add(types.InlineKeyboardButton(text=share_text, url=share_url))
    kb.add(types.InlineKeyboardButton(text=back_text, callback_data="menu_back"))
    kb.adjust(1)
    
    text = (
        f"🎁 **Do'stlarni taklif qilish (Referral dasturi)**\n\n"
        f"Do'stlaringizni Darktown Mafiya o'yiniga taklif qiling va har bir do'stingiz uchun **+50 Dark Coins** bonusga ega bo'ling! Taklif qilingan do'stingiz ham **+50 tanga** oladi.\n\n"
        f"👥 Siz taklif qilgan do'stlar: **{ref_count} ta**\n"
        f"💰 Ishlangan tangalar: **{earned_coins} ta**\n\n"
        f"🔗 **Sizning maxsus taklif havolangiz**:\n`{ref_link}`"
    )
    if lang == "ru":
        text = (
            f"🎁 **Приглашение друзей (Реферальная программа)**\n\n"
            f"Приглашайте друзей в Darktown Mafia и получайте **+50 Dark Coins** за каждого приглашенного друга! Ваш друг также получит **+50 монет**.\n\n"
            f"👥 Приглашено друзей: **{ref_count}**\n"
            f"💰 Заработано монет: **{earned_coins}**\n\n"
            f"🔗 **Ваша реферальная ссылка**:\n`{ref_link}`"
        )
    elif lang == "en":
        text = (
            f"🎁 **Invite Friends (Referral Program)**\n\n"
            f"Invite friends to Darktown Mafia and get **+50 Dark Coins** for each friend! Your friend also gets **+50 coins**.\n\n"
            f"👥 Friends invited: **{ref_count}**\n"
            f"💰 Coins earned: **{earned_coins}**\n\n"
            f"🔗 **Your referral link**:\n`{ref_link}`"
        )
    elif lang == "kz":
        text = (
            f"🎁 **Достарды шақыру (Реферальды бағдарлама)**\n\n"
            f"Достарыңызды Darktown Mafia ойынына шақырып, әр дос үшін **+50 Dark Coins** алыңыз! Сіздің досыңыз да **+50 монета** алады.\n\n"
            f"👥 Шақырылған достар: **{ref_count}**\n"
            f"💰 Табылған монеталар: **{earned_coins}**\n\n"
            f"🔗 **Сіздің сілтемеңіз**:\n`{ref_link}`"
        )
        
    await message.answer(text, reply_markup=kb.as_markup(), parse_mode="Markdown")

@router.callback_query(F.data == "menu_shop")
async def cb_menu_shop(cb: types.CallbackQuery):
    user_id = cb.from_user.id
    user = await db.get_user(user_id)
    lang = user.get('language', 'uz')
    coins = user.get('coins', 0)
    
    title = f"🛒 **Darktown Do'koni**\n💰 Sizning balansingiz: **{coins} Dark Coins**\n\nQuyidagi buyumlardan birini sotib olishingiz mumkin:\n"
    if lang == "ru":
        title = f"🛒 **Магазин Darktown**\n💰 Ваш баланс: **{coins} Dark Coins**\n\nВыберите предмет для покупки:\n"
    elif lang == "en":
        title = f"🛒 **Darktown Shop**\n💰 Your balance: **{coins} Dark Coins**\n\nChoose an item to purchase:\n"
    elif lang == "kz":
        title = f"🛒 **Darktown Дүкені**\n💰 Сіздің балансыңыз: **{coins} Dark Coins**\n\nСатып алу үшін таңдаңыз:\n"
        
    for item in SHOP_ITEMS.values():
        name = item.get(f"name_{lang}", item["name_uz"])
        desc = item.get(f"desc_{lang}", item["desc_uz"])
        title += f"\n• **{name}** ({item['cost']} 🪙)\n  _{desc}_\n"
        
    await cb.message.edit_text(title, reply_markup=get_shop_keyboard(lang), parse_mode="Markdown")
    await cb.answer()

@router.callback_query(F.data == "menu_ref")
async def cb_menu_ref(cb: types.CallbackQuery):
    user_id = cb.from_user.id
    user = await db.get_user(user_id)
    lang = user.get('language', 'uz')
    bot_user = (await cb.bot.get_me()).username
    ref_count = await db.get_referral_count(user_id)
    earned_coins = ref_count * 50
    ref_link = f"https://t.me/{bot_user}?start=ref_{user_id}"
    
    share_url = f"https://t.me/share/url?url={ref_link}&text=Darktown%20Mafiya%20o%27yiniga%20qo%27shiling%20va%20+50%20tanga%20bonus%20oling!"
    
    kb = InlineKeyboardBuilder()
    share_text = "📤 Do'stlarga ulashish" if lang == "uz" else "📤 Поделиться с друзьями" if lang == "ru" else "📤 Share with Friends" if lang == "en" else "📤 Достармен бөлісу"
    back_text = "◀️ Orqaga" if lang == "uz" else "◀️ Назад" if lang == "ru" else "◀️ Back" if lang == "en" else "◀️ Артқа"
    kb.add(types.InlineKeyboardButton(text=share_text, url=share_url))
    kb.add(types.InlineKeyboardButton(text=back_text, callback_data="menu_back"))
    kb.adjust(1)
    
    text = (
        f"🎁 **Do'stlarni taklif qilish (Referral dasturi)**\n\n"
        f"Do'stlaringizni Darktown Mafiya o'yiniga taklif qiling va har bir do'stingiz uchun **+50 Dark Coins** bonusga ega bo'ling! Taklif qilingan do'stingiz ham **+50 tanga** oladi.\n\n"
        f"👥 Siz taklif qilgan do'stlar: **{ref_count} ta**\n"
        f"💰 Ishlangan tangalar: **{earned_coins} ta**\n\n"
        f"🔗 **Sizning maxsaviy taklif havolangiz**:\n`{ref_link}`"
    )
    if lang == "ru":
        text = (
            f"🎁 **Приглашение друзей (Реферальная программа)**\n\n"
            f"Приглашайте друзей в Darktown Mafia и получайте **+50 Dark Coins** за каждого приглашенного друга! Ваш друг также получит **+50 монет**.\n\n"
            f"👥 Приглашено друзей: **{ref_count}**\n"
            f"💰 Заработано монет: **{earned_coins}**\n\n"
            f"🔗 **Ваша реферальная ссылка**:\n`{ref_link}`"
        )
    elif lang == "en":
        text = (
            f"🎁 **Invite Friends (Referral Program)**\n\n"
            f"Invite friends to Darktown Mafia and get **+50 Dark Coins** for each friend! Your friend also gets **+50 coins**.\n\n"
            f"👥 Friends invited: **{ref_count}**\n"
            f"💰 Coins earned: **{earned_coins}**\n\n"
            f"🔗 **Your referral link**:\n`{ref_link}`"
        )
    elif lang == "kz":
        text = (
            f"🎁 **Достарды шақыру (Реферальды бағдарлама)**\n\n"
            f"Достарыңызды Darktown Mafia ойынына шақырып, әр дос үшін **+50 Dark Coins** алыңыз! Сіздің досыңыз да **+50 монета** алады.\n\n"
            f"👥 Шақырылған достар: **{ref_count}**\n"
            f"💰 Табылған монеталар: **{earned_coins}**\n\n"
            f"🔗 **Сіздің сілтемеңіз**:\n`{ref_link}`"
        )
        
    await cb.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="Markdown")
    await cb.answer()

@router.callback_query(F.data == "menu_profile")
async def cb_menu_profile(cb: types.CallbackQuery):
    user_id = cb.from_user.id
    user = await db.get_user(user_id, cb.from_user.username, cb.from_user.full_name)
    lang = user.get('language', 'uz')
    bot_user = (await cb.bot.get_me()).username
    
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
    
    stats_text = ""
    if lang == "uz":
        stats_text = f"\n\n🎮 O'yinlar: **{total_played} ta**\n🏆 G'alabalar: **{total_won} ta** ({win_rate:.1f}%)"
    elif lang == "ru":
        stats_text = f"\n\n🎮 Игры: **{total_played}**\n🏆 Победы: **{total_won}** ({win_rate:.1f}%)"
    elif lang == "en":
        stats_text = f"\n\n🎮 Games: **{total_played}**\n🏆 Wins: **{total_won}** ({win_rate:.1f}%)"
    elif lang == "kz":
        stats_text = f"\n\n🎮 Ойындар: **{total_played}**\n🏆 Жеңістер: **{total_won}** ({win_rate:.1f}%)"
        
    bonus_claimed = bool(user.get('channel_bonus_claimed', 0))
    await cb.message.edit_text(profile_text + stats_text, reply_markup=get_start_keyboard(user_id, bot_user, lang, bonus_claimed), parse_mode="Markdown")
    await cb.answer()

def get_players_leaderboard_text(leaders: list, lang: str) -> str:
    text = get_text(lang, "leaderboard_title")
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    
    for i, u in enumerate(leaders):
        first_name = escape_markdown(u['first_name'])
        username_part = ""
        if u['username']:
            username_esc = escape_markdown(u['username'])
            username_part = f" (@{username_esc})"
        text += f"{medals[i]} **{first_name}**{username_part} — Level {u['level']} ({u['xp']} XP)\n"
        
    if not leaders:
        text += "Hozircha o'yinchilar yo'q."
    return text

def get_groups_leaderboard_text(groups: list, lang: str) -> str:
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    text = "🌐 **DarkTown — Eng Faol Top 10 Guruhlar**:\n\n"
    if lang == "ru":
        text = "🌐 **DarkTown — Топ-10 активных групп**:\n\n"
    elif lang == "en":
        text = "🌐 **DarkTown — Top 10 Active Groups**:\n\n"
    elif lang == "kz":
        text = "🌐 **DarkTown — Үздік 10 белсенді топтар**:\n\n"
        
    for i, g in enumerate(groups):
        medal = medals[i] if i < len(medals) else f"{i+1}."
        title = escape_markdown(g.get('title') or f"Guruh {g['chat_id']}")
        uname = f" (@{escape_markdown(g['username'])})" if g.get('username') else ""
        games = g.get('total_games', 0)
        players = g.get('total_players', 0)
        text += f"{medal} **{title}**{uname}\n   🎮 O'yinlar: **{games} ta** | 👥 Ishtirokchilar: **{players} ta**\n\n"
        
    if not groups:
        text += "Hozircha guruhlar statistikasi mavjud emas."
    return text

@router.callback_query(F.data.in_({"menu_top", "menu_top_players"}))
async def cb_menu_top(cb: types.CallbackQuery):
    user_id = cb.from_user.id
    lang = await db.get_user_language(user_id)
    leaders = await db.get_leaderboard(10)
    text = get_players_leaderboard_text(leaders, lang)
    
    kb = InlineKeyboardBuilder()
    groups_tab_btn = "🌐 Top Guruhlar" if lang == "uz" else "🌐 Топ Групп" if lang == "ru" else "🌐 Top Groups" if lang == "en" else "🌐 Үздік Топтар"
    back_text = "◀️ Orqaga" if lang == "uz" else "◀️ Назад" if lang == "ru" else "◀️ Back" if lang == "en" else "◀️ Артқа"
    kb.add(types.InlineKeyboardButton(text=groups_tab_btn, callback_data="menu_top_groups"))
    kb.add(types.InlineKeyboardButton(text=back_text, callback_data="menu_back"))
    kb.adjust(1)
    
    await cb.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="Markdown")
    await cb.answer()

@router.callback_query(F.data == "menu_top_groups")
async def cb_menu_top_groups(cb: types.CallbackQuery):
    user_id = cb.from_user.id
    lang = await db.get_user_language(user_id)
    groups = await db.get_top_groups(10)
    text = get_groups_leaderboard_text(groups, lang)
    
    kb = InlineKeyboardBuilder()
    players_tab_btn = "👤 O'yinchilar Reytingi" if lang == "uz" else "👤 Топ Игроков" if lang == "ru" else "👤 Top Players" if lang == "en" else "👤 Үздік Ойыншылар"
    back_text = "◀️ Orqaga" if lang == "uz" else "◀️ Назад" if lang == "ru" else "◀️ Back" if lang == "en" else "◀️ Артқа"
    kb.add(types.InlineKeyboardButton(text=players_tab_btn, callback_data="menu_top_players"))
    kb.add(types.InlineKeyboardButton(text=back_text, callback_data="menu_back"))
    kb.adjust(1)
    
    await cb.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="Markdown")
    await cb.answer()

@router.message(Command("top", "leaderboard", "reyting"))
async def cmd_top(message: types.Message):
    user_id = message.from_user.id
    lang = await db.get_user_language(user_id)
    leaders = await db.get_leaderboard(10)
    text = get_players_leaderboard_text(leaders, lang)
    
    kb = InlineKeyboardBuilder()
    groups_tab_btn = "🌐 Top Guruhlar" if lang == "uz" else "🌐 Топ Групп" if lang == "ru" else "🌐 Top Groups" if lang == "en" else "🌐 Үздік Топтар"
    kb.add(types.InlineKeyboardButton(text=groups_tab_btn, callback_data="menu_top_groups"))
    kb.adjust(1)
    await message.answer(text, reply_markup=kb.as_markup(), parse_mode="Markdown")

@router.message(Command("topgroups", "topguruhlar"))
async def cmd_topgroups_pm(message: types.Message):
    user_id = message.from_user.id
    lang = await db.get_user_language(user_id)
    groups = await db.get_top_groups(10)
    text = get_groups_leaderboard_text(groups, lang)
    
    kb = InlineKeyboardBuilder()
    players_tab_btn = "👤 O'yinchilar Reytingi" if lang == "uz" else "👤 Топ Игроков" if lang == "ru" else "👤 Top Players" if lang == "en" else "👤 Үздік Ойыншылар"
    kb.add(types.InlineKeyboardButton(text=players_tab_btn, callback_data="menu_top_players"))
    kb.adjust(1)
    await message.answer(text, reply_markup=kb.as_markup(), parse_mode="Markdown")

@router.callback_query(F.data == "menu_boosters")
async def cb_menu_boosters(cb: types.CallbackQuery):
    user_id = cb.from_user.id
    lang = await db.get_user_language(user_id)
    inventory = await db.get_inventory(user_id)
    bot_user = (await cb.bot.get_me()).username
    
    boosters = {k: v for k, v in inventory.items() if k.startswith("booster_") and v > 0}
    
    if not boosters:
        no_boosters_text = "⚠️ Sizda faol rol boosterlari yo'q.\nUlarni Do'kondan sotib olishingiz mumkin!"
        if lang == "ru":
            no_boosters_text = "⚠️ У вас нет активных бустеров ролей.\nВы можете купить их в Магазине!"
        elif lang == "en":
            no_boosters_text = "⚠️ You have no active role boosters.\nYou can buy them in the Shop!"
        elif lang == "kz":
            no_boosters_text = "⚠️ Сізде белсенді рөлдік бустерлер жоқ.\nОларды Дүкеннен сатып алуға болады!"
            
        kb = InlineKeyboardBuilder()
        if FEATURE_SHOP:
            shop_btn = "🛒 Do'konga o'tish" if lang == "uz" else "🛒 В магазин" if lang == "ru" else "🛒 Go to Shop" if lang == "en" else "🛒 Дүкенге өту"
            kb.add(types.InlineKeyboardButton(text=shop_btn, callback_data="menu_shop"))
        back_text = "◀️ Orqaga" if lang == "uz" else "◀️ Назад" if lang == "ru" else "◀️ Back" if lang == "en" else "◀️ Артқа"
        kb.add(types.InlineKeyboardButton(text=back_text, callback_data="menu_back"))
        kb.adjust(1)
        
        await cb.message.edit_text(no_boosters_text, reply_markup=kb.as_markup())
        await cb.answer()
        return
        
    kb = InlineKeyboardBuilder()
    for item_key, qty in boosters.items():
        if item_key == "booster_active":
            btn_title = f"🎭 Faol Rol ({qty} dona)" if lang == "uz" else f"🎭 Активная роль ({qty} шт)" if lang == "ru" else f"🎭 Active Role ({qty} pcs)" if lang == "en" else f"🎭 Белсенді рөл ({qty} дана)"
        else:
            r_name = item_key.replace("booster_", "").capitalize()
            btn_title = f"🎭 {r_name} ({qty} dona)" if lang == "uz" else f"🎭 {r_name} ({qty} шт)" if lang == "ru" else f"🎭 {r_name} ({qty} pcs)" if lang == "en" else f"🎭 {r_name} ({qty} дана)"
        kb.add(types.InlineKeyboardButton(text=btn_title, callback_data=f"activate_{item_key}"))
    back_text = "◀️ Orqaga" if lang == "uz" else "◀️ Назад" if lang == "ru" else "◀️ Back" if lang == "en" else "◀️ Артқа"
    kb.add(types.InlineKeyboardButton(text=back_text, callback_data="menu_back"))
    kb.adjust(1)
    
    boost_title = "🎭 **Rol Boosterini Faollashtirish**\n\nKeyingi o'yinda qaysi rolni olish ehtimolini oshirmoqchisiz? Tanlang:\n_(O'yin boshlanganda 1 ta booster sarflanadi)_"
    if lang == "ru":
        boost_title = "🎭 **Активация Бустера Роли**\n\nКакую роль вы хотите получить с большей вероятностью в следующей игре? Выберите:\n_(1 бустер будет потрачен при старте игры)_"
    elif lang == "en":
        boost_title = "🎭 **Activate Role Booster**\n\nWhich role do you want to have a higher chance of getting in the next game? Choose:\n_(1 booster will be consumed when the game starts)_"
    elif lang == "kz":
        boost_title = "🎭 **Рөлдік Бустерді Белсендіру**\n\nКелесі ойында қай рөлді алу ықтималдығын арттырғыңыз келеді? Таңдаңыз:\n_(Ойын басталғанда 1 бустер жұмсалады)_"
        
    await cb.message.edit_text(boost_title, reply_markup=kb.as_markup(), parse_mode="Markdown")
    await cb.answer()

@router.callback_query(F.data == "menu_back")
async def cb_menu_back(cb: types.CallbackQuery):
    user_id = cb.from_user.id
    user = await db.get_user(user_id, cb.from_user.username, cb.from_user.full_name)
    lang = user.get('language', 'uz')
    bot_user = (await cb.bot.get_me()).username
    welcome_text = get_text(lang, "start_private", name=cb.from_user.full_name)
    bonus_claimed = bool(user.get('channel_bonus_claimed', 0))
    
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
    
    if not bonus_claimed:
        bonus_hint = "\n\n🎁 **Maxsus Sovg'a**: Rasmiy kanalimizga a'zo bo'ling va **+100 Dark Coins** bonusga ega bo'ling!"
        if lang == "ru":
            bonus_hint = "\n\n🎁 **Бонус**: Подпишитесь на наш канал и получите **+100 Dark Coins**!"
        elif lang == "en":
            bonus_hint = "\n\n🎁 **Bonus**: Subscribe to our channel to claim **+100 Dark Coins**!"
        elif lang == "kz":
            bonus_hint = "\n\n🎁 **Бонус**: Ресми арнамызға жазылып, **+100 Dark Coins** алыңыз!"
        status_text += bonus_hint
        
    await cb.message.edit_text(welcome_text + status_text, reply_markup=get_start_keyboard(user_id, bot_user, lang, bonus_claimed), parse_mode="Markdown")
    await cb.answer()

@router.message(Command("leaderboard"))
async def cmd_leaderboard(message: types.Message):
    user_id = message.from_user.id
    lang = await db.get_user_language(user_id)
    leaders = await db.get_leaderboard(10)
    
    text = get_text(lang, "leaderboard_title")
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    
    for i, user in enumerate(leaders):
        first_name = escape_markdown(user['first_name'])
        username_part = ""
        if user['username']:
            username_esc = escape_markdown(user['username'])
            username_part = f" (@{username_esc})"
        text += f"{medals[i]} **{first_name}**{username_part} — Level {user['level']} ({user['xp']} XP)\n"
        
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
            reply_markup=get_start_keyboard(user_id, bot_user, lang)
        )
        return
        
    kb = InlineKeyboardBuilder()
    for item_key, qty in boosters.items():
        if item_key == "booster_active":
            btn_title = f"🎭 Faol Rol ({qty} dona)" if lang == "uz" else f"🎭 Активная роль ({qty} шт)" if lang == "ru" else f"🎭 Active Role ({qty} pcs)" if lang == "en" else f"🎭 Белсенді рөл ({qty} дана)"
        else:
            r_name = item_key.replace("booster_", "").capitalize()
            btn_title = f"🎭 {r_name} ({qty} dona)" if lang == "uz" else f"🎭 {r_name} ({qty} шт)" if lang == "ru" else f"🎭 {r_name} ({qty} pcs)" if lang == "en" else f"🎭 {r_name} ({qty} дана)"
        kb.add(types.InlineKeyboardButton(text=btn_title, callback_data=f"activate_{item_key}"))
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
    
    if item_key == "booster_active":
        role_name = "Active"
        display_name = "Faol Rol (Mafiya/Komissar/Shifokor)" if lang == "uz" else "Активная роль (Мафия/Комиссар/Доктор)" if lang == "ru" else "Active Role (Mafia/Detective/Doctor)" if lang == "en" else "Белсенді рөл"
    else:
        role_name = item_key.replace("booster_", "").capitalize()
        display_name = role_name
    
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
        success_text = f"🎭 Siz keyingi o'yin uchun **{display_name}** boosterini faollashtirdingiz! O'yin boshlanganda u sarflanadi."
        alert_text = "Booster faollashtirildi!"
        if lang == "ru":
            success_text = f"🎭 Вы активировали бустер **{display_name}** на следующую игру! Он будет потрачен при старте."
            alert_text = "Бустер активирован!"
        elif lang == "en":
            success_text = f"🎭 You activated the **{display_name}** booster for the next game! It will be consumed on start."
            alert_text = "Booster activated!"
        elif lang == "kz":
            success_text = f"🎭 Келесі ойын үшін **{display_name}** бустерін белсендірдіңіз! Ол ойын басталғанда жұмсалады."
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

def get_admin_panel_keyboard() -> types.InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.add(types.InlineKeyboardButton(text="📊 Batafsil Statistika", callback_data="admin_stats"))
    kb.add(types.InlineKeyboardButton(text="📥 O'yinchilar Ro'yxati (Excel)", callback_data="admin_export_excel"))
    kb.add(types.InlineKeyboardButton(text="🎮 Faol O'yinlar", callback_data="admin_active_games"))
    kb.add(types.InlineKeyboardButton(text="📖 Buyruqlar Qo'llanmasi", callback_data="admin_guide"))
    kb.add(types.InlineKeyboardButton(text="💰 O'zimga +1000 🪙", callback_data="admin_self_coins"))
    kb.add(types.InlineKeyboardButton(text="⚡ O'zimga +500 XP", callback_data="admin_self_xp"))
    kb.add(types.InlineKeyboardButton(text="📢 Xabar Tarqatish", callback_data="admin_broadcast_help"))
    kb.add(types.InlineKeyboardButton(text="🚫 Ban / Unban", callback_data="admin_ban_help"))
    kb.add(types.InlineKeyboardButton(text="🔍 Foydalanuvchi Tekshirish", callback_data="admin_user_help"))
    kb.add(types.InlineKeyboardButton(text="◀️ Bosh Menyu", callback_data="menu_back"))
    kb.adjust(2, 2, 2, 2, 1, 1)
    return kb.as_markup()

ADMIN_GUIDE_TEXT = (
    "👑 **DarkTown — Admin Buyruqlari Qo'llanmasi**\n\n"
    "Quyidagi barcha buyruqlar faqat Bot Admini uchun ishlaydi:\n\n"
    "• `/admin` — Admin panelini ochish (barcha tugmalar bilan)\n"
    "• `/export` yoki `/excel` — Barcha o'yinchilarni Excel (.csv) formatida yuklab olish\n"
    "• `/adminhelp` — Ushbu buyruqlar spravkasini ochish\n"
    "• `/user <user_id>` — Foydalanuvchi ma'lumotlarini tekshirish\n"
    "  _Misol:_ `/user 12345678`\n\n"
    "• `/givecoins <user_id> <miqdor>` — Foydalanuvchiga tanga berish\n"
    "  _Misol:_ `/givecoins 12345678 1000`\n\n"
    "• `/givexp <user_id> <miqdor>` — Foydalanuvchiga XP berish\n"
    "  _Misol:_ `/givexp 12345678 500`\n\n"
    "• `/ban <user_id>` — Foydalanuvchini botda bloklash\n"
    "  _Misol:_ `/ban 12345678`\n\n"
    "• `/unban <user_id>` — Foydalanuvchini blokdan chiqarish\n"
    "  _Misol:_ `/unban 12345678`\n\n"
    "• `/broadcast <xabar>` — Barcha o'yinchilarga xabar tarqatish\n"
    "  _Misol:_ `/broadcast Bugun soat 20:00 da o'yin!`\n\n"
    "• `/activegames` — Guruhlardagi hozirgi faol jonli o'yinlar ro'yxati\n\n"
    "💡 _Eslatma: Telegram qidiruvida `/` belgisini yozsangiz, barcha admin buyruqlari avtomatik chiqadi._"
)

@router.callback_query(F.data == "admin_panel")
async def cb_admin_panel(cb: types.CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        await cb.answer("⚠️ Siz bot admini emassiz!", show_alert=True)
        return
        
    stats = await db.get_detailed_admin_analytics()
    from game.manager import game_manager
    active_games = len(game_manager.games)
    
    text = (
        f"👑 **DarkTown — Maxsus Admin Paneli**\n\n"
        f"Assalomu alaykum, Hurmatli Admin!\n\n"
        f"👥 Jami o'yinchilar: **{stats['total_users']} ta**\n"
        f"📅 Bugungi faol o'yinchilar (DAU): **{stats['today_active']} ta**\n"
        f"🎮 Bugun o'ynalgan o'yinlar: **{stats['today_games']} ta**\n"
        f"🕹 Jami o'ynalgan o'yinlar: **{stats['total_games']} ta**\n"
        f"🔥 Hozirgi faol o'yinlar: **{active_games} ta**\n\n"
        f"Kerakli bo'limni tanlang:"
    )
    await cb.message.edit_text(text, reply_markup=get_admin_panel_keyboard(), parse_mode="Markdown")
    await cb.answer()

@router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(cb: types.CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        await cb.answer("⚠️ Siz bot admini emassiz!", show_alert=True)
        return
        
    stats = await db.get_detailed_admin_analytics()
    from game.manager import game_manager
    active_games = len(game_manager.games)
    
    kb = InlineKeyboardBuilder()
    kb.add(types.InlineKeyboardButton(text="📥 Excel Faylni Yuklab Olish", callback_data="admin_export_excel"))
    kb.add(types.InlineKeyboardButton(text="◀️ Admin Panelga qaytish", callback_data="admin_panel"))
    kb.adjust(1)
    
    text = (
        f"📊 **DarkTown Bot — Kengaytirilgan Analitika & Statistika**\n\n"
        f"👥 **Foydalanuvchilar:**\n"
        f"• Jami ro'yxatdan o'tgan: **{stats['total_users']} ta**\n"
        f"• Bugun kirganlar (Faol DAU): **{stats['today_active']} ta**\n"
        f"• Bloklangan foydalanuvchilar: **{stats['banned_count']} ta**\n\n"
        f"🎮 **O'yinlar:**\n"
        f"• Bugun o'ynalgan o'yinlar: **{stats['today_games']} ta**\n"
        f"• Jami o'yinlar soni: **{stats['total_games']} ta**\n"
        f"• Hozir guruhlarda davom etayotgan: **{active_games} ta**\n\n"
        f"💰 **Iqtisodiyot:**\n"
        f"• Muomaladagi jami tangalar: **{stats['total_coins']} 🪙**\n\n"
        f"💡 _Barcha o'yinchilarning to'liq jadvalini Excel formatida yuklab olishingiz mumkin._"
    )
    await cb.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="Markdown")
    await cb.answer()

@router.callback_query(F.data == "admin_export_excel")
async def cb_admin_export_excel(cb: types.CallbackQuery, bot: Bot):
    if cb.from_user.id != ADMIN_ID:
        await cb.answer("⚠️ Siz bot admini emassiz!", show_alert=True)
        return
        
    await cb.answer("⏳ Excel fayl tayyorlanmoqda...")
    users_data = await db.get_all_users_for_export()
    csv_bytes = generate_users_csv(users_data)
    
    today_str = datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = f"DarkTown_Oyinchilar_{today_str}.csv"
    input_file = BufferedInputFile(csv_bytes, filename=filename)
    
    caption = (
        f"📊 **DarkTown Mafiya — Barcha O'yinchilar Ro'yxati**\n\n"
        f"👥 Jami o'yinchilar: **{len(users_data)} ta**\n"
        f"📅 Sana: **{datetime.now().strftime('%Y-%m-%d %H:%M')}**\n\n"
        f"✅ _Ushbu fayl Microsoft Excel va Google Sheets dasturlarida ochish uchun to'liq moslashtirilgan (UTF-8, CSV)._"
    )
    
    await bot.send_document(
        chat_id=cb.from_user.id,
        document=input_file,
        caption=caption,
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "admin_self_coins")
async def cb_admin_self_coins(cb: types.CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        await cb.answer("⚠️ Siz bot admini emassiz!", show_alert=True)
        return
    user_id = cb.from_user.id
    await db.add_xp_and_coins(user_id, 0, 1000)
    user = await db.get_user(user_id)
    await cb.answer(f"🎉 Hisobingizga +1000 Dark Coins qo'shildi!\nJami balansingiz: {user['coins']} 🪙", show_alert=True)

@router.callback_query(F.data == "admin_self_xp")
async def cb_admin_self_xp(cb: types.CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        await cb.answer("⚠️ Siz bot admini emassiz!", show_alert=True)
        return
    user_id = cb.from_user.id
    leveled, new_lvl = await db.add_xp_and_coins(user_id, 500, 0)
    await cb.answer(f"⚡ Hisobingizga +500 XP qo'shildi! (Daraja: {new_lvl})", show_alert=True)

@router.callback_query(F.data == "admin_active_games")
async def cb_admin_active_games(cb: types.CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        await cb.answer("⚠️ Siz bot admini emassiz!", show_alert=True)
        return
    from game.manager import game_manager
    games = game_manager.games
    
    kb = InlineKeyboardBuilder()
    kb.add(types.InlineKeyboardButton(text="◀️ Admin Panelga qaytish", callback_data="admin_panel"))
    
    if not games:
        text = "🎮 **Hozirda faol o'yinlar mavjud emas.**"
    else:
        text = f"🎮 **Hozirgi faol o'yinlar ({len(games)} ta)**:\n\n"
        for chat_id, g in games.items():
            text += f"• Guruh ID: `{chat_id}` | Faza: **{g.phase}** | O'yinchilar: **{len(g.players)} ta**\n"
    
    await cb.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="Markdown")
    await cb.answer()

@router.callback_query(F.data == "admin_broadcast_help")
async def cb_admin_broadcast_help(cb: types.CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        await cb.answer("⚠️ Siz bot admini emassiz!", show_alert=True)
        return
    kb = InlineKeyboardBuilder()
    kb.add(types.InlineKeyboardButton(text="◀️ Admin Panelga qaytish", callback_data="admin_panel"))
    
    text = (
        f"📢 **Xabar Tarqatish (Broadcast) Yo'riqnomasi**\n\n"
        f"Barcha bot foydalanuvchilariga xabar yuborish uchun chatga quyidagicha yozing:\n\n"
        f"`/broadcast Xabaringiz matni shu yerda bo'ladi`\n\n"
        f"Bot barcha a'zolarga xabarni yetkazib, yakunda hisobot beradi."
    )
    await cb.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="Markdown")
    await cb.answer()

@router.callback_query(F.data == "admin_ban_help")
async def cb_admin_ban_help(cb: types.CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        await cb.answer("⚠️ Siz bot admini emassiz!", show_alert=True)
        return
    kb = InlineKeyboardBuilder()
    kb.add(types.InlineKeyboardButton(text="◀️ Admin Panelga qaytish", callback_data="admin_panel"))
    
    text = (
        f"🚫 **Foydalanuvchini Bloklash / Blokdan Chiqarish**\n\n"
        f"• Bloklash uchun: `/ban <user_id>`\n"
        f"• Blokdan chiqarish uchun: `/unban <user_id>`\n\n"
        f"Misol: `/ban 12345678`"
    )
    await cb.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="Markdown")
    await cb.answer()

@router.callback_query(F.data == "admin_user_help")
async def cb_admin_user_help(cb: types.CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        await cb.answer("⚠️ Siz bot admini emassiz!", show_alert=True)
        return
    kb = InlineKeyboardBuilder()
    kb.add(types.InlineKeyboardButton(text="◀️ Admin Panelga qaytish", callback_data="admin_panel"))
    
    text = (
        f"🔍 **Foydalanuvchini Tekshirish**\n\n"
        f"Foydalanuvchi haqida to'liq ma'lumot (balans, daraja, XP, g'alabalar, ban) olish uchun:\n\n"
        f"`/user <user_id>`\n\n"
        f"Misol: `/user 12345678`"
    )
    await cb.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="Markdown")
    await cb.answer()

@router.callback_query(F.data == "admin_guide")
async def cb_admin_guide(cb: types.CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        await cb.answer("⚠️ Siz bot admini emassiz!", show_alert=True)
        return
    kb = InlineKeyboardBuilder()
    kb.add(types.InlineKeyboardButton(text="📥 Qo'llanma Fayli (Yuklab Olish)", callback_data="admin_download_guide"))
    kb.add(types.InlineKeyboardButton(text="◀️ Admin Panelga qaytish", callback_data="admin_panel"))
    kb.adjust(1)
    
    await cb.message.edit_text(ADMIN_GUIDE_TEXT, reply_markup=kb.as_markup(), parse_mode="Markdown")
    await cb.answer()

@router.callback_query(F.data == "admin_download_guide")
async def cb_admin_download_guide(cb: types.CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        await cb.answer("⚠️ Siz bot admini emassiz!", show_alert=True)
        return
    guide_bytes = ADMIN_GUIDE_TEXT.encode('utf-8')
    input_file = BufferedInputFile(guide_bytes, filename="DarkTown_Admin_Qollanma.txt")
    await cb.bot.send_document(
        chat_id=cb.from_user.id,
        document=input_file,
        caption="📖 **DarkTown Admin Buyruqlari va Qo'llanmasi** (Matnli hujjat).",
        parse_mode="Markdown"
    )
    await cb.answer("✅ Qo'llanma fayli yuborildi!", show_alert=True)

@router.message(Command("adminhelp", "adminguide"))
async def cmd_adminhelp(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⚠️ Ushbu buyruq faqat bot admini uchun!")
        return
    kb = InlineKeyboardBuilder()
    kb.add(types.InlineKeyboardButton(text="👑 Admin Panel", callback_data="admin_panel"))
    kb.add(types.InlineKeyboardButton(text="📥 Qo'llanma Fayli", callback_data="admin_download_guide"))
    kb.adjust(2)
    await message.answer(ADMIN_GUIDE_TEXT, reply_markup=kb.as_markup(), parse_mode="Markdown")

@router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        await message.answer(f"⚠️ Ushbu buyruq faqat bot admini uchun!\nSizning ID: `{user_id}`\nConfigdagi Admin ID: `{ADMIN_ID}`", parse_mode="Markdown")
        return
        
    stats = await db.get_detailed_admin_analytics()
    from game.manager import game_manager
    active_games = len(game_manager.games)
    
    text = (
        f"👑 **DarkTown — Maxsus Admin Paneli**\n\n"
        f"Assalomu alaykum, Hurmatli Admin!\n\n"
        f"👥 Jami o'yinchilar: **{stats['total_users']} ta**\n"
        f"📅 Bugungi faol o'yinchilar (DAU): **{stats['today_active']} ta**\n"
        f"🎮 Bugun o'ynalgan o'yinlar: **{stats['today_games']} ta**\n"
        f"🕹 Jami o'ynalgan o'yinlar: **{stats['total_games']} ta**\n"
        f"🔥 Hozirgi faol o'yinlar: **{active_games} ta**\n\n"
        f"Kerakli bo'limni tanlang:"
    )
    await message.answer(text, reply_markup=get_admin_panel_keyboard(), parse_mode="Markdown")

@router.message(Command("export", "exel", "excel"))
async def cmd_export_excel(message: types.Message, bot: Bot):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⚠️ Ushbu buyruq faqat bot admini uchun!")
        return
        
    status_msg = await message.answer("⏳ Excel fayl tayyorlanmoqda, iltimos kuting...")
    users_data = await db.get_all_users_for_export()
    csv_bytes = generate_users_csv(users_data)
    
    today_str = datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = f"DarkTown_Oyinchilar_{today_str}.csv"
    input_file = BufferedInputFile(csv_bytes, filename=filename)
    
    caption = (
        f"📊 **DarkTown Mafiya — Barcha O'yinchilar Ro'yxati**\n\n"
        f"👥 Jami o'yinchilar: **{len(users_data)} ta**\n"
        f"📅 Sana: **{datetime.now().strftime('%Y-%m-%d %H:%M')}**\n\n"
        f"✅ _Ushbu fayl Microsoft Excel va Google Sheets dasturlarida ochish uchun to'liq moslashtirilgan (UTF-8, CSV)._"
    )
    
    await bot.send_document(
        chat_id=message.from_user.id,
        document=input_file,
        caption=caption,
        parse_mode="Markdown"
    )
    try:
        await status_msg.delete()
    except Exception:
        pass

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
        await message.answer(f"✅ O'yinchi `{target_uid}` ga **{amount}** Dark Coins berildi!", parse_mode="Markdown")
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
        await message.answer(f"✅ O'yinchi `{target_uid}` ga **{amount}** XP berildi!", parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"Xato: {e}")

@router.message(Command("ban"))
async def cmd_ban(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⚠️ Ushbu buyruq faqat bot admini uchun!")
        return
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Format: `/ban <user_id>`", parse_mode="Markdown")
        return
    try:
        target_uid = int(args[1].strip("<>"))
        await db.ban_user(target_uid, True)
        await message.answer(f"🚫 Foydalanuvchi `{target_uid}` botda bloklandi!", parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"Xatolik: {e}")

@router.message(Command("unban"))
async def cmd_unban(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⚠️ Ushbu buyruq faqat bot admini uchun!")
        return
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Format: `/unban <user_id>`", parse_mode="Markdown")
        return
    try:
        target_uid = int(args[1].strip("<>"))
        await db.ban_user(target_uid, False)
        await message.answer(f"✅ Foydalanuvchi `{target_uid}` blokdan chiqarildi!", parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"Xatolik: {e}")

@router.message(Command("user"))
async def cmd_user_info(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⚠️ Ushbu buyruq faqat bot admini uchun!")
        return
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Format: `/user <user_id>`", parse_mode="Markdown")
        return
    try:
        target_uid = int(args[1].strip("<>"))
        user = await db.get_user(target_uid)
        is_banned = await db.is_user_banned(target_uid)
        stats = await db.get_user_stats(target_uid)
        total_played = sum(s['games_played'] for s in stats)
        total_won = sum(s['games_won'] for s in stats)
        
        info = (
            f"👤 **Foydalanuvchi Ma'lumotlari**:\n\n"
            f"• ID: `{target_uid}`\n"
            f"• Ism: **{user.get('first_name', 'Noma\'lum')}**\n"
            f"• Username: @{user.get('username') or 'Mavjud emas'}\n"
            f"• Daraja (Level): **{user.get('level', 1)}** (XP: {user.get('xp', 0)})\n"
            f"• Tangalar: **{user.get('coins', 0)} 🪙**\n"
            f"• Qalqon: {'🛡️ Faol' if user.get('shield_active') else '❌ Yo\'q'}\n"
            f"• Bloklangan: {'🚫 Ha' if is_banned else '🟢 Yo\'q'}\n"
            f"• O'yinlar: **{total_played} ta** (G'alaba: {total_won} ta)\n"
        )
        await message.answer(info, parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"Xatolik: {e}")

@router.message(Command("broadcast"))
async def cmd_broadcast(message: types.Message, bot: Bot):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⚠️ Ushbu buyruq faqat bot admini uchun!")
        return
    text_to_send = message.text.replace("/broadcast", "").strip()
    if not text_to_send:
        await message.answer("Format: `/broadcast <yubormoqchi bo'lgan xabaringiz>`", parse_mode="Markdown")
        return
        
    user_ids = await db.get_all_user_ids()
    status_msg = await message.answer(f"⏳ Xabar tarqatish boshlandi... Jami: {len(user_ids)} ta foydalanuvchi.")
    
    sent = 0
    failed = 0
    for uid in user_ids:
        try:
            await bot.send_message(uid, f"📢 **E'lon**:\n\n{text_to_send}", parse_mode="Markdown")
            sent += 1
            await asyncio.sleep(0.05) # Rate limit protection
        except Exception:
            failed += 1
            
    await status_msg.edit_text(
        f"✅ **Xabar tarqatish yakunlandi!**\n\n"
        f"📤 Yetib bordi: **{sent} ta**\n"
        f"❌ Xatolik (bloklaganlar): **{failed} ta**"
    )

@router.message(Command("activegames"))
async def cmd_activegames(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⚠️ Ushbu buyruq faqat bot admini uchun!")
        return
    from game.manager import game_manager
    games = game_manager.games
    if not games:
        await message.answer("🎮 Hozirda guruhlarda faol o'yinlar yo'q.")
        return
    text = f"🎮 **Faol o'yinlar ({len(games)} ta)**:\n\n"
    for chat_id, g in games.items():
        text += f"• Guruh ID: `{chat_id}` | Faza: **{g.phase}** | O'yinchilar: **{len(g.players)} ta**\n"
    await message.answer(text, parse_mode="Markdown")

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

@router.message(Command("friend", "friends"))
async def cmd_friend(message: types.Message):
    user_id = message.from_user.id
    lang = await db.get_user_language(user_id)
    
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
    
    lang = await db.get_user_language(message.from_user.id)
    
    if payload == "vip_1month":
        await db.upgrade_to_vip(message.from_user.id, 30)
        success_msg = "👑 **Tabriklaymiz! VIP status muvaffaqiyatli faollashtirildi!**\nSiz 1 oy davomida maxsus oltin ramka, 2x XP mukofotlari va orqa fonga shaxsiy rasm yuklash imkoniyatiga ega bo'ldingiz."
        if lang == "ru":
            success_msg = "👑 **Поздравляем! VIP-статус успешно активирован!**\nВ течение 1 месяца вам доступны золотая рамка, 2x XP и возможность установить фоновое изображение."
        elif lang == "en":
            success_msg = "👑 **Congratulations! VIP status activated successfully!**\nFor 1 month, you have access to a gold avatar frame, 2x XP rewards, and custom WebApp backgrounds."
        elif lang == "kz":
            success_msg = "👑 **Құттықтаймыз! VIP мәртебесі сәтті белсендірілді!**\n1 ай бойы сізге алтын жақтау, 2 еселенген XP және жеке фондық сурет орнату мүмкіндігі беріледі."
            
        await message.answer(success_msg, parse_mode="Markdown")
        return

    coin_rewards = {
        "coins_50": 50,
        "coins_100": 100,
        "coins_500": 550,
        "coins_1000": 1200
    }
    coins = coin_rewards.get(payload, 0)
    if not coins and payload.startswith("coins_"):
        try:
            coins = int(payload.replace("coins_", ""))
        except ValueError:
            pass
            
    if coins > 0:
        await db.add_xp_and_coins(message.from_user.id, 0, coins)
        
        bonus_text = ""
        if payload == "coins_500":
            bonus_text = " (+50 bonus)"
        elif payload == "coins_1000":
            bonus_text = " (+200 bonus)"
            
        success_msg = f"🎉 **Xarid muvaffaqiyatli yakunlandi!** Hisobingizga **{coins}** tanga{bonus_text} qo'shildi."
        if lang == "ru":
            success_msg = f"🎉 **Покупка успешно завершена!** На ваш баланс зачислено **{coins}** монет{bonus_text}."
        elif lang == "en":
            success_msg = f"🎉 **Purchase completed successfully!** **{coins}** coins{bonus_text} have been added to your balance."
        elif lang == "kz":
            success_msg = f"🎉 **Сатып алу сәтті аяқталды!** Балансыңызға **{coins}** монета{bonus_text} қосылды."
            
        await message.answer(success_msg, parse_mode="Markdown")

@router.callback_query(F.data == "claim_channel_bonus")
async def cb_claim_channel_bonus(cb: types.CallbackQuery):
    user_id = cb.from_user.id
    user = await db.get_user(user_id)
    lang = user.get('language', 'uz')
    bot_user = (await cb.bot.get_me()).username
    from config import REQUIRED_CHANNEL
    
    if await db.is_channel_bonus_claimed(user_id):
        already_msg = "⚠️ Siz allaqachon kanal obunasi uchun bonusni olgansiz!" if lang == "uz" else "⚠️ Вы уже получили бонус за подписку на канал!" if lang == "ru" else "⚠️ You have already claimed the channel bonus!" if lang == "en" else "⚠️ Сіз арнаға жазылу бонусын алғансыз!"
        await cb.answer(already_msg, show_alert=True)
        return
        
    is_member = False
    if REQUIRED_CHANNEL:
        try:
            member = await cb.bot.get_chat_member(REQUIRED_CHANNEL, user_id)
            if member.status in ["creator", "administrator", "member"]:
                is_member = True
        except Exception as e:
            logging.warning(f"Error checking channel sub: {e}")
            
    if is_member:
        await db.claim_channel_bonus(user_id, 100)
        success_msg = "🎉 Tabriklaymiz! Rasmiy kanalimizga a'zo bo'lganingiz uchun +100 Dark Coins qo'shildi!" if lang == "uz" else "🎉 Поздравляем! Вам начислено +100 Dark Coins за подписку на канал!" if lang == "ru" else "🎉 Congratulations! +100 Dark Coins added for subscribing to our channel!" if lang == "en" else "🎉 Құттықтаймыз! Арнаға жазылғаныңыз үшін +100 Dark Coins қосылды!"
        await cb.answer(success_msg, show_alert=True)
        
        # Refresh start menu
        user = await db.get_user(user_id)
        welcome_text = get_text(lang, "start_private", name=cb.from_user.full_name)
        shield_status = "🛡️ Faol" if user['shield_active'] else "❌ Faol emas"
        status_text = "\n\n" + get_text(
            lang, "profile_text",
            level=user['level'],
            xp=user['xp'],
            coins=user['coins'],
            shield=shield_status
        )
        await cb.message.edit_text(welcome_text + status_text, reply_markup=get_start_keyboard(user_id, bot_user, lang, bonus_claimed=True), parse_mode="Markdown")
    else:
        # Show prompt to subscribe
        title = (
            f"🎁 **+100 Dark Coins Sovg'asi!**\n\n"
            f"1. Rasmiy **{REQUIRED_CHANNEL}** kanalimizga a'zo bo'ling;\n"
            f"2. Pastdagi **'✅ Obunani tekshirish'** tugmasini bosing va **+100 tanga**ga ega bo'ling!"
        )
        if lang == "ru":
            title = (
                f"🎁 **Бонус +100 Dark Coins!**\n\n"
                f"1. Подпишитесь на наш официальный канал **{REQUIRED_CHANNEL}**;\n"
                f"2. Нажмите кнопку **'✅ Проверить подписку'** ниже и получите **+100 монет**!"
            )
        elif lang == "en":
            title = (
                f"🎁 **+100 Dark Coins Bonus!**\n\n"
                f"1. Subscribe to our official channel **{REQUIRED_CHANNEL}**;\n"
                f"2. Click the **'✅ Verify Subscription'** button below to claim **+100 coins**!"
            )
        elif lang == "kz":
            title = (
                f"🎁 **+100 Dark Coins Бонусы!**\n\n"
                f"1. Ресми **{REQUIRED_CHANNEL}** арнамызға жазылыңыз;\n"
                f"2. Төмендегі **'✅ Жазылуды тексеру'** батырмасын басып, **+100 монета** алыңыз!"
            )
            
        kb = InlineKeyboardBuilder()
        sub_text = "📢 Kanalga a'zo bo'lish" if lang == "uz" else "📢 Подписаться на канал" if lang == "ru" else "📢 Subscribe to Channel" if lang == "en" else "📢 Арнаға жазылу"
        verify_text = "✅ Obunani tekshirish (+100 🪙)" if lang == "uz" else "✅ Проверить (+100 🪙)" if lang == "ru" else "✅ Verify (+100 🪙)" if lang == "en" else "✅ Тексеру (+100 🪙)"
        back_text = "◀️ Orqaga" if lang == "uz" else "◀️ Назад" if lang == "ru" else "◀️ Back" if lang == "en" else "◀️ Артқа"
        
        kb.add(types.InlineKeyboardButton(text=sub_text, url=f"https://t.me/{REQUIRED_CHANNEL.replace('@', '')}"))
        kb.add(types.InlineKeyboardButton(text=verify_text, callback_data="verify_channel_bonus"))
        kb.add(types.InlineKeyboardButton(text=back_text, callback_data="menu_back"))
        kb.adjust(1)
        
        await cb.message.edit_text(title, reply_markup=kb.as_markup(), parse_mode="Markdown")
        await cb.answer()

@router.callback_query(F.data.in_({"verify_channel_bonus", "check_channel_sub"}))
async def cb_verify_channel_bonus(cb: types.CallbackQuery):
    user_id = cb.from_user.id
    user = await db.get_user(user_id)
    lang = user.get('language', 'uz')
    bot_user = (await cb.bot.get_me()).username
    from config import REQUIRED_CHANNEL
    
    if await db.is_channel_bonus_claimed(user_id):
        already_msg = "⚠️ Siz allaqachon kanal obunasi uchun bonusni olgansiz!" if lang == "uz" else "⚠️ Вы уже получили бонус за подписку на канал!" if lang == "ru" else "⚠️ You have already claimed the channel bonus!" if lang == "en" else "⚠️ Сіз арнаға жазылу бонусын алғансыз!"
        await cb.answer(already_msg, show_alert=True)
        return
        
    is_member = False
    if REQUIRED_CHANNEL:
        try:
            member = await cb.bot.get_chat_member(REQUIRED_CHANNEL, user_id)
            if member.status in ["creator", "administrator", "member"]:
                is_member = True
        except Exception as e:
            logging.warning(f"Error checking channel sub: {e}")
            
    if is_member:
        await db.claim_channel_bonus(user_id, 100)
        success_msg = "🎉 Tabriklaymiz! Rasmiy kanalimizga a'zo bo'lganingiz uchun +100 Dark Coins qo'shildi!" if lang == "uz" else "🎉 Поздравляем! Вам начислено +100 Dark Coins за подписку на канал!" if lang == "ru" else "🎉 Congratulations! +100 Dark Coins added for subscribing to our channel!" if lang == "en" else "🎉 Құттықтаймыз! Арнаға жазылғаныңыз үшін +100 Dark Coins қосылды!"
        await cb.answer(success_msg, show_alert=True)
        
        user = await db.get_user(user_id)
        welcome_text = get_text(lang, "start_private", name=cb.from_user.full_name)
        shield_status = "🛡️ Faol" if user['shield_active'] else "❌ Faol emas"
        status_text = "\n\n" + get_text(
            lang, "profile_text",
            level=user['level'],
            xp=user['xp'],
            coins=user['coins'],
            shield=shield_status
        )
        await cb.message.edit_text(welcome_text + status_text, reply_markup=get_start_keyboard(user_id, bot_user, lang, bonus_claimed=True), parse_mode="Markdown")
    else:
        not_sub_msg = f"⚠️ Siz hali {REQUIRED_CHANNEL} kanaliga obuna bo'lmadingiz. Avval kanalga a'zo bo'ling!" if lang == "uz" else f"⚠️ Вы еще не подписались на канал {REQUIRED_CHANNEL}!" if lang == "ru" else f"⚠️ You haven't subscribed to {REQUIRED_CHANNEL} yet!" if lang == "en" else f"⚠️ Сіз әлі {REQUIRED_CHANNEL} арнасына жазылмадыңыз!"
        await cb.answer(not_sub_msg, show_alert=True)
