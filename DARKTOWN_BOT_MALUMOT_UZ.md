# 🏙 DarkTown Mafia Bot & WebApp — To'liq Loyiha Ma'lumotnomasi (Taqdimot)

Ushbu hujjat **DarkTown Mafia Bot & Mini App** loyihasini sotib olmoqchi bo'lgan xaridorlar, investorlar yoki dasturchilar uchun loyihaning barcha imkoniyatlari, texnologik arxitekturasi, faol va vaqtincha o'chirilgan modullari haqida to'liq texnik va tijoriy ma'lumot beradi.

---

## 📌 1. Loyihaning Qisqacha Tavsifi

**DarkTown** — bu Telegram platformasi uchun maxsus ishlab chiqilgan, zamonaviy **Telegram Mini App (WebApp)** va **klassik Bot** imkoniyatlarini birlashtirgan yangi avlod onlayn Mafia o'yini ekotizimidir.

Foydalanuvchilar o'yinni ham Telegram guruhlarida, ham Mini App orqali real vaqtda (real-time matchmaking) butun dunyo o'yinchilari yoki do'stlari bilan o'ynashlari mumkin.

---

## 🚀 2. Texnologiyalar Steki (Tech Stack)

- **Backend:** Python 3.11 - 3.13, iogram 3.x (Asinxron Telegram Bot freymvorki), iohttp (Asinxron Web Server va REST API).
- **Frontend (Mini App):** HTML5, Vanilla JavaScript (ES6+), CSS3 (Cyberpunk / Modern Neon UI), Telegram WebApp SDK.
- **Ma'lumotlar Bazasi:** Asinxron iosqlite (SQLite3) / PostgreSQL qo'llab-quvvatlaydi.
- **Avto-zaxiralash (Backup):** Har bir o'zgarish va davriy zaxira avtomatik ravishda Telegram shaxsiy kanal/arxiviga .db fayl ko'rinishida yuklanadi va pin qilinadi (Ma'lumotlar hech qachon yo'qolmaydi).
- **Deployment & Hosting:** Render.com, VPS (Ubuntu/Debian), Railway, Heroku yoki Docker orqali 24/7 rejimida o'z-o'zini uyg'otib turuvchi (Self-Ping Keep-Alive) arxitektura.

---

## 🟢 3. Hozirda TO'LIQ FAOL Bo'lgan Funksiyalar (ON)

### 🎮 A. O'yin Mexanikasi va Matchmaking
1. **CS2-uslubidagi Avto-Matching (Tezkor Qidiruv):** O'yinchilar bitta tugma orqali ochiq lobbylarga avtomatik tarzda ulanadi.
2. **Yopiq (Private) Xonalar:** Do'stlar uchun maxsus PIN-kod bilan himoyalangan xonalar yaratish imkoniyati.
3. **Sozlanuvchi Vaqtlar:** Xona yaratuvchisi kunduzgi muhokama va tungi fazalar soniyasini mustaqil belgilay oladi.
4. **Real Vaqtli Faza O'tishlari:** Kecha / Kunduz / Ovoz berish / Qatl animatsiyalari va ovoz effektlari.
5. **O'yin Ichidagi Uch Bosqichli Chat:**
   - ☀️ *Kunduzgi Chat:* Barcha tirik o'yinchilar muhokamasi va ovoz berish.
   - 🔴 *Mafiya Yashirin Chati:* Kechasi mafiozilarning maxfiy rejalashtirish chati.
   - 👻 *Arvoxlar (Ghost) Chati:* O'yindan chiqqanlar o'yinni kuzatib, o'zaro suhbatlashishi uchun maxsus chat.

### 🎭 B. O'yin Rollari va Qobiliyatlari
- **🤵 Don (Mafiya Bossi):** Mafiya guruhini boshqaradi, tunda qurbonni belgilaydi va komissarni tekshiradi.
- **🔫 Mafiya:** Tunda don bilan birgalikda tinch aholini yo'q qiladi.
- **🕵️‍♂️ Komissar (Sherif):** Har kecha bitta o'yinchining rolini (Mafiya yoki Tinch) fosh etadi.
- **💉 Shifokor (Doktor):** Har kecha bir o'yinchini mafiya hujumidan davolab saqlab qoladi.
- **💋 Jazoirchi (Jariya / Escort):** Tunda o'yinchini band qilib, uning tungi qobiliyatini bloklaydi.
- **🤪 Telba (Maniak):** O'z manfaati uchun o'ynaydi va hamma uchun xavf tug'diradi.
- **👤 Tinch Aholi:** Kunduzgi tahlil va ovoz berish orqali shaharni tozalaydi.

### 🛒 C. Do'kon, Iqtisodiyot va Maxsus Busterlar
1. **🪙 Tangalar (Coins) Tizimi:** O'yinlardagi g'alaba, ishtirok va referrallar uchun beriladi.
2. **🛡️ XP Qalqoni (Shield):** Tunda o'ldirilganda tajriba (XP) va tangalarning yo'qolishidan 1 marta himoya qiladi.
3. **⚡ Faol Rol Busteri:** O'yinda oddiy fuqaro bo'lib qolmaslik va faol rol (Mafiya, Komissar, Shifokor va h.k.) olishni 100% kafolatlaydi.
4. **🪪 Soxta Hujjat (Fake ID):** Mafiya bo'lganingizda Komissar tekshirsa, sizni «Tinch aholi» qilib ko'rsatuvchi noyob buster!
5. **⭐️ To'lov Tizimi:** Telegram Stars orqali tangalar va VIP xarid qilish imkoniyati.

