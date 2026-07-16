import aiosqlite
import os
import math
from datetime import datetime

from config import DATABASE_PATH
DB_PATH = DATABASE_PATH

async def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA synchronous=NORMAL")
        # Users table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                coins INTEGER DEFAULT 100,
                shield_active INTEGER DEFAULT 0
            )
        """)
        
        # Stats table (wins and plays by role)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS stats (
                user_id INTEGER,
                role TEXT,
                games_played INTEGER DEFAULT 0,
                games_won INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, role)
            )
        """)
        
        # Inventory table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                user_id INTEGER,
                item_key TEXT,
                quantity INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, item_key)
            )
        """)
        
        # Group Settings table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS group_settings (
                chat_id INTEGER PRIMARY KEY,
                language TEXT DEFAULT 'uz'
            )
        """)
        
        # Match Rooms table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS rooms (
                room_id TEXT PRIMARY KEY,
                owner_id INTEGER,
                status TEXT DEFAULT 'lobby',
                is_private INTEGER DEFAULT 0,
                pin_code TEXT,
                day_limit INTEGER DEFAULT 60,
                night_limit INTEGER DEFAULT 60,
                created_at TEXT
            )
        """)
        
        # Room Players table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS room_players (
                room_id TEXT,
                user_id INTEGER,
                role TEXT DEFAULT 'Civilian',
                is_alive INTEGER DEFAULT 1,
                afk_streak INTEGER DEFAULT 0,
                PRIMARY KEY (room_id, user_id)
            )
        """)
        
        # Parties table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS parties (
                party_id TEXT,
                leader_id INTEGER,
                member_id INTEGER,
                PRIMARY KEY (party_id, member_id)
            )
        """)
        
        # Game History table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS game_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                room_id TEXT,
                role TEXT,
                is_winner INTEGER,
                winning_faction TEXT,
                played_at TEXT
            )
        """)

        # User Achievements table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_achievements (
                user_id INTEGER,
                achievement_key TEXT,
                unlocked_at TEXT,
                PRIMARY KEY (user_id, achievement_key)
            )
        """)
        
        # Migrations for existing database
        try:
            await db.execute("ALTER TABLE users ADD COLUMN language TEXT DEFAULT 'uz'")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE users ADD COLUMN referred_by INTEGER")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE users ADD COLUMN last_daily_claim TEXT")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE users ADD COLUMN banned INTEGER DEFAULT 0")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE users ADD COLUMN daily_games_played INTEGER DEFAULT 0")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE users ADD COLUMN daily_mafia_killed INTEGER DEFAULT 0")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE users ADD COLUMN last_quest_reset TEXT")
        except Exception:
            pass
            
        await db.commit()

async def get_user(user_id: int, username: str = None, first_name: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                # Update username/first_name if they changed
                if username or first_name:
                    await db.execute(
                        "UPDATE users SET username = ?, first_name = ? WHERE user_id = ?",
                        (username or row['username'], first_name or row['first_name'], user_id)
                    )
                    await db.commit()
                # Fetch updated
                async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor2:
                    return dict(await cursor2.fetchone())
            
            # Register new user
            await db.execute(
                "INSERT INTO users (user_id, username, first_name, xp, level, coins) VALUES (?, ?, ?, 0, 1, 100)",
                (user_id, username or f"User{user_id}", first_name or "Mafiozi")
            )
            await db.commit()
            
            async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor2:
                return dict(await cursor2.fetchone())

async def add_xp_and_coins(user_id: int, xp_amount: int, coins_amount: int):
    # Sanitize inputs to prevent overflow/unreasonable values
    if xp_amount > 1_000_000:
        xp_amount = 1_000_000
    if xp_amount < 0:
        xp_amount = 0
    if coins_amount > 1_000_000:
        coins_amount = 1_000_000
    if coins_amount < 0:
        coins_amount = 0
        
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT xp, level, coins FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return
            
            current_xp = row['xp']
            current_level = row['level']
            new_coins = row['coins'] + coins_amount
            
            # Calculate absolute total XP
            absolute_xp = 250 * current_level * (current_level - 1) + current_xp + xp_amount
            
            # Calculate new level mathematically using closed-form quadratic formula
            new_level = int(0.5 + math.sqrt(0.25 + absolute_xp / 250.0))
            if new_level < 1:
                new_level = 1
            if new_level > 1000: # Limit max level to 1000
                new_level = 1000
                
            # Calculate remaining XP at this new level
            xp_used_for_level = 250 * new_level * (new_level - 1)
            new_xp = absolute_xp - xp_used_for_level
            if new_xp < 0:
                new_xp = 0
                
            leveled_up = new_level > current_level
            
            await db.execute(
                "UPDATE users SET xp = ?, level = ?, coins = ? WHERE user_id = ?",
                (new_xp, new_level, new_coins, user_id)
            )
            await db.commit()

            if new_coins >= 500:
                async with db.execute("SELECT 1 FROM user_achievements WHERE user_id = ? AND achievement_key = 'rich_mafia'", (user_id,)) as cursor:
                    if not await cursor.fetchone():
                        unlocked_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        await db.execute(
                            "INSERT INTO user_achievements (user_id, achievement_key, unlocked_at) VALUES (?, 'rich_mafia', ?)",
                            (user_id, unlocked_at)
                        )
                        await db.execute("UPDATE users SET coins = coins + 200 WHERE user_id = ?", (user_id,))
                        await db.commit()
            
            return leveled_up, new_level

async def get_user_stats(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT role, games_played, games_won FROM stats WHERE user_id = ?", (user_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def update_stats(user_id: int, role: str, won: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT games_played, games_won FROM stats WHERE user_id = ? AND role = ?",
            (user_id, role)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                played = row[0] + 1
                won_count = row[1] + (1 if won else 0)
                await db.execute(
                    "UPDATE stats SET games_played = ?, games_won = ? WHERE user_id = ? AND role = ?",
                    (played, won_count, user_id, role)
                )
            else:
                await db.execute(
                    "INSERT INTO stats (user_id, role, games_played, games_won) VALUES (?, ?, 1, ?)",
                    (user_id, role, 1 if won else 0)
                )
        await db.commit()

async def get_leaderboard(limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT user_id, username, first_name, level, xp, coins FROM users ORDER BY level DESC, xp DESC LIMIT ?",
            (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_inventory(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT item_key, quantity FROM inventory WHERE user_id = ?", (user_id,)) as cursor:
            rows = await cursor.fetchall()
            return {row['item_key']: row['quantity'] for row in rows}

async def buy_item(user_id: int, item_key: str, cost: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT coins FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if not row or row['coins'] < cost:
                return False, "Yetarli tanga yo'q!"
            
            # Deduct coins
            await db.execute("UPDATE users SET coins = coins - ? WHERE user_id = ?", (cost, user_id))
            
            # Add to inventory
            async with db.execute(
                "SELECT quantity FROM inventory WHERE user_id = ? AND item_key = ?",
                (user_id, item_key)
            ) as cursor2:
                inv_row = await cursor2.fetchone()
                if inv_row:
                    await db.execute(
                        "UPDATE inventory SET quantity = quantity + 1 WHERE user_id = ? AND item_key = ?",
                        (user_id, item_key)
                    )
                else:
                    await db.execute(
                        "INSERT INTO inventory (user_id, item_key, quantity) VALUES (?, ?, 1)",
                        (user_id, item_key)
                    )
            await db.commit()
            return True, "Muvaffaqiyatli sotib olindi!"

async def use_item(user_id: int, item_key: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT quantity FROM inventory WHERE user_id = ? AND item_key = ?",
            (user_id, item_key)
        ) as cursor:
            row = await cursor.fetchone()
            if not row or row['quantity'] <= 0:
                return False
            
            await db.execute(
                "UPDATE inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_key = ?",
                (user_id, item_key)
            )
            await db.commit()
            return True

async def set_shield(user_id: int, active: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET shield_active = ? WHERE user_id = ?", (1 if active else 0, user_id))
        await db.commit()

async def get_global_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            total_users = (await cursor.fetchone())[0]
        async with db.execute("SELECT SUM(games_played) FROM stats") as cursor:
            row = await cursor.fetchone()
            total_plays = row[0] if row[0] is not None else 0
        return {
            "total_users": total_users,
            "total_plays": total_plays
        }

async def set_user_language(user_id: int, lang: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET language = ? WHERE user_id = ?", (lang, user_id))
        await db.commit()

async def get_user_language(user_id: int) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT language FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row['language'] if row and row['language'] else 'uz'

async def set_group_language(chat_id: int, lang: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO group_settings (chat_id, language) VALUES (?, ?) "
            "ON CONFLICT(chat_id) DO UPDATE SET language = excluded.language",
            (chat_id, lang)
        )
        await db.commit()

async def get_group_language(chat_id: int) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT language FROM group_settings WHERE chat_id = ?", (chat_id,)) as cursor:
            row = await cursor.fetchone()
            return row['language'] if row and row['language'] else 'uz'

async def get_chat_language(chat_id: int) -> str:
    if chat_id < 0:
        return await get_group_language(chat_id)
    else:
        return await get_user_language(chat_id)

async def claim_daily_reward(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT coins, last_daily_claim FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return False, 0, "Foydalanuvchi topilmadi."
            
            now = datetime.now()
            last_claim_str = row['last_daily_claim']
            if last_claim_str:
                try:
                    last_claim = datetime.fromisoformat(last_claim_str)
                    delta = now - last_claim
                    if delta.total_seconds() < 86400:
                        seconds_left = int(86400 - delta.total_seconds())
                        hours = seconds_left // 3600
                        minutes = (seconds_left % 3600) // 60
                        return False, 0, f"keyingi_bonus_kutish_{hours}_{minutes}"
                except Exception:
                    pass
            
            bonus_coins = 50
            await db.execute(
                "UPDATE users SET coins = coins + ?, last_daily_claim = ? WHERE user_id = ?",
                (bonus_coins, now.isoformat(), user_id)
            )
            await db.commit()
            return True, bonus_coins, None

async def add_referral(invitee_id: int, inviter_id: int) -> bool:
    if invitee_id == inviter_id:
        return False
        
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT referred_by FROM users WHERE user_id = ?", (invitee_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                await db.execute(
                    "INSERT INTO users (user_id, username, first_name, xp, level, coins, referred_by) "
                    "VALUES (?, ?, ?, 0, 1, 150, ?)",
                    (invitee_id, f"User{invitee_id}", "Mafiozi", inviter_id)
                )
                await db.execute("UPDATE users SET coins = coins + 50 WHERE user_id = ?", (inviter_id,))
                await db.commit()
                return True
            
            if row['referred_by'] is None:
                await db.execute("UPDATE users SET referred_by = ? WHERE user_id = ?", (inviter_id, invitee_id))
                await db.execute("UPDATE users SET coins = coins + 50 WHERE user_id = ?", (invitee_id,))
                await db.execute("UPDATE users SET coins = coins + 50 WHERE user_id = ?", (inviter_id,))
                await db.commit()
                return True
                
            return False

# Room and Party Tizimi funksiyalari
async def create_room(room_id: str, owner_id: int, is_private: int, pin_code: str, day_limit: int, night_limit: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO rooms (room_id, owner_id, status, is_private, pin_code, day_limit, night_limit, created_at) "
                "VALUES (?, ?, 'lobby', ?, ?, ?, ?, ?)",
                (room_id, owner_id, is_private, pin_code, day_limit, night_limit, datetime.now().isoformat())
            )
            # Add owner to the room players
            await db.execute(
                "INSERT INTO room_players (room_id, user_id, role, is_alive, afk_streak) VALUES (?, ?, 'Civilian', 1, 0)",
                (room_id, owner_id)
            )
            await db.commit()
            return True
        except Exception:
            return False

async def get_active_room(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        # Get active room where player is currently in (status != 'finished')
        query = """
            SELECT r.* FROM rooms r
            JOIN room_players rp ON r.room_id = rp.room_id
            WHERE rp.user_id = ? AND r.status != 'finished'
        """
        async with db.execute(query, (user_id,)) as cursor:
            return await cursor.fetchone()

async def get_room_players(room_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT rp.*, u.username, u.first_name, u.level FROM room_players rp
            JOIN users u ON rp.user_id = u.user_id
            WHERE rp.room_id = ?
        """
        async with db.execute(query, (room_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def join_room(room_id: str, user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            # Check if already in the room
            async with db.execute("SELECT 1 FROM room_players WHERE room_id = ? AND user_id = ?", (room_id, user_id)) as cursor:
                if await cursor.fetchone():
                    return True
            
            # Join player
            await db.execute(
                "INSERT INTO room_players (room_id, user_id, role, is_alive, afk_streak) VALUES (?, ?, 'Civilian', 1, 0)",
                (room_id, user_id)
            )
            await db.commit()
            return True
        except Exception:
            return False

async def leave_room(room_id: str, user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute("DELETE FROM room_players WHERE room_id = ? AND user_id = ?", (room_id, user_id))
            
            # If room has no players, or if owner leaves lobby, we close/finish it
            async with db.execute("SELECT COUNT(*) FROM room_players WHERE room_id = ?", (room_id,)) as cursor:
                count_row = await cursor.fetchone()
                count = count_row[0] if count_row else 0
                
            async with db.execute("SELECT owner_id, status FROM rooms WHERE room_id = ?", (room_id,)) as cursor:
                room_row = await cursor.fetchone()
                
            if count == 0:
                await db.execute("UPDATE rooms SET status = 'finished' WHERE room_id = ?", (room_id,))
            elif room_row and room_row[0] == user_id and room_row[1] == 'lobby':
                # Owner left lobby, close the room
                await db.execute("UPDATE rooms SET status = 'finished' WHERE room_id = ?", (room_id,))
                await db.execute("DELETE FROM room_players WHERE room_id = ?", (room_id,))
                
            await db.commit()
            return True
        except Exception:
            return False

async def get_open_rooms():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        # Get public open lobby rooms
        query = """
            SELECT r.*, COUNT(rp.user_id) as player_count FROM rooms r
            LEFT JOIN room_players rp ON r.room_id = rp.room_id
            WHERE r.status = 'lobby' AND r.is_private = 0
            GROUP BY r.room_id
            ORDER BY r.created_at DESC
        """
        async with db.execute(query) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def start_room_game(room_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE rooms SET status = 'active' WHERE room_id = ?", (room_id,))
        await db.commit()

async def finish_room_game(room_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE rooms SET status = 'finished' WHERE room_id = ?", (room_id,))
        await db.commit()

async def update_room_player_role(room_id: str, user_id: int, role: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE room_players SET role = ? WHERE room_id = ? AND user_id = ?", (role, room_id, user_id))
        await db.commit()

async def kill_room_player(room_id: str, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE room_players SET is_alive = 0 WHERE room_id = ? AND user_id = ?", (room_id, user_id))
        await db.commit()

async def increment_room_player_afk(room_id: str, user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT afk_streak FROM room_players WHERE room_id = ? AND user_id = ?", (room_id, user_id)) as cursor:
            row = await cursor.fetchone()
            if row:
                new_streak = row[0] + 1
                await db.execute("UPDATE room_players SET afk_streak = ? WHERE room_id = ? AND user_id = ?", (new_streak, room_id, user_id))
                await db.commit()
                return new_streak
            return 0

async def reset_room_player_afk(room_id: str, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE room_players SET afk_streak = 0 WHERE room_id = ? AND user_id = ?", (room_id, user_id))
        await db.commit()

# Party Management
async def create_party(party_id: str, leader_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            # Delete old parties of leader
            await db.execute("DELETE FROM parties WHERE leader_id = ?", (leader_id,))
            # Add leader as member
            await db.execute("INSERT INTO parties (party_id, leader_id, member_id) VALUES (?, ?, ?)", (party_id, leader_id, leader_id))
            await db.commit()
            return True
        except Exception:
            return False

async def add_to_party(party_id: str, leader_id: int, member_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            # Check if already in party
            async with db.execute("SELECT 1 FROM parties WHERE party_id = ? AND member_id = ?", (party_id, member_id)) as cursor:
                if await cursor.fetchone():
                    return True
            # Add member
            await db.execute("INSERT INTO parties (party_id, leader_id, member_id) VALUES (?, ?, ?)", (party_id, leader_id, member_id))
            await db.commit()
            return True
        except Exception:
            return False

async def remove_from_party(party_id: str, member_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute("DELETE FROM parties WHERE party_id = ? AND member_id = ?", (party_id, member_id))
            await db.commit()
            return True
        except Exception:
            return False

async def get_party_members(party_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT p.*, u.username, u.first_name, u.level FROM parties p
            JOIN users u ON p.member_id = u.user_id
            WHERE p.party_id = ?
        """
        async with db.execute(query, (party_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def get_user_party(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM parties WHERE member_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()

async def ban_user(user_id: int, ban: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        val = 1 if ban else 0
        await db.execute("UPDATE users SET banned = ? WHERE user_id = ?", (val, user_id))
        await db.commit()

async def is_user_banned(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT banned FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return (row[0] == 1) if row else False

async def get_all_user_ids() -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users") as cursor:
            rows = await cursor.fetchall()
            return [r[0] for r in rows]

# --- PHASE 2 DATABASE FUNCTIONS ---

async def save_game_history(user_id: int, room_id: str, role: str, is_winner: int, winning_faction: str):
    async with aiosqlite.connect(DB_PATH) as db:
        played_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await db.execute(
            "INSERT INTO game_history (user_id, room_id, role, is_winner, winning_faction, played_at) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, room_id, role, is_winner, winning_faction, played_at)
        )
        await db.commit()

async def get_game_history(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM game_history WHERE user_id = ? ORDER BY id DESC LIMIT 10", (user_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

ACHIEVEMENTS_LIST = {
    "first_win": {
        "name_uz": "Birinchi G'alaba", "name_ru": "Первая Победа",
        "desc_uz": "Mafiya o'yinida 1-marta g'alaba qozoning", "desc_ru": "Выиграйте первую игру",
        "reward": 50
    },
    "mafia_slayer": {
        "name_uz": "Mafiya Qotili", "name_ru": "Истребитель Мафии",
        "desc_uz": "O'yinchi sifatida mafiya a'zolarini o'ldiring", "desc_ru": "Убейте мафию будучи мирным",
        "reward": 100
    },
    "active_player": {
        "name_uz": "Faol O'yinchi", "name_ru": "Активный Игрок",
        "desc_uz": "Jami 10 ta o'yinda qatnashish", "desc_ru": "Сыграйте всего 10 игр",
        "reward": 150
    },
    "rich_mafia": {
        "name_uz": "Boy Mafioz", "name_ru": "Богатый Мафиози",
        "desc_uz": "Jami 500 tanga yig'ing", "desc_ru": "Соберите 500 монет",
        "reward": 200
    }
}

async def get_user_achievements(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT achievement_key, unlocked_at FROM user_achievements WHERE user_id = ?", (user_id,)) as cursor:
            rows = await cursor.fetchall()
            unlocked = {r[0]: r[1] for r in rows}
            
        result = []
        for key, info in ACHIEVEMENTS_LIST.items():
            is_unlocked = key in unlocked
            result.append({
                "key": key,
                "name_uz": info["name_uz"],
                "name_ru": info["name_ru"],
                "desc_uz": info["desc_uz"],
                "desc_ru": info["desc_ru"],
                "reward": info["reward"],
                "unlocked": is_unlocked,
                "unlocked_at": unlocked.get(key) if is_unlocked else None
            })
        return result

async def unlock_achievement(user_id: int, achievement_key: str) -> bool:
    if achievement_key not in ACHIEVEMENTS_LIST:
        return False
    async with aiosqlite.connect(DB_PATH) as db:
        # Check if already unlocked
        async with db.execute("SELECT 1 FROM user_achievements WHERE user_id = ? AND achievement_key = ?", (user_id, achievement_key)) as cursor:
            if await cursor.fetchone():
                return False
                
        # Unlock and give reward
        unlocked_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await db.execute(
            "INSERT INTO user_achievements (user_id, achievement_key, unlocked_at) VALUES (?, ?, ?)",
            (user_id, achievement_key, unlocked_at)
        )
        reward = ACHIEVEMENTS_LIST[achievement_key]["reward"]
        await db.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (reward, user_id))
        await db.commit()
        return True

async def get_daily_quests(user_id: int):
    today_str = datetime.now().strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT daily_games_played, daily_mafia_killed, last_quest_reset FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            
        if not row:
            return []
            
        games = row["daily_games_played"] or 0
        killed = row["daily_mafia_killed"] or 0
        last_reset = row["last_quest_reset"]
        
        if last_reset != today_str:
            games = 0
            killed = 0
            await db.execute(
                "UPDATE users SET daily_games_played = 0, daily_mafia_killed = 0, last_quest_reset = ? WHERE user_id = ?",
                (today_str, user_id)
            )
            await db.commit()
            
        quests = [
            {
                "id": "play_3_games",
                "name_uz": "3 ta o'yinda qatnashish",
                "name_ru": "Сыграть 3 игры",
                "progress": games,
                "target": 3,
                "reward": 30,
                "completed": games >= 3
            },
            {
                "id": "kill_1_mafia",
                "name_uz": "1 ta mafiyani yo'q qilish",
                "name_ru": "Убить 1 мафию",
                "progress": killed,
                "target": 1,
                "reward": 50,
                "completed": killed >= 1
            }
        ]
        return quests

async def increment_daily_games(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        # Make sure reset check runs first
        await get_daily_quests(user_id)
        await db.execute("UPDATE users SET daily_games_played = daily_games_played + 1 WHERE user_id = ?", (user_id,))
        await db.commit()
        
        # Check active player achievement (10 total games played)
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT COUNT(*) FROM game_history WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            cnt = row[0] if row else 0
            if cnt >= 10:
                await unlock_achievement(user_id, "active_player")

async def increment_daily_mafia_killed(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await get_daily_quests(user_id)
        await db.execute("UPDATE users SET daily_mafia_killed = daily_mafia_killed + 1 WHERE user_id = ?", (user_id,))
        await db.commit()
        await unlock_achievement(user_id, "mafia_slayer")
