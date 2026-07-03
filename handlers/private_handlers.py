import logging
from aiogram import Router, F, Bot, types
from game.manager import game_manager

router = Router()

# Only process private chat messages
router.message.filter(F.chat.type == "private")

async def register_night_choice(cb: types.CallbackQuery, action_type: str, target_id: int):
    user_id = cb.from_user.id
    
    # Find game where user is active
    game = game_manager.get_game_by_player(user_id)
    if not game or game.phase != "night":
        await cb.answer("⚠️ Hozir tungi bosqich emas yoki o'yin topilmadi!", show_alert=True)
        return
        
    player = game.players.get(user_id)
    if not player or not player.is_alive:
        await cb.answer("⚠️ Siz o'yinda emassiz yoki tirik emassiz!", show_alert=True)
        return

    target_player = game.players.get(target_id)
    if not target_player or not target_player.is_alive:
        await cb.answer("⚠️ Ushbu o'yinchi tirik emas yoki topilmadi!", show_alert=True)
        return

    # Check if they are blocked (in case the block was already applied, but courtesan blocks are usually evaluated at night end)
    # Actually, we let them make choices. We evaluate block during night processing.
    
    # Process choice
    if action_type == "mafia":
        if player.role not in ["Mafia", "Don"]:
            await cb.answer("⚠️ Siz mafiya emassiz!", show_alert=True)
            return
        game.night_actions["mafia"][user_id] = target_id
        await cb.message.edit_text(f"🔴 Siz **{target_player.name}**ni o'ldirishga ovoz berdingiz. Tanlov qabul qilindi!")
        
    elif action_type == "don":
        if player.role != "Don":
            await cb.answer("⚠️ Siz Don emassiz!", show_alert=True)
            return
        game.night_actions["don"] = target_id
        await cb.message.edit_text(f"🕶️ Siz **{target_player.name}**ni tekshirishni tanladingiz. Tanlov qabul qilindi!")
        
    elif action_type == "det":
        if player.role != "Detective":
            await cb.answer("⚠️ Siz Komissar emassiz!", show_alert=True)
            return
        game.night_actions["detective_check"] = target_id
        await cb.message.edit_text(f"🔵 Siz **{target_player.name}**ni tekshirishni tanladingiz. Tun oxirida natija yuboriladi.")
        
    elif action_type == "doc":
        if player.role != "Doctor":
            await cb.answer("⚠️ Siz Shifokor emassiz!", show_alert=True)
            return
        game.night_actions["doctor"] = target_id
        await cb.message.edit_text(f"🟡 Siz **{target_player.name}**ni davolashni tanladingiz. Tanlov qabul qilindi!")
        
    elif action_type == "guard":
        if player.role != "Bodyguard":
            await cb.answer("⚠️ Siz Tansoqchi emassiz!", show_alert=True)
            return
        game.night_actions["bodyguard"] = target_id
        await cb.message.edit_text(f"🛡️ Siz **{target_player.name}**ni himoya qilishni tanladingiz. Tanlov qabul qilindi!")
        
    elif action_type == "block":
        if player.role != "Courtesan":
            await cb.answer("⚠️ Siz Kutizanka emassiz!", show_alert=True)
            return
        game.night_actions["courtesan"] = target_id
        await cb.message.edit_text(f"🌸 Siz **{target_player.name}**ni bloklashni tanladingiz. Tanlov qabul qilindi!")
        
    elif action_type == "maniac":
        if player.role != "Maniac":
            await cb.answer("⚠️ Siz Telba (Maniac) emassiz!", show_alert=True)
            return
        game.night_actions["maniac"] = target_id
        await cb.message.edit_text(f"🦹 Siz **{target_player.name}**ni o'ldirishni tanladingiz. Tanlov qabul qilindi!")
        
    await cb.answer("Tanlov qabul qilindi!")

# Setup callbacks mapping
@router.callback_query(F.data.startswith("mafia_"))
async def cb_mafia(cb: types.CallbackQuery):
    target_id = int(cb.data.replace("mafia_", ""))
    await register_night_choice(cb, "mafia", target_id)

@router.callback_query(F.data.startswith("don_"))
async def cb_don(cb: types.CallbackQuery):
    target_id = int(cb.data.replace("don_", ""))
    await register_night_choice(cb, "don", target_id)

