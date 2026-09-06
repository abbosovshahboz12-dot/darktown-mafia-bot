# 👑 DarkTown Mafia Bot — Admin Qo'llanmasi va Buyruqlar

Ushbu qo'llanma bot administratori uchun barcha mavjud buyruqlar, panellar va funksiyalarni o'z ichiga oladi.

---

## ⚡ Asosiy Buyruqlar (Telegram Bot)

| Buyruq | Izoh | Misol |
|---|---|---|
| /admin | Admin boshqaruv panelini ochish (barcha tugmalar bilan) | /admin |
| /export yoki /excel | Barcha o'yinchilar ro'yxatini Excel (.csv) formatida yuklab olish | /export |
| /adminhelp | Admin buyruqlari spravkasini xabar shaklida ko'rish | /adminhelp |
| /broadcast <matn> | Barcha ro'yxatdan o'tgan foydalanuvchilarga xabar yuborish | /broadcast Bugun soat 20:00 da turnir! |
| /user <user_id> | Ma'lum bir foydalanuvchi ma'lumotlarini (balans, daraja, o'yinlar) tekshirish | /user 12345678 |
| /givecoins <user_id> <miqdor> | Foydalanuvchiga Dark Coins (tanga) berish | /givecoins 12345678 1000 |
| /givexp <user_id> <miqdor> | Foydalanuvchiga tajriba (XP) berish | /givexp 12345678 500 |
| /ban <user_id> | Qoidabuzar o'yinchini botda butunlay bloklash | /ban 12345678 |
| /unban <user_id> | Bloklangan o'yinchini blokdan chiqarish | /unban 12345678 |
| /activegames | Guruhlardagi ayni paytda o'ynalayotgan faol o'yinlarni ko'rish | /activegames |

---

## 📱 Admin Panel Bo'limlari (/admin)

Botdagi /admin panelida quyidagi qulay tugmalar mavjud:

1. **📊 Batafsil Statistika:**
   - Jami o'yinchilar soni
   - Bugungi faol o'yinchilar (DAU)
   - Bugun o'ynalgan o'yinlar soni
   - Jami o'ynalgan barcha o'yinlar
   - Hozirgi guruhlardagi faol jonli o'yinlar
   - Aylanmadagi jami tangalar
   - Bloklangan foydalanuvchilar soni

2. **📥 O'yinchilar Ro'yxati (Excel):**
   - Barcha o'yinchilar bazasini Microsoft Excel va Google Sheets uchun moslashtirilgan UTF-8 formatida fayl qilib yuboradi.

3. **🎮 Faol O'yinlar:**
   - Guruhlardagi hozirgi jonli partiyalarni ko'rsatadi.

4. **💰 O'zimga +1000 🪙 va ⚡ O'zimga +500 XP:**
   - Bitta bosishda admin hisobini to'ldirish tugmalari.

5. **📖 Buyruqlar Qo'llanmasi:**
   - Barcha buyruqlarni bot ichida eslatib turuvchi tezkor yordamchi.

---

## 🔒 Xavfsizlik

- Barcha admin buyruqlari faqat .env dagi ADMIN_ID ga ega bo'lgan Telegram akkaunt uchun ishlaydi.
- Begona foydalanuvchilar ushbu buyruqlarni ishlata olmaydi.
