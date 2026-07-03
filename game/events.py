import random

EVENTS = [
    {
        "key": "fog",
        "name": "🌫️ Qalin Tuman",
        "description": "Darktown ustiga quyuq tuman tushdi. Bugun tunda Komissar tekshiruv o'tkaza olmaydi."
    },
    {
        "key": "epidemic",
        "name": "💉 Tibbiy Epidemiya",
        "description": "Shaharda epidemiya tarqaldi. Shifokor tunda bir kishini ketma-ket ikki marta davolash huquqiga ega bo'ladi."
    },
    {
        "key": "fair",
        "name": "🎪 Shahar Yarmarkasi",
        "description": "Yarmarka munosabati bilan barcha o'yinchilar o'yin yakunida qo'shimcha +30 tanga oladilar."
    },
    {
        "key": "curfew",
        "name": "🚨 Komendantlik Soati",
        "description": "Komendantlik soati o'rnatildi. Bugun tunda Telba (Maniac) qotillik qila olmaydi."
    },
    {
        "key": "anarchy",
        "name": "🔥 Anarxiya",
        "description": "Qonunlar ishlamayapti! Kunduzgi ovoz berishda agar ovozlar teng bo'lib qolsa, nomzodlardan biri tasodifiy osiladi."
    }
]

def get_random_event():
    # 30% chance for an event to happen each day
    if random.random() < 0.4:
        return random.choice(EVENTS)
    return None
