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

        # Clans table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS clans (
                clan_id TEXT PRIMARY KEY,
                name TEXT UNIQUE,
                leader_id INTEGER,
                logo_url TEXT,
                total_wins INTEGER DEFAULT 0,
                total_points INTEGER DEFAULT 0,
                created_at TEXT
            )
        """)
        
        # Clan Members table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS clan_members (
                clan_id TEXT,
                user_id INTEGER PRIMARY KEY,
                role TEXT DEFAULT 'member',
                joined_at TEXT
            )
        """)
        
        # Tournaments table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tournaments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                prize_pool TEXT,
                status TEXT DEFAULT 'upcoming',
                start_time TEXT,
                winner_name TEXT
            )
        """)
        
        # Tournament Participants table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tournament_participants (
                tournament_id INTEGER,
                user_id INTEGER,
                joined_at TEXT,
                PRIMARY KEY (tournament_id, user_id)
            )
        """)
        
        # Battle Pass table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS battle_pass (
                user_id INTEGER PRIMARY KEY,
                pass_level INTEGER DEFAULT 1,
                pass_xp INTEGER DEFAULT 0,
                is_premium INTEGER DEFAULT 0
            )
        """)
        
        # Seed Tournament if empty
        async with db.execute("SELECT COUNT(*) FROM tournaments") as cursor:
            count = (await cursor.fetchone())[0]
            if count == 0:
                await db.execute(
                    "INSERT INTO tournaments (title, prize_pool, status, start_time, winner_name) "
                    "VALUES ('DarkTown Haftalik Turnir #1', '1000 Telegram Stars + 5000 Coins', 'active', 'Yakshanba 20:00', NULL)"
                )
        
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
        try:
            await db.execute("ALTER TABLE users ADD COLUMN group_invites INTEGER DEFAULT 0")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE users ADD COLUMN streak_days INTEGER DEFAULT 0")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE users ADD COLUMN last_streak_date TEXT")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE tournaments ADD COLUMN group_link TEXT")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE users ADD COLUMN tournament_points INTEGER DEFAULT 0")
        except Exception:
            pass
            
        # VIP migrations
        try:
            await db.execute("ALTER TABLE users ADD COLUMN is_vip INTEGER DEFAULT 0")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE users ADD COLUMN vip_expires_at TEXT")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE users ADD COLUMN custom_bg TEXT")
        except Exception:
            pass
            
        await db.commit()

async def get_user(user_id: int, username: str = None, first_name: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                rdict = dict(row)
                is_vip = rdict.get('is_vip', 0) or 0
                vip_expires_at = rdict.get('vip_expires_at')
                if is_vip == 1 and vip_expires_at:
                    try:
                        from datetime import datetime
                        expiry = datetime.strptime(vip_expires_at, "%Y-%m-%d %H:%M:%S")
                        if datetime.now() > expiry:
                            await db.execute("UPDATE users SET is_vip = 0 WHERE user_id = ?", (user_id,))
                            await db.commit()
                    except Exception:
                        pass
                        
                if username or first_name:
                    await db.execute(
                        "UPDATE users SET username = ?, first_name = ? WHERE user_id = ?",
                        (username or rdict.get('username'), first_name or rdict.get('first_name'), user_id)
                    )
                    await db.commit()
                async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor2:
                    row2 = await cursor2.fetchone()
                    return dict(row2) if row2 else {}
            
            await db.execute(
                "INSERT INTO users (user_id, username, first_name, xp, level, coins) VALUES (?, ?, ?, 0, 1, 100)",
                (user_id, username or f"User{user_id}", first_name or "Mafiozi")
            )
            await db.commit()
            
            async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor2:
                row2 = await cursor2.fetchone()
                return dict(row2) if row2 else {}

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
        async with db.execute("SELECT xp, level, coins, is_vip FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return
            
            is_vip = row['is_vip'] or 0
            if is_vip == 1:
                xp_amount *= 2
                
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
            
    # Check achievements outside active transaction
    if new_coins >= 500:
        await unlock_achievement(user_id, "rich_mafia")
    if new_level >= 10:
        await unlock_achievement(user_id, "lvl_10")
    if new_level >= 100:
        await unlock_achievement(user_id, "lvl_100")
            
    return leveled_up, new_level

async def get_user_stats(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT role, games_played, games_won FROM stats WHERE user_id = ?", (user_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def update_stats(user_id: int, role: str, won: bool):
    keys_to_unlock = []
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
        
        if won:
            # Get stats for this user
            async with db.execute("SELECT role, games_won FROM stats WHERE user_id = ?", (user_id,)) as cursor:
                rows = await cursor.fetchall()
                stats_dict = {r[0]: r[1] for r in rows}
                
            mafia_wins = stats_dict.get('mafia', 0) + stats_dict.get('don', 0)
            det_wins = stats_dict.get('detective', 0)
            doc_wins = stats_dict.get('doctor', 0)
            bg_wins = stats_dict.get('bodyguard', 0)
            maniac_wins = stats_dict.get('maniac', 0)
            
            if mafia_wins >= 5:
                keys_to_unlock.append("mafia_veteran")
            if det_wins >= 5:
                keys_to_unlock.append("detective_holmes")
            if (doc_wins + bg_wins) >= 5:
                keys_to_unlock.append("guardian_angel")
            if maniac_wins >= 5:
                keys_to_unlock.append("serial_killer")
                
    for key in keys_to_unlock:
        await unlock_achievement(user_id, key)

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
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return False, 0, "Foydalanuvchi topilmadi."
            
            row_dict = dict(row)
            now = datetime.now()
            last_claim_str = row_dict.get('last_daily_claim')
            current_streak = row_dict.get('streak_days', 0) or 0
            
            if last_claim_str:
                try:
                    last_claim = datetime.fromisoformat(last_claim_str)
                    delta = now - last_claim
                    if delta.total_seconds() < 86400:
                        seconds_left = int(86400 - delta.total_seconds())
                        hours = seconds_left // 3600
                        minutes = (seconds_left % 3600) // 60
                        return False, 0, f"Har 24 soatda 1 marta olish mumkin! ({hours} soat {minutes} daqiqa qoldi)"
                    elif delta.total_seconds() > 172800:
                        current_streak = 0
                except Exception:
                    pass
            
            new_streak = current_streak + 1
            if new_streak > 7:
                new_streak = 1
                
            streak_rewards = {
                1: 10,
                2: 20,
                3: 30,
                4: 50,
                5: 75,
                6: 100,
                7: 200
            }
            bonus_coins = streak_rewards.get(new_streak, 50)
            
            await db.execute(
                "UPDATE users SET coins = coins + ?, last_daily_claim = ?, streak_days = ? WHERE user_id = ?",
                (bonus_coins, now.isoformat(), new_streak, user_id)
            )
            
            is_vip_awarded = False
            if new_streak == 7:
                await upgrade_to_vip(user_id, 3)
                is_vip_awarded = True
                
            await db.commit()
            return True, bonus_coins, {"streak_day": new_streak, "is_vip_awarded": is_vip_awarded}

async def track_group_invite(bot, inviter_id: int, new_members_count: int = 1):
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute("INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)", (inviter_id, f"User{inviter_id}", "User"))
            
            async with db.execute("SELECT group_invites FROM users WHERE user_id = ?", (inviter_id,)) as cursor:
                row = await cursor.fetchone()
                old_invites = row[0] if (row and row[0]) else 0
                
            new_total = old_invites + new_members_count
            await db.execute("UPDATE users SET group_invites = ? WHERE user_id = ?", (new_total, inviter_id))
            await db.commit()
            
            old_milestone = old_invites // 5
            new_milestone = new_total // 5
            
            if new_milestone > old_milestone:
                await upgrade_to_vip(inviter_id, 3)
                await add_xp_and_coins(inviter_id, 0, 200)
                try:
                    await bot.send_message(
                        inviter_id,
                        f"🎉 **TABRIKLAYMIZ!** Siz guruhga {new_total} ta do'stingizni taklif qildingiz va **3 kunlik VIP Status** hamda **200 ta Dark Coins** yutib oldingiz!",
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass
        except Exception as e:
            import logging
            logging.error(f"Error in track_group_invite: {e}")

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
            await db.execute("INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)", (owner_id, f"User{owner_id}", "Mafiozi"))
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
        except Exception as e:
            import logging
            logging.error(f"Error in create_room: {e}")
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
            SELECT rp.*, 
                   COALESCE(u.username, '') as username, 
                   COALESCE(u.first_name, 'O\'yinchi') as first_name, 
                   COALESCE(u.level, 1) as level 
            FROM room_players rp
            LEFT JOIN users u ON rp.user_id = u.user_id
            WHERE rp.room_id = ?
        """
        async with db.execute(query, (room_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def join_room(room_id: str, user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute("INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)", (user_id, f"User{user_id}", "Mafiozi"))
            
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
        except Exception as e:
            import logging
            logging.error(f"Error in join_room: {e}")
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
        except Exception as e:
            import logging
            logging.error(f"Error in leave_room: {e}")
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

async def set_player_alive(room_id: str, user_id: int, is_alive: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        val = 1 if is_alive else 0
        await db.execute("UPDATE room_players SET is_alive = ? WHERE room_id = ? AND user_id = ?", (val, room_id, user_id))
        await db.commit()

async def reset_room_afk(room_id: str, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE room_players SET afk_streak = 0 WHERE room_id = ? AND user_id = ?", (room_id, user_id))
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
            await db.execute("INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)", (leader_id, f"User{leader_id}", "Leader"))
            # Delete old parties of leader
            await db.execute("DELETE FROM parties WHERE leader_id = ? OR member_id = ?", (leader_id, leader_id))
            # Add leader as member
            await db.execute("INSERT INTO parties (party_id, leader_id, member_id) VALUES (?, ?, ?)", (party_id, leader_id, leader_id))
            await db.commit()
            return True
        except Exception as e:
            import logging
            logging.error(f"Error in create_party: {e}")
            return False

async def add_to_party(party_id: str, leader_id: int, member_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute("INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)", (member_id, f"User{member_id}", "Mafiozi"))
            await db.execute("INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)", (leader_id, f"User{leader_id}", "Leader"))
            
            # Check if already in party
            async with db.execute("SELECT 1 FROM parties WHERE party_id = ? AND member_id = ?", (party_id, member_id)) as cursor:
                if await cursor.fetchone():
                    return True
                    
            # Delete member from old parties if any
            await db.execute("DELETE FROM parties WHERE member_id = ?", (member_id,))
            
            # Add member
            await db.execute("INSERT INTO parties (party_id, leader_id, member_id) VALUES (?, ?, ?)", (party_id, leader_id, member_id))
            await db.commit()
            return True
        except Exception as e:
            import logging
            logging.error(f"Error in add_to_party: {e}")
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
            SELECT p.*, 
                   u.user_id, 
                   COALESCE(u.username, '') as username, 
                   COALESCE(u.first_name, 'O\'yinchi') as first_name, 
                   COALESCE(u.level, 1) as level 
            FROM parties p
            LEFT JOIN users u ON p.member_id = u.user_id
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

async def upgrade_to_vip(user_id: int, days: int = 30) -> bool:
    from datetime import datetime, timedelta
    expiry = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "UPDATE users SET is_vip = 1, vip_expires_at = ? WHERE user_id = ?",
                (expiry, user_id)
            )
            await db.commit()
            return True
        except Exception:
            return False

async def set_custom_bg(user_id: int, bg_url: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            async with db.execute("SELECT is_vip FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                if not row or row[0] != 1:
                    return False
            await db.execute("UPDATE users SET custom_bg = ? WHERE user_id = ?", (bg_url, user_id))
            await db.commit()
            return True
        except Exception:
            return False

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
        "name_uz": "Birinchi G'alaba", "name_ru": "Первая Победа", "name_en": "First Win", "name_kz": "Бірінші Жеңіс",
        "desc_uz": "Mafiya o'yinida 1-marta g'alaba qozonish", "desc_ru": "Выиграть 1 игру", "desc_en": "Win 1 game", "desc_kz": "1 ойында жеңіске жету",
        "icon": "🏆", "reward": 50
    },
    "mafia_slayer": {
        "name_uz": "Mafiya Qotili", "name_ru": "Истребитель Мафии", "name_en": "Mafia Slayer", "name_kz": "Мафия Қолынан",
        "desc_uz": "Tinch aholi bo'lib mafiyani o'ldirish", "desc_ru": "Убить мафию будучи мирным", "desc_en": "Kill a mafia member as a civilian", "desc_kz": "Бейбіт тұрғын болып мафияны өлтіру",
        "icon": "⚔️", "reward": 100
    },
    "active_player": {
        "name_uz": "Faol O'yinchi", "name_ru": "Активный Игрок", "name_en": "Active Player", "name_kz": "Белсенді Ойыншы",
        "desc_uz": "Jami 10 ta o'yinda qatnashish", "desc_ru": "Сыграть всего 10 игр", "desc_en": "Play a total of 10 games", "desc_kz": "Барлығы 10 ойын ойнау",
        "icon": "🎮", "reward": 150
    },
    "rich_mafia": {
        "name_uz": "Boy Mafioz", "name_ru": "Богатый Мафиози", "name_en": "Rich Mafia", "name_kz": "Бай Мафиози",
        "desc_uz": "Jami 500 tanga yig'ish", "desc_ru": "Собрать 500 монет", "desc_en": "Accumulate 500 coins", "desc_kz": "Барлығы 500 монета жинау",
        "icon": "💰", "reward": 200
    },
    "mafia_veteran": {
        "name_uz": "Mafiya Veterani", "name_ru": "Ветеран Мафии", "name_en": "Mafia Veteran", "name_kz": "Мафия Ардагері",
        "desc_uz": "Mafiya/Don bo'lib 5 ta o'yinda yutish", "desc_ru": "5 побед за Мафию/Дона", "desc_en": "Win 5 games as Mafia/Don", "desc_kz": "Мафия/Дон болып 5 ойынды жеңу",
        "icon": "🕶️", "reward": 100
    },
    "detective_holmes": {
        "name_uz": "Komissar Xolms", "name_ru": "Комиссар Холмс", "name_en": "Detective Holmes", "name_kz": "Комиссар Холмс",
        "desc_uz": "Komissar bo'lib 5 ta o'yinda yutish", "desc_ru": "5 побед за Комиссара", "desc_en": "Win 5 games as Detective", "desc_kz": "Комиссар болып 5 ойынды жеңу",
        "icon": "🔍", "reward": 100
    },
    "guardian_angel": {
        "name_uz": "Himoyachi Farishta", "name_ru": "Ангел-Хранитель", "name_en": "Guardian Angel", "name_kz": "Қорғаушы Періште",
        "desc_uz": "Shifokor/Tansoqchi bo'lib 5 marta yutish", "desc_ru": "5 побед за Доктора/Телохранителя", "desc_en": "Win 5 games as Doctor/Bodyguard", "desc_kz": "Дәрігер/Қорғаушы болып 5 рет жеңу",
        "icon": "👼", "reward": 100
    },
    "serial_killer": {
        "name_uz": "Telba Qotil", "name_ru": "Безумный Убийца", "name_en": "Maniac Killer", "name_kz": "Жынды Қанішер",
        "desc_uz": "Telba (Maniac) bo'lib 5 marta yutish", "desc_ru": "5 побед за Маньяка", "desc_en": "Win 5 games as Maniac", "desc_kz": "Маньяк болып 5 рет жеңу",
        "icon": "🔪", "reward": 100
    },
    "lvl_10": {
        "name_uz": "Tajribali Jangchi", "name_ru": "Опытный Боец", "name_en": "Seasoned Fighter", "name_kz": "Тәжірибелі Жауынгер",
        "desc_uz": "10-darajaga erishish", "desc_ru": "Достичь 10 уровня", "desc_en": "Reach Level 10", "desc_kz": "10-деңгейге жету",
        "icon": "🎖️", "reward": 150
    },
    "lvl_100": {
        "name_uz": "Afsonaviy Master", "name_ru": "Легендарный Мастер", "name_en": "Legendary Master", "name_kz": "Аңызға айналған Шебер",
        "desc_uz": "100-darajaga erishish", "desc_ru": "Достичь 100 уровня", "desc_en": "Reach Level 100", "desc_kz": "100-деңгейге жету",
        "icon": "👑", "reward": 500
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
                "name_en": info.get("name_en", key),
                "name_kz": info.get("name_kz", key),
                "desc_uz": info["desc_uz"],
                "desc_ru": info["desc_ru"],
                "desc_en": info.get("desc_en", ""),
                "desc_kz": info.get("desc_kz", ""),
                "icon": info.get("icon", "🏆"),
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

# --- TELEGRAM BACKUP & RESTORE ---
import logging

async def restore_db_backup(bot):
    backup_chat = os.getenv("BACKUP_CHAT_ID")
    if not backup_chat:
        logging.info("BACKUP_CHAT_ID aniqlanmadi, zaxiradan tiklash o'tkazib yuborildi.")
        return False
    try:
        chat = await bot.get_chat(backup_chat)
        if chat.pinned_message and chat.pinned_message.document:
            doc = chat.pinned_message.document
            if doc.file_name == "darktown.db":
                os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
                await bot.download(doc.file_id, destination=DB_PATH)
                logging.info("Database zaxiradan muvaffaqiyatli tiklandi!")
                return True
    except Exception as e:
        logging.error(f"Error restoring DB backup: {e}")
    return False

async def save_db_backup(bot):
    backup_chat = os.getenv("BACKUP_CHAT_ID")
    if not backup_chat or not os.path.exists(DB_PATH):
        return False
    try:
        from aiogram.types import FSInputFile
        file_to_send = FSInputFile(DB_PATH, filename="darktown.db")
        msg = await bot.send_document(
            chat_id=backup_chat,
            document=file_to_send,
            caption=f"Darktown DB Auto-Backup\nSana: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        await bot.pin_chat_message(chat_id=backup_chat, message_id=msg.message_id)
        logging.info("Database muvaffaqiyatli Telegram-ga yuklandi va pin qilindi!")
        return True
    except Exception as e:
        logging.error(f"Error saving DB backup: {e}")
    return False

async def get_group_leaderboard(chat_id: int, limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT gh.user_id, u.username, u.first_name, COUNT(gh.id) as games_played, SUM(gh.is_winner) as games_won
            FROM game_history gh
            JOIN users u ON gh.user_id = u.user_id
            WHERE gh.room_id = ?
            GROUP BY gh.user_id
            ORDER BY games_won DESC, games_played ASC
            LIMIT ?
        """
        async with db.execute(query, (str(chat_id), limit)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

# Clans System helper functions
async def create_clan(name: str, leader_id: int, logo_url: str = None) -> tuple[bool, str, dict | None]:
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute("INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)", (leader_id, f"User{leader_id}", "Leader"))
            
            async with db.execute("SELECT clan_id FROM clan_members WHERE user_id = ?", (leader_id,)) as cursor:
                if await cursor.fetchone():
                    return False, "Siz allaqachon klan a'zosisiz! Yangi klan yaratish uchun avvalgisidan chiqing.", None
            
            async with db.execute("SELECT clan_id FROM clans WHERE name = ?", (name,)) as cursor:
                if await cursor.fetchone():
                    return False, "Ushbu nomdagi klan allaqachon mavjud!", None
                    
            import uuid
            clan_id = f"clan_{uuid.uuid4().hex[:8]}"
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            await db.execute(
                "INSERT INTO clans (clan_id, name, leader_id, logo_url, total_wins, total_points, created_at) "
                "VALUES (?, ?, ?, ?, 0, 0, ?)",
                (clan_id, name, leader_id, logo_url, created_at)
            )
            await db.execute(
                "INSERT INTO clan_members (clan_id, user_id, role, joined_at) VALUES (?, ?, 'leader', ?)",
                (clan_id, leader_id, created_at)
            )
            await db.commit()
            return True, "Klan muvaffaqiyatli yaratildi!", {"clan_id": clan_id, "name": name, "leader_id": leader_id}
        except Exception as e:
            import logging
            logging.error(f"Error in create_clan: {e}")
            return False, "Klan yaratishda xatolik yuz berdi", None

async def join_clan(clan_id: str, user_id: int) -> tuple[bool, str]:
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute("INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)", (user_id, f"User{user_id}", "Mafiozi"))
            
            async with db.execute("SELECT clan_id FROM clan_members WHERE user_id = ?", (user_id,)) as cursor:
                if await cursor.fetchone():
                    return False, "Siz allaqachon klan a'zosisiz!"
                    
            async with db.execute("SELECT clan_id, name FROM clans WHERE clan_id = ? OR name = ?", (clan_id, clan_id)) as cursor:
                clan = await cursor.fetchone()
                if not clan:
                    return False, "Bunday klan topilmadi!"
                target_clan_id = clan[0]
                
            joined_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            await db.execute(
                "INSERT INTO clan_members (clan_id, user_id, role, joined_at) VALUES (?, ?, 'member', ?)",
                (target_clan_id, user_id, joined_at)
            )
            await db.commit()
            return True, "Klanga muvaffaqiyatli qo'shildingiz!"
        except Exception as e:
            import logging
            logging.error(f"Error in join_clan: {e}")
            return False, "Klanga qo'shilishda xatolik yuz berdi"

async def leave_clan(user_id: int) -> tuple[bool, str]:
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            async with db.execute("SELECT clan_id, role FROM clan_members WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return False, "Siz hech qaysi klanda emassiz!"
                clan_id, role = row[0], row[1]
                
            if role == 'leader':
                async with db.execute("SELECT user_id FROM clan_members WHERE clan_id = ? AND user_id != ?", (clan_id, user_id)) as cursor:
                    other_members = await cursor.fetchall()
                    if other_members:
                        new_leader = other_members[0][0]
                        await db.execute("UPDATE clan_members SET role = 'leader' WHERE user_id = ?", (new_leader,))
                        await db.execute("UPDATE clans SET leader_id = ? WHERE clan_id = ?", (new_leader, clan_id))
                    else:
                        await db.execute("DELETE FROM clans WHERE clan_id = ?", (clan_id,))
                        
            await db.execute("DELETE FROM clan_members WHERE user_id = ?", (user_id,))
            await db.commit()
            return True, "Klandan muvaffaqiyatli chiqdingiz!"
        except Exception as e:
            import logging
            logging.error(f"Error in leave_clan: {e}")
            return False, "Klandan chiqishda xatolik yuz berdi"

async def get_user_clan(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT c.*, cm.role as user_role, cm.joined_at 
            FROM clan_members cm
            JOIN clans c ON cm.clan_id = c.clan_id
            WHERE cm.user_id = ?
        """
        async with db.execute(query, (user_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def get_clan_members(clan_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT cm.*, u.username, u.first_name, u.level, u.xp, u.coins 
            FROM clan_members cm
            JOIN users u ON cm.user_id = u.user_id
            WHERE cm.clan_id = ?
            ORDER BY CASE WHEN cm.role = 'leader' THEN 0 ELSE 1 END, cm.joined_at ASC
        """
        async with db.execute(query, (clan_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def get_clan_leaderboard(limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT c.clan_id, c.name, c.leader_id, c.logo_url, c.total_wins, c.total_points, c.created_at,
                   COUNT(cm.user_id) as member_count, COALESCE(u.first_name, 'Lider') as leader_name 
            FROM clans c
            LEFT JOIN clan_members cm ON c.clan_id = cm.clan_id
            LEFT JOIN users u ON c.leader_id = u.user_id
            GROUP BY c.clan_id, c.name, c.leader_id, c.logo_url, c.total_wins, c.total_points, c.created_at, u.first_name
            ORDER BY c.total_points DESC, c.total_wins DESC
            LIMIT ?
        """
        async with db.execute(query, (limit,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def add_clan_points(user_id: int, points: int = 10, is_win: bool = False):
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            async with db.execute("SELECT clan_id FROM clan_members WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return
                clan_id = row[0]
                
            win_val = 1 if is_win else 0
            await db.execute(
                "UPDATE clans SET total_points = total_points + ?, total_wins = total_wins + ? WHERE clan_id = ?",
                (points, win_val, clan_id)
            )
            await db.commit()
        except Exception as e:
            import logging
            logging.error(f"Error adding clan points: {e}")

# Tournaments DB Functions
async def get_tournaments():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT t.*, (SELECT COUNT(*) FROM tournament_participants tp WHERE tp.tournament_id = t.id) as participants_count FROM tournaments t ORDER BY t.id DESC") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def create_tournament(title: str, prize_pool: str, start_time: str, group_link: str = None) -> tuple[bool, str]:
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO tournaments (title, prize_pool, status, start_time, group_link) VALUES (?, ?, 'active', ?, ?)",
                (title, prize_pool, start_time, group_link or "https://t.me/DarkTownuz")
            )
            await db.commit()
            return True, "Turnir muvaffaqiyatli yaratildi!"
        except Exception as e:
            import logging
            logging.error(f"Error creating tournament: {e}")
            return False, f"Turnir yaratishda xatolik: {e}"

async def join_tournament(tournament_id: int, user_id: int) -> tuple[bool, str, str | None]:
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute("INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)", (user_id, f"User{user_id}", "Turnirchi"))
            joined_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            await db.execute(
                "INSERT INTO tournament_participants (tournament_id, user_id, joined_at) VALUES (?, ?, ?)",
                (tournament_id, user_id, joined_at)
            )
            await db.commit()
            
            async with db.execute("SELECT group_link FROM tournaments WHERE id = ?", (tournament_id,)) as cursor:
                row = await cursor.fetchone()
                glink = row[0] if (row and row[0]) else "https://t.me/DarkTownuz"
                
            return True, "Turnirga muvaffaqiyatli ro'yxatdan o'tdingiz!", glink
        except Exception:
            async with db.execute("SELECT group_link FROM tournaments WHERE id = ?", (tournament_id,)) as cursor:
                row = await cursor.fetchone()
                glink = row[0] if (row and row[0]) else "https://t.me/DarkTownuz"
            return False, "Siz allaqachon ushbu turnirga ro'yxatdan o'tgansiz!", glink

async def is_user_registered_for_tournament(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        query = """
            SELECT tp.user_id 
            FROM tournament_participants tp
            JOIN tournaments t ON tp.tournament_id = t.id
            WHERE tp.user_id = ? AND t.status = 'active'
        """
        async with db.execute(query, (user_id,)) as cursor:
            return bool(await cursor.fetchone())

async def add_tournament_points(user_id: int, points: int):
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute("UPDATE users SET tournament_points = COALESCE(tournament_points, 0) + ? WHERE user_id = ?", (points, user_id))
            await db.commit()
        except Exception as e:
            import logging
            logging.error(f"Error adding tournament points: {e}")

async def distribute_tournament_prizes(tournament_id: int, winner_user_id: int, coins: int = 1000, vip_days: int = 7) -> tuple[bool, str, str | None, dict | None]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        try:
            async with db.execute("SELECT * FROM users WHERE user_id = ?", (winner_user_id,)) as cursor:
                user_row = await cursor.fetchone()
                if not user_row:
                    return False, "G'olib foydalanuvchi topilmadi!", None, None
                user_dict = dict(user_row)
                winner_name = user_dict.get('first_name') or user_dict.get('username') or f"User{winner_user_id}"
                
            async with db.execute("SELECT * FROM tournaments WHERE id = ?", (tournament_id,)) as cursor2:
                t_row = await cursor2.fetchone()
                t_dict = dict(t_row) if t_row else {}
                
            await db.execute("UPDATE tournaments SET status = 'completed', winner_name = ? WHERE id = ?", (winner_name, tournament_id))
            await db.commit()
            
            await add_xp_and_coins(winner_user_id, 500, coins)
            await upgrade_to_vip(winner_user_id, vip_days)
            
            username = user_dict.get('username')
            t_link = f"https://t.me/{username}" if username else f"tg://user?id={winner_user_id}"
            
            details = {
                "title": t_dict.get("title", "DarkTown Turnir"),
                "prize_pool": t_dict.get("prize_pool", "Mukofotlar"),
                "winner_name": winner_name,
                "username": username,
                "group_link": t_dict.get("group_link")
            }
            
            return True, f"Turnir muvaffaqiyatli yakunlandi! G'olib **{winner_name}**ga +{coins} Coins va {vip_days} Kunlik VIP berildi va kanalda e'lon qilindi.", t_link, details
        except Exception as e:
            import logging
            logging.error(f"Error in distribute_tournament_prizes: {e}")
            return False, f"Xatolik: {e}", None, None

async def delete_tournament(tournament_id: int) -> tuple[bool, str]:
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute("DELETE FROM tournament_participants WHERE tournament_id = ?", (tournament_id,))
            await db.execute("DELETE FROM tournaments WHERE id = ?", (tournament_id,))
            await db.commit()
            return True, "Turnir muvaffaqiyatli o'chirildi!"
        except Exception as e:
            import logging
            logging.error(f"Error deleting tournament: {e}")
            return False, f"O'chirishda xatolik: {e}"

# Battle Pass DB Functions
async def get_user_battle_pass(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM battle_pass WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                await db.execute("INSERT INTO battle_pass (user_id, pass_level, pass_xp, is_premium) VALUES (?, 1, 0, 0)", (user_id,))
                await db.commit()
                return {"user_id": user_id, "pass_level": 1, "pass_xp": 0, "is_premium": 0}
            return dict(row)

async def add_battle_pass_xp(user_id: int, xp_gain: int):
    bp = await get_user_battle_pass(user_id)
    new_xp = bp["pass_xp"] + xp_gain
    new_level = bp["pass_level"]
    
    while new_xp >= 100 and new_level < 30:
        new_xp -= 100
        new_level += 1
        
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE battle_pass SET pass_level = ?, pass_xp = ? WHERE user_id = ?",
            (new_level, new_xp, user_id)
        )
        await db.commit()