@router.callback_query(F.data == "det_choice_check")
async def cb_det_choice_check(cb: types.CallbackQuery):
    user_id = cb.from_user.id
    game = game_manager.get_game_by_player(user_id)
    if game and game.phase == "night":
        player = game.players.get(user_id)
        if player and player.role == "Detective" and player.is_alive:
            # Check for event Fog
            if game.event and game.event["key"] == "fog":
                await cb.answer("🌫️ Qalin tuman sababli bugun tunda tekshiruv o'tkaza olmaysiz!", show_alert=True)
                return
                
            alive_players = game.get_alive_players()
            kb = InlineKeyboardBuilder()
            for p in alive_players:
                if p.user_id != user_id:
                    kb.add(types.InlineKeyboardButton(text=p.name, callback_data=f"det_{p.user_id}"))
            kb.adjust(2)
            await cb.message.edit_text("🔍 **Komissar tekshiruvi**: Rolini aniqlamoqchi bo'lgan o'yinchini tanlang:", reply_markup=kb.as_markup())
            await cb.answer()

@router.callback_query(F.data == "det_choice_shoot")
async def cb_det_choice_shoot(cb: types.CallbackQuery):
    user_id = cb.from_user.id
    game = game_manager.get_game_by_player(user_id)
    if game and game.phase == "night":
        player = game.players.get(user_id)
        if player and player.role == "Detective" and player.is_alive:
            alive_players = game.get_alive_players()
            kb = InlineKeyboardBuilder()
            for p in alive_players:
                if p.user_id != user_id:
                    kb.add(types.InlineKeyboardButton(text=p.name, callback_data=f"detshoot_{p.user_id}"))
            kb.adjust(2)
            await cb.message.edit_text("🔫 **Komissar o'q otishi**: Kimni otib o'ldirmoqchisiz?", reply_markup=kb.as_markup())
            await cb.answer()

@router.callback_query(F.data.startswith("detshoot_"))
async def cb_detshoot(cb: types.CallbackQuery):
    user_id = cb.from_user.id
    target_id = int(cb.data.replace("detshoot_", ""))
    game = game_manager.get_game_by_player(user_id)
    if game and game.phase == "night":
        player = game.players.get(user_id)
        if player and player.role == "Detective" and player.is_alive:
            target_player = game.players.get(target_id)
            if target_player and target_player.is_alive:
                game.night_actions["detective_shoot"] = target_id
                await cb.message.edit_text(f"🔫 Siz **{target_player.name}**ni otib o'ldirishni tanladingiz. Tanlov qabul qilindi!")
                await cb.answer("Tanlov qabul qilindi!")

@router.callback_query(F.data.startswith("det_"))
async def cb_det(cb: types.CallbackQuery):
    target_id = int(cb.data.replace("det_", ""))
    await register_night_choice(cb, "det", target_id)

@router.callback_query(F.data.startswith("doc_"))
async def cb_doc(cb: types.CallbackQuery):
    target_id = int(cb.data.replace("doc_", ""))
    await register_night_choice(cb, "doc", target_id)

@router.callback_query(F.data.startswith("guard_"))
async def cb_guard(cb: types.CallbackQuery):
    target_id = int(cb.data.replace("guard_", ""))
    await register_night_choice(cb, "guard", target_id)

@router.callback_query(F.data.startswith("block_"))
async def cb_block(cb: types.CallbackQuery):
    target_id = int(cb.data.replace("block_", ""))
    await register_night_choice(cb, "block", target_id)

@router.callback_query(F.data.startswith("maniac_"))
async def cb_maniac(cb: types.CallbackQuery):
    target_id = int(cb.data.replace("maniac_", ""))
    await register_night_choice(cb, "maniac", target_id)

@router.message()
async def private_text_handler(message: types.Message):
    user_id = message.from_user.id
    game = game_manager.get_game_by_player(user_id)
    if game and game.waiting_last_words.get(user_id):
        game.last_words[user_id] = message.text
        game.waiting_last_words[user_id] = False
        await message.answer("✍️ Vasiyatingiz qabul qilindi. U tong otganda guruhda e'lon qilinadi.")
        return
