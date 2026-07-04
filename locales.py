# locales.py

TEXTS = {
    "uz": {
        "start_private": "👋 **Assalomu alaykum, {name}!**\n\nDarktown Mafia botiga xush kelibsiz!\n\nBu bot guruhlarda qiziqarli asinxron **Mafiya** o'yinlarini tashkil qilish uchun xizmat qiladi. O'yinni boshlash uchun uni guruhga qo'shing va `/newgame` buyrug'ini bering.",
        "lang_changed": "✅ Bot tili **O'zbekcha**ga o'zgartirildi!",
        "lang_select": "🌐 Bot tilini tanlang:",
        "only_admin_lang": "⚠️ Faqat guruh administratorlari guruh tilini o'zgartira oladi!",
        "new_game_created": "🎮 **Yangi o'yin lobisi yaratildi!**\n\nO'yinda ishtirok etish uchun pastdagi tugmani bosing.\n⏳ O'yin boshlanishiga **2 daqiqa** qoldi (kamida 5 kishi kerak).",
        "lobby_join": "🙋‍♂️ Qo'shilish",
        "lobby_leave": "🚪 Chiqish",
        "lobby_start": "🚀 Boshlash",
        "joined_lobby": "✅ Siz lobiga qo'shildingiz!",
        "left_lobby": "🚪 Siz lobidan chiqdingiz!",
        "game_started_announcement": "🎭 **Rollar taqsimlandi!** Har bir o'yinchiga o'z roli shaxsiy chatda yuborildi.\n\n🌙 **Qorong'u tushmoqda... Tun boshlandi!**\nBarcha o'yinchilar shaxsiy chatda yoki Mini App-da harakat qilsin.",
        "night_fell": "🌙 **Shahar uzra tun cho'kdi... Barcha tinch aholi shirin uyquda. Mafiya va faol rollar tunda uyg'onmoqda.**\n\n_(Harakatlarni bajarish uchun shaxsiy chatga o'ting yoki Mini App-ni oching!)_",
        "day_broke": "🌅 **Tong otdi! Darktown shahri uyg'ondi...**\n\n",
        "day_discussion": "💬 **Shahar uyg'ondi! Kun boshlandi. Munozara maydoni ochiq.**\nShubha ostidagilarni aniqlang, munozara qiling va gumondorlarni o'rtaga chiqaring.\n⏳ Ovoz berish bosqichi boshlanishiga **60 soniya** qoldi.",
        "voting_started": "🗳️ **Ovoz berish boshlandi!**\nKimni dorda osmoqchisiz? Quyidagi tugmalardan birini tanlang.\nOvoz berish 45 soniya davom etadi.",
        "voting_results": "🗳️ **Ovoz berish natijalari**:\n",
        "game_ended": "🎉 **O'yin yakunlandi!**\n\nG'olib tomon: **{winner}**\n\n",
        "rewards_title": "💰 **Mukofotlar (XP & Tangalar)**:\n",
        "profile_text": "👤 **Sizning profilingiz**:\n\n⭐ Daraja: **{level}**\n📈 Tajriba: **{xp}/500**\n💰 Tangalar: **{coins}**\n🛡️ Faol Qalqon: **{shield}**",
        "leaderboard_title": "🏆 **Global Top 10 O'yinchilar**:\n\n",
        "no_active_game": "⚠️ Bu guruhda faol o'yin topilmadi.",
        "already_in_game": "⚠️ Siz allaqachon lobidasiz!",
        "not_in_game": "⚠️ Siz lobida emassiz!",
        "game_min_players": "⚠️ O'yinni boshlash uchun kamida 5 ta o'yinchi bo'lishi kerak!",
        "help_text": (
            "ℹ️ **Darktown Mafia Bot - Nimalar qila oladi?**\n\n"
            "Bu bot guruhlarda asinxron **Mafiya** o'yinlarini tashkil qilish va o'ynash uchun yaratilgan. Barcha o'yin boshqaruvi Telegram chatida va maxsus **Mini App** interfeysida amalga oshiriladi.\n\n"
            "**Asosiy imkoniyatlar**:\n"
            "1. 🎭 **8 ta Noyob Rollar**: Mafiya, Don, Komissar, Shifokor, Tansoqchi, Kutizanka, Telba (Maniac) va Tinch aholi.\n"
            "2. 📱 **Telegram Mini App**: Shaxsiy profil, o'yin statistikasi, do'kon (boosterlar va qalqonlar sotib olish), global yetakchilar reytingi va jonli o'yin maydoni!\n"
            "3. 🔫 **Komissar Qobiliyati**: Komissar tunda nafaqat tekshira oladi, balki gumondorni otib ham tashlay oladi!\n"
            "4. 💀 **Oxirgi So'z (Vasiyatnoma)**: Tunda o'ldirilgan o'yinchi shaxsiy chatida botga o'z vasiyatini yozadi va bot uni tongda guruhga e'lon qiladi.\n"
            "5. 📊 **Tiriklar jadvali**: Tong otganda tirik qolgan o'yinchilar jadvali guruhda yangilanib boradi.\n\n"
            "**Mavjud buyruqlar**:\n"
            "/profile - Profilingiz va statslaringizni ko'rish\n"
            "/leaderboard - Global Top 10 o'yinchilar\n"
            "/boost - Faol boosterlaringizni ko'rish\n"
            "/rules - O'yin va guruh qoidalari\n"
            "/friend - Do'stlarimiz kanallari\n"
            "/newgame - Guruhda yangi o'yin boshlash (lobi)"
        ),
        "rules_text": (
            "📖 **O'yin va Guruh Qoidalari**\n\n"
            "**🎮 O'YIN QOIDALARI**:\n"
            "1. **Maqsad**:\n"
            "   * **Tinch aholi**: Barcha Mafiya va Telbalarni topib dorda osish.\n"
            "   * **Mafiya**: Shahar ahlini yo'qotib, son jihatdan tenglashish.\n"
            "   * **Telba (Maniac)**: Yakka o'zi tirik qolgan so'nggi o'yinchi bo'lish.\n"
            "2. **Bosqichlar**:\n"
            "   * **🌙 Tun**: Faol rollar o'z qobiliyatlarini ishga soladilar (o'ldirish, davolash, tekshirish).\n"
            "   * **🌅 Kun**: Tungi yo'qotishlar va vasiyatnomalar o'qiladi. O'yinchilar munozara olib boradilar.\n"
            "   * **🗳️ Ovoz berish**: Gumondorni dorda osish uchun ovoz beriladi. Ko'p ovoz olgan o'yinchi osiladi.\n\n"
            "**⚠️ GURUH QOIDALARI**:\n"
            "1. Kurash madaniyatli bo'lishi kerak. Haqorat va so'kinish qat'iyan man etiladi.\n"
            "2. O'yin boshlangach uni tashlab ketish (afk bo'lish) boshqalarning o'yinini buzadi. Bunday o'yinchilar jazolanadi.\n"
            "3. O'yin vaqtida o'lganlar guruhda yozishi yoki faol o'yinchilar roliga aralashishi taqiqlanadi."
        ),
        "friend_text": (
            "🤝 **Do'stlarimiz va Hamkorlarimiz kanallari**\n\n"
            "Quyidagi tugmalar orqali rasmiy guruhimizga va foydali kanallarga qo'shilishingiz mumkin:"
        ),
        "group_help_text": (
            "ℹ️ **Darktown Mafia Bot - Guruh Yordami**\n\n"
            "Guruhda asinxron mafiya o'yinlarini o'ynash uchun quyidagi buyruqlardan foydalaning:\n\n"
            "/newgame - Yangi o'yin (lobi) yaratish. (Lobi 2 daqiqa davomida ochiq bo'ladi va kamida 5 kishi yig'ilgach boshlanadi).\n"
            "/start yoki /startgame - Yig'ilgan o'yinchilar bilan o'yinni darhol boshlash (faqat lobi yaratuvchisi yoki admin uchun).\n"
            "/leave - Lobidan yoki o'yindan chiqish.\n"
            "/rules - O'yin va guruh qoidalari bilan tanishish\n"
            "/friend - Rasmiy guruh va do'stlar kanallar ro'yxati"
        ),
        "role_assigned_private": "🎭 **Sizning rolingiz**: {role_emoji} **{role}**\n\n{details}\n\nO'yin tez orada boshlanadi. Tungi harakatlarga tayyor turing!",
        "game_joined_success": "✅ Siz muvaffaqiyatli guruh o'yiniga qo'shildingiz!",
        "game_left_success": "🚪 Siz o'yinni tark etdingiz.",
        "cannot_leave_active": "⚠️ O'yin faol bosqichda bo'lganda uni tark eta olmaysiz!",
        "referral_welcome": "🎁 **Siz taklifnoma orqali qo'shildingiz!** Sizga va taklif qilgan do'stingizga **+50 tanga** bonus taqdim etildi!",
        "referral_notification": "👥 **Do'stingiz botga qo'shildi!** Siz taklif qilganligingiz uchun **+50 tanga** bonus oldingiz!"
    },
    "ru": {
        "start_private": "👋 **Здравствуйте, {name}!**\n\nДобро пожаловать в бот Darktown Mafia!\n\nЭтот бот используется для организации увлекательных асинхронных игр в **Мафию** в группах. Чтобы начать игру, добавьте бота в группу и отправьте команду `/newgame`.",
        "lang_changed": "✅ Язык бота изменен на **Русский**!",
        "lang_select": "🌐 Выберите язык бота:",
        "only_admin_lang": "⚠️ Только администраторы группы могут менять язык группы!",
        "new_game_created": "🎮 **Создано новое лобби игры!**\n\nНажмите кнопку ниже, чтобы принять участие.\n⏳ До начала игры осталось **2 минуты** (требуется минимум 5 человек).",
        "lobby_join": "🙋‍♂️ Присоединиться",
        "lobby_leave": "🚪 Выйти",
        "lobby_start": "🚀 Начать",
        "joined_lobby": "✅ Вы присоединились к лобби!",
        "left_lobby": "🚪 Вы вышли из лобби!",
        "game_started_announcement": "🎭 **Роли распределены!** Каждому игроку его роль отправлена в личные сообщения.\n\n🌙 **Наступает ночь... Игра началась!**\nВсе игроки делают свои ночные ходы в ЛС или в Mini App.",
        "night_fell": "🌙 **На город опускается ночь... Мирные жители засыпают, просыпаются мафия и активные роли.**\n\n_(Для совершения ходов перейдите в личные сообщения или откройте Mini App!)_",
        "day_broke": "🌅 **Наступило утро! Жители города проснулись...**\n\n",
        "day_discussion": "💬 **Город проснулся! Наступил день. Время для обсуждений открыто.**\nВысказывайте подозрения и находите мафию.\n⏳ До начала голосования осталось **60 секунд**.",
        "voting_started": "🗳️ **Голосование началось!**\nКого вы хотите повесить на площади? Выберите один из вариантов ниже.\nГолосование длится 45 секунд.",
        "voting_results": "🗳️ **Результаты голосования**:\n",
        "game_ended": "🎉 **Игра окончена!**\n\nПобедила фракция: **{winner}**\n\n",
        "rewards_title": "💰 **Награды (XP и монеты)**:\n",
        "profile_text": "👤 **Ваш профиль**:\n\n⭐ Уровень: **{level}**\n📈 Опыт: **{xp}/500**\n💰 Монеты: **{coins}**\n🛡️ Активный щит: **{shield}**",
        "leaderboard_title": "🏆 **Глобальный Топ 10 игроков**:\n\n",
        "no_active_game": "⚠️ Активная игра в этой группе не найдена.",
        "already_in_game": "⚠️ Вы уже находитесь в лобби!",
        "not_in_game": "⚠️ Вас нет в лобби!",
        "game_min_players": "⚠️ Для начала игры требуется минимум 5 игроков!",
        "help_text": (
            "ℹ️ **Darktown Mafia Bot - Что может этот бот?**\n\n"
            "Этот бот создан для игры в асинхронную **Мафию** в группах Telegram. Все управление происходит в чате и через **Mini App** интерфейс.\n\n"
            "**Основные возможности**:\n"
            "1. 🎭 **8 Уникальных ролей**: Мафия, Дон, Комиссар, Доктор, Телохранитель, Куртизанка, Маньяк и Мирный житель.\n"
            "2. 📱 **Telegram Mini App**: Профиль, детальная статистика, магазин (бустеры ролей, щиты опыта), таблица лидеров и интерактивная арена игры!\n"
            "3. 🔫 **Выбор Комиссара**: Комиссар ночью может не только проверить роль, но и застрелить подозреваемого!\n"
            "4. 💀 **Последнее слово (Завещание)**: Убитый ночью игрок пишет свое завещание боту в ЛС, и утром бот отправляет его в группу.\n"
            "5. 📊 **Таблица живых**: Список выживших игроков обновляется каждое утро.\n\n"
            "**Доступные команды**:\n"
            "/profile - Посмотреть свой профиль\n"
            "/leaderboard - Таблица лучших игроков\n"
            "/boost - Посмотреть активные бустеры\n"
            "/rules - Правила игры и группы\n"
            "/friend - Наши каналы и друзья\n"
            "/newgame - Создать новое лобби в группе"
        ),
        "rules_text": (
            "📖 **Правила игры и группы**\n\n"
            "**🎮 ПРАВИЛА ИГРЫ**:\n"
            "1. **Цель**:\n"
            "   * **Мирные жители**: Найти и повесить всю мафию и маньяка.\n"
            "   * **Мафия**: Избавиться от мирных жителей и сравняться с ними по количеству.\n"
            "   * **Маньяк**: Остаться последним выжившим в игре.\n"
            "2. **Фазы**:\n"
            "   * **🌙 Ночь**: Активные роли делают свои ходы в ЛС бота или в Mini App.\n"
            "   * **🌅 День**: Объявляются ночные жертвы и завещания. Игроки ведут обсуждение.\n"
            "   * **🗳️ Голосование**: Голосование за казнь подозреваемого. Игрок с наибольшим количеством голосов вешается.\n\n"
            "**⚠️ ПРАВИЛА ГРУППЫ**:\n"
            "1. Соблюдайте вежливость. Любые оскорбления и мат строго запрещены.\n"
            "2. Выходить из активной игры (afk) запрещено. Нарушители наказываются.\n"
            "3. Мертвым игрокам запрещено общаться в группе во время текущей игры."
        ),
        "friend_text": (
            "🤝 **Наши каналы и партнеры**\n\n"
            "Присоединяйтесь к нашей официальной группе и каналам через кнопки ниже:"
        ),
        "group_help_text": (
            "ℹ️ **Darktown Mafia Bot - Помощь в группе**\n\n"
            "Используйте следующие команды для игры в группе:\n\n"
            "/newgame - Создать лобби новой игры (будет открыто 2 минуты, требуется минимум 5 игроков).\n"
            "/start или /startgame - Начать игру немедленно с собравшимися игроками (только для создателя лобби или админа).\n"
            "/leave - Выйти из лобби или активной игры.\n"
            "/rules - Ознакомиться с правилами игры и чата\n"
            "/friend - Список дружественных каналов и ресурсов"
        ),
        "role_assigned_private": "🎭 **Ваша роль**: {role_emoji} **{role}**\n\n{details}\n\nИгра начнется в ближайшее время. Будьте готовы к ночным действиям!",
        "game_joined_success": "✅ Вы успешно присоединились к игре!",
        "game_left_success": "🚪 Вы покинули игру.",
        "cannot_leave_active": "⚠️ Вы не можете покинуть игру в активной фазе!",
        "referral_welcome": "🎁 **Вы присоединились по приглашению!** Вам и вашему другу начислено по **+50 монет**!",
        "referral_notification": "👥 **Ваш друг присоединился по ссылке!** Вы получили бонус **+50 монет**!"
    },
    "en": {
        "start_private": "👋 **Hello, {name}!**\n\nWelcome to Darktown Mafia bot!\n\nThis bot organizes exciting asynchronous **Mafia** games in groups. To start a game, add the bot to a group and send the `/newgame` command.",
        "lang_changed": "✅ Bot language changed to **English**!",
        "lang_select": "🌐 Select bot language:",
        "only_admin_lang": "⚠️ Only group administrators can change the group language!",
        "new_game_created": "🎮 **New game lobby created!**\n\nPress the button below to join the game.\n⏳ The game starts in **2 minutes** (minimum 5 players required).",
        "lobby_join": "🙋‍♂️ Join",
        "lobby_leave": "🚪 Leave",
        "lobby_start": "🚀 Start",
        "joined_lobby": "✅ You have joined the lobby!",
        "left_lobby": "🚪 You have left the lobby!",
        "game_started_announcement": "🎭 **Roles assigned!** Each player has received their role privately.\n\n🌙 **Night is falling... The game has started!**\nAll players make their night moves in private chat or Mini App.",
        "night_fell": "🌙 **Night falls over the city... All citizens fall asleep. Mafia and active roles wake up to perform their actions.**\n\n_(Go to private chat or open the Mini App to make your moves!)_",
        "day_broke": "🌅 **Morning has come! The citizens of Darktown wake up...**\n\n",
        "day_discussion": "💬 **The city is awake! Day has started. Discussion channel is open.**\nDiscuss, find suspects, and reveal the mafia.\n⏳ **60 seconds** left until voting starts.",
        "voting_started": "🗳️ **Voting started!**\nWho do you want to hang in the public square? Choose one of the options below.\nVoting lasts for 45 seconds.",
        "voting_results": "🗳️ **Voting results**:\n",
        "game_ended": "🎉 **Game ended!**\n\nWinning faction: **{winner}**\n\n",
        "rewards_title": "💰 **Rewards (XP & Coins)**:\n",
        "profile_text": "👤 **Your Profile**:\n\n⭐ Level: **{level}**\n📈 Experience: **{xp}/500**\n💰 Coins: **{coins}**\n🛡️ Active Shield: **{shield}**",
        "leaderboard_title": "🏆 **Global Top 10 Players**:\n\n",
        "no_active_game": "⚠️ No active game found in this group.",
        "already_in_game": "⚠️ You are already in the lobby!",
        "not_in_game": "⚠️ You are not in the lobby!",
        "game_min_players": "⚠️ At least 5 players are required to start the game!",
        "help_text": (
            "ℹ️ **Darktown Mafia Bot - What can this bot do?**\n\n"
            "This bot is designed to play asynchronous **Mafia** games in Telegram groups. All controls are available in chat and via the **Mini App** interface.\n\n"
            "**Key Features**:\n"
            "1. 🎭 **8 Unique Roles**: Mafia, Don, Detective, Doctor, Bodyguard, Courtesan, Maniac, and Civilian.\n"
            "2. 📱 **Telegram Mini App**: Profile dashboard, gameplay statistics, shop (role boosters, XP shields), global leaderboard, and live game arena!\n"
            "3. 🔫 **Detective Choice**: The Detective can choose to either check a suspect's role or shoot them at night!\n"
            "4. 💀 **Last Words (Will)**: A player killed at night writes their last words in private chat to the bot, which are read to the group in the morning.\n"
            "5. 📊 **Alive Players Grid**: The table of surviving players updates every morning.\n\n"
            "**Available Commands**:\n"
            "/profile - View your profile and statistics\n"
            "/leaderboard - Global top players\n"
            "/boost - View active boosters\n"
            "/rules - Read game and group rules\n"
            "/friend - Official links and partners\n"
            "/newgame - Start a new game lobby in a group"
        ),
        "rules_text": (
            "📖 **Game and Group Rules**\n\n"
            "**🎮 GAME RULES**:\n"
            "1. **Goal**:\n"
            "   * **Civilians**: Find and hang all mafia members and the maniac.\n"
            "   * **Mafia**: Eliminate civilians until mafia matches civilian count.\n"
            "   * **Maniac**: Be the last surviving player in the game.\n"
            "2. **Phases**:\n"
            "   * **🌙 Night**: Active roles make their choices in PM or Mini App.\n"
            "   * **🌅 Day**: Night victims and wills are announced. Players discuss.\n"
            "   * **🗳️ Voting**: Vote to hang a suspect. The player with the most votes is hanged.\n\n"
            "**⚠️ GROUP RULES**:\n"
            "1. Be respectful. No insults or profanity are allowed.\n"
            "2. Leaving an active game (afk) is prohibited. Violators will be punished.\n"
            "3. Dead players are not allowed to chat in the group during the active game."
        ),
        "friend_text": (
            "🤝 **Our channels and partners**\n\n"
            "Join our official group and friendly channels using the buttons below:"
        ),
        "group_help_text": (
            "ℹ️ **Darktown Mafia Bot - Group Help**\n\n"
            "Use the following commands in the group chat:\n\n"
            "/newgame - Create a new game lobby (stays open for 2 minutes, minimum 5 players needed).\n"
            "/start or /startgame - Start the game immediately with joined players (creator or admin only).\n"
            "/leave - Leave the lobby or active game.\n"
            "/rules - Check game and group rules\n"
            "/friend - List of friendly channels and resources"
        ),
        "role_assigned_private": "🎭 **Your Role**: {role_emoji} **{role}**\n\n{details}\n\nThe game will start soon. Get ready for night actions!",
        "game_joined_success": "✅ You have successfully joined the game!",
        "game_left_success": "🚪 You have left the game.",
        "cannot_leave_active": "⚠️ You cannot leave the game when it is in progress!",
        "referral_welcome": "🎁 **You joined via invitation!** You and your friend received **+50 coins** bonus!",
        "referral_notification": "👥 **Your friend joined via your link!** You received **+50 coins** bonus!"
    },
    "kz": {
        "start_private": "👋 **Сәлеметсіз бе, {name}!**\n\nDarktown Mafia ботына қош келдіңіз!\n\nБұл бот топтарда қызықты асинхронды **Мафия** ойындарын ұйымдастыруға арналған. Ойынды бастау үшін оны топқа қосып, `/newgame` командасын жіберіңіз.",
        "lang_changed": "✅ Бот тілі **Қазақ тіліне** өзгертілді!",
        "lang_select": "🌐 Бот тілін таңдаңыз:",
        "only_admin_lang": "⚠️ Тек топ әкімшілері ғана топ тілін өзгерте алады!",
        "new_game_created": "🎮 **Жаңа ойын лоббиі жасалды!**\n\nҚатысу үшін төмендегі батырманы басыңыз.\n⏳ Ойынның басталуына **2 минут** қалды (кемінде 5 адам қажет).",
        "lobby_join": "🙋‍♂️ Қосылу",
        "lobby_leave": "🚪 Шығу",
        "lobby_start": "🚀 Бастау",
        "joined_lobby": "✅ Сіз лоббиге қосылдыңыз!",
        "left_lobby": "🚪 Сіз лоббиден шықтыңыз!",
        "game_started_announcement": "🎭 **Рөлдер бөлінді!** Әр ойыншыға өз рөлі жеке чатта жіберілді.\n\n🌙 **Қараңғы түсіп келеді... Ойын басталды!**\nБарлық ойыншылар түнгі әрекеттерін жеке чатта немесе Mini App-та жасайды.",
        "night_fell": "🌙 **Қалаға түн батуда... Барлық бейбіт тұрғындар ұйқыға кетті. Мафия және белсенді рөлдер оянуда.**\n\n_(Әрекеттерді орындау үшін жеке чатқа өтіңіз немесе Mini App-ты ашыңыз!)_",
        "day_broke": "🌅 **Таң атты! Darktown қаласы оянды...**\n\n",
        "day_discussion": "💬 **Қала оянды! Күн басталды. Талқылау алаңы ашық.**\nКүдіктілерді анықтап, мафияны табыңыз.\n⏳ Дауыс беру кезеңінің басталуына **60 секунд** қалды.",
        "voting_started": "🗳️ **Дауыс беру басталды!**\nАлаңда кімді асуды қалайсыз? Төмендегі батырмалардың бірін таңдаңыз.\nДауыс беру 45 секундқа созылады.",
        "voting_results": "🗳️ **Дауыс беру нәтижелері**:\n",
        "game_ended": "🎉 **Ойын аяқталды!**\n\nЖеңімпаз тарап: **{winner}**\n\n",
        "rewards_title": "💰 **Марапаттар (XP және монеталар)**:\n",
        "profile_text": "👤 **Сіздің профиліңіз**:\n\n⭐ Деңгей: **{level}**\n📈 Тәжірибе: **{xp}/500**\n💰 Монеталар: **{coins}**\n🛡️ Белсенді қалқан: **{shield}**",
        "leaderboard_title": "🏆 **Жаһандық үздік 10 ойыншы**:\n\n",
        "no_active_game": "⚠️ Бұл топта белсенді ойын табылмады.",
        "already_in_game": "⚠️ Сіз лоббидесіз!",
        "not_in_game": "⚠️ Сіз лоббиде емессіз!",
        "game_min_players": "⚠️ Ойынды бастау үшін кемінде 5 ойыншы қажет!",
        "help_text": (
            "ℹ️ **Darktown Mafia Bot - Бұл бот не істей алады?**\n\n"
            "Бұл бот Telegram топтарында асинхронды **Мафия** ойындарын ойнауға арналған. Барлық басқару чатта және арнайы **Mini App** интерфейсінде жүзеге асырылады.\n\n"
            "**Негізгі мүмкіндіктер**:\n"
            "1. 🎭 **8 ерекше рөл**: Мафия, Дон, Комиссар, Дәрігер, Оққағар, Куртизанка, Маньяк және Бейбіт тұрғын.\n"
            "2. 📱 **Telegram Mini App**: Профиль, толық статистика, дүкен (рөл бустерлері, қалқандар), көшбасшылар тақтасы және ойын алаңы!\n"
            "3. 🔫 **Комиссар таңдауы**: Комиссар түнде күдіктіні тексеріп қана қоймай, оны атып та тастай алады!\n"
            "4. 💀 **Соңғы сөз (Өсиет)**: Түнде өлтірілген ойыншы өз өсиетін жеке чатта ботқа жазады, ал таңертең бот оны топқа жібереді.\n"
            "5. 📊 **Тірілер кестесі**: Тірі қалған ойыншылар тізімі әр таң сайын жаңартылып отырады.\n\n"
            "**Қолжетімді командалар**:\n"
            "/profile - Профильді көру\n"
            "/leaderboard - Үздік ойыншылар кестесі\n"
            "/boost - Белсенді бустерлерді көру\n"
            "/rules - Ойын және топ ережелері\n"
            "/friend - Біздің арналар мен серіктестер\n"
            "/newgame - Топта жаңа лобби құру"
        ),
        "rules_text": (
            "📖 **Ойын және топ ережелері**\n\n"
            "**🎮 ОЙЫН ЕРЕЖЕЛЕРІ**:\n"
            "1. **Мақсат**:\n"
            "   * **Бейбіт тұрғындар**: Барлық мафия мен маньякты тауып асу.\n"
            "   * **Мафия**: Бейбіт тұрғындарды жойып, олармен саны жағынан теңесу.\n"
            "   * **Маньяк**: Ойында соңғы тірі қалған адам болу.\n"
            "2. **Кезеңдер**:\n"
            "   * **🌙 Түн**: Белсенді рөлдер өз әрекеттерін боттың жеке чатында немесе Mini App-та жасайды.\n"
            "   * **🌅 Күн**: Түнгі құрбандар мен өсиеттер жарияланады. Ойыншылар талқылайды.\n"
            "   * **🗳️ Дауыс беру**: Күдіктіні асу үшін дауыс беру. Ең көп дауыс жинаған ойыншы асылады.\n\n"
            "**⚠️ ТОП ЕРЕЖЕЛЕРІ**:\n"
            "1. Әдепті болыңыз. Балағаттау мен балағат сөздерге қатаң тыйым салынады.\n"
            "2. Белсенді ойыннан шығуға (afk) тыйым салынады. Ереже бұзушылар жазаланады.\n"
            "3. Өлген ойыншыларға ойын кезінде топта сөйлесуге тыйым салынады."
        ),
        "friend_text": (
            "🤝 **Біздің арналар мен серіктестер**\n\n"
            "Төмендегі батырмалар арқылы ресми тобымыз бен арналарымызға қосылыңыз:"
        ),
        "group_help_text": (
            "ℹ️ **Darktown Mafia Bot - Топтағы көмек**\n\n"
            "Топта ойнау үшін келесі командаларды қолданыңыз:\n\n"
            "/newgame - Жаңа ойын лоббиін құру (2 минут ашық болады, кемінде 5 ойыншы қажет).\n"
            "/start немесе /startgame - Жиналған ойыншылармен ойынды дереу бастау (тек лобби жасаушы немесе әкімші үшін).\n"
            "/leave - Лоббиден немесе белсенді ойыннан шығу.\n"
            "/rules - Ойын және чат ережелерімен танысу\n"
            "/friend - Достық арналар мен ресурстар тізімі"
        ),
        "role_assigned_private": "🎭 **Сіздің рөліңіз**: {role_emoji} **{role}**\n\n{details}\n\nОйын жақын арада басталады. Түнгі әрекеттерге дайын болыңыз!",
        "game_joined_success": "✅ Сіз ойынға сәтті қосылдыңыз!",
        "game_left_success": "🚪 Сіз ойыннан шықтыңыз.",
        "cannot_leave_active": "⚠️ Белсенді кезеңде ойыннан шыға алмайсыз!",
        "referral_welcome": "🎁 **Сіз шақыру арқылы қосылдыңыз!** Сізге және досыңызға **+50 монета** бонус берілді!",
        "referral_notification": "👥 **Досыңыз сіздің сілтемеңізбен қосылды!** Сіз **+50 монета** бонус алдыңыз!"
    }
}

def get_text(lang: str, key: str, **kwargs) -> str:
    lang_dict = TEXTS.get(lang, TEXTS["uz"])
    template = lang_dict.get(key, TEXTS["uz"].get(key, key))
    try:
        return template.format(**kwargs)
    except Exception:
        return template