### 🎁 D. Rivojlanish, Bonuslar va Foydalanuvchi Profili
- **🔥 7-Kunlik Bonus Streak:** Har kuni kirgan foydalanuvchiga oshib boruvchi tangalar va sovg'alar.
- **📋 Kunlik Vazifalar (Quests):** O'yin ichidagi topshiriqlar orqali qo'shimcha daromad.
- **👥 Referral Tizimi:** Har bir taklif qilingan faol do'st uchun +50 tanga mukofot (Antifraud tizimi bilan).
- **🏆 Global Reyting (Leaderboard):** G'alabalar, o'yinlar soni, Winrate va daraja bo'yicha global TOP.
- **📊 Mafiya Balans Kalkulyatori:** Mini App ichida istalgan o'yinchilar soni uchun rollar taqsimotini hisoblovchi interaktiv kalkulyator.
- **👑 VIP Profil:** Maxsus fon rasmlari va VIP daraja imtiyozlari.

### 🌍 E. To'liq 4 Tilli Lokalizatsiya (Multi-Language)
- 🇺🇿 **O'zbekcha (UZ)**
- 🇷🇺 **Русский (RU)**
- 🇬🇧 **English (EN)**
- 🇰🇿 **Қазақша (KZ)**
*(Til o'zgarganda sahifani qayta yuklamasdan barcha tugmalar, modallar, xonalar va chatlar bir zumda tarjima bo'ladi).*

### 👑 F. Qudratli Admin Panel
- **Statistika:** Jami o'yinchilar, bugungi faollar, o'tkazilgan o'yinlar, aylanmadagi tangalar.
- **Foydalanuvchi Boshqaruvi:** ID orqali qidirish, profilini ko'rish, Bloklash (Ban) / Blokdan chiqarish (Unban).
- **Balans Boshqaruvi:** Istalgan foydalanuvchiga tanga yoki XP qo'shish/ayirish.
- **📢 Broadcast:** Barcha bot foydalanuvchilariga bir zumda rasm/matnli ommaviy xabar yuborish.
- **Texnik Ishlar Rejimi (Maintenance Mode):** Bir tugma bilan botni yangilash rejimiga o'tkazish.

---

## 🟡 4. Vaqtincha O'chirilgan (Kengaytirish uchun TAYYOR) Modullar (OFF)

Quyidagi funksiyalar kod bazasida to'liq yozilgan, arxitekturasi tayyor, lekin loyihaning 1-bosqichi (MVP) yengil va tez ishlashi uchun vaqtincha config.py sozlamasi orqali o'chirib turilibdi. Yangi egasi istalgan vaqtda ularni bitta o'zgaruvchi bilan faollashtirishi mumkin:

1. **🛡️ Klanlar (Clans) Tizimi (OFF):**
   - Klan yaratish, a'zolar qabul qilish, klan xazinasi, klanlar reytingi va klanlararo o'yinlar.
2. **📜 Mavsumiy Battle Pass (OFF):**
   - 30 kunlik mavsumiy darajalar, bepul va Premium Battle Pass yo'lakchalari, maxsus rollar va unvonlar.
3. **🏆 Turnirlar Tizimi (OFF):**
   - Admin tomonidan Mini App orqali maxsus turnir e'lon qilish, mukofot jamg'armasi belgilash va g'oliblarga avtomatik sovg'a tarqatish.
4. **🎰 Kazino & Mini-O'yinlar (OFF):**
   - Tangalar yordamida o'ynaladigan omadli g'ildirak va ruletka tizimi.

---

## 💼 5. Loyihaning Tijoriy Afzalliklari (Monetizatsiya)

1. **Telegram Stars & Donat:** Foydalanuvchilar busterlar, VIP status va tangalarni to'g'ridan-to'g'ri Telegram ichida xarid qiladi.
2. **Majburiy Kanal Obunasi (OP):** Bot va Mini Appga kirish uchun homiy kanallarga obuna bo'lish talabi (Katta reklama daromadi).
3. **Reklama va Broadcast:** O'n minglab faol o'yinchilarga reklama xabarlarini sotish imkoniyati.
4. **Virusli Tarqalish (Referral):** Foydalanuvchilar bonus tanga olish uchun o'z do'stlari va guruhlariga botni o'zlari tarqatadi.

---

## 📦 6. Sotuv Paketiga Nimalar Kiradi?

1. Loyihaning **to'liq va toza ochiq kodi (Full Source Code)** — Backend va Frontend.
2. Tayyor SQLite ma'lumotlar bazasi va avtomatik zaxiralash tizimi.
3. Render / VPS / Serverga 5 daqiqada o'rnatish bo'yicha to'liq qo'llanma.
4. Loyihani topshirish va dastlabki sozlash bo'yicha texnik ko'mak.

---
*DarkTown Mafia — Telegram o'yin industriyasidagi tayyor va yuqori daromadli biznes yechim!* 🚀
