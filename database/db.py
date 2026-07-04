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
        
        # Friends table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS friends (
                user_id INTEGER,
                friend_id INTEGER,
                status TEXT, -- 'pending', 'accepted'
                PRIMARY KEY (user_id, friend_id)
            )
        """)

        # Webapp Matchmaking Queue
        await db.execute("""
            CREATE TABLE IF NOT EXISTS webapp_matchmaking_queue (
                user_id INTEGER PRIMARY KEY,
                joined_at TEXT
            )
        """)

        # Webapp Games table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS webapp_games (
                game_id TEXT PRIMARY KEY,
                phase TEXT, -- 'lobby', 'night', 'day_discussion', 'voting', 'ended'
                phase_ends_at TEXT,
                created_at TEXT
            )
        """)

        # Webapp Game Players table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS webapp_game_players (
                game_id TEXT,
                user_id INTEGER,
                role TEXT,
                is_alive INTEGER DEFAULT 1,
                has_voted INTEGER DEFAULT 0,
                target_id INTEGER, -- night action target
                PRIMARY KEY (game_id, user_id)
            )
        """)

        # Webapp Game Messages table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS webapp_game_messages (
                message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id TEXT,
                sender_id INTEGER,
                sender_name TEXT,
                message_text TEXT,
                is_mafia_only INTEGER DEFAULT 0,
                sent_at TEXT
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
            await db.execute("ALTER TABLE users ADD COLUMN last_spin_claim TEXT")
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

# --- Friends Tizimi ---
async def get_friends(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        # Get accepted friends (either direction in the friends table)
        async with db.execute("""
            SELECT u.user_id, u.username, u.first_name, u.level 
            FROM friends f
            JOIN users u ON (f.friend_id = u.user_id AND f.user_id = ?) 
                         OR (f.user_id = u.user_id AND f.friend_id = ?)
            WHERE f.status = 'accepted' AND u.user_id != ?
        """, (user_id, user_id, user_id)) as cursor:
            friends = [dict(row) for row in await cursor.fetchall()]
            
        # Get incoming pending requests
        async with db.execute("""
            SELECT u.user_id, u.username, u.first_name, u.level
            FROM friends f
            JOIN users u ON f.user_id = u.user_id
            WHERE f.friend_id = ? AND f.status = 'pending'
        """, (user_id,)) as cursor:
            incoming = [dict(row) for row in await cursor.fetchall()]
            
        return {"friends": friends, "incoming": incoming}

async def add_friend(user_id: int, friend_id: int) -> bool:
    if user_id == friend_id:
        return False
    async with aiosqlite.connect(DB_PATH) as db:
        # Check if already friends or pending
        async with db.execute(
            "SELECT * FROM friends WHERE (user_id = ? AND friend_id = ?) OR (user_id = ? AND friend_id = ?)",
            (user_id, friend_id, friend_id, user_id)
        ) as cursor:
            if await cursor.fetchone():
                return False
        await db.execute(
            "INSERT INTO friends (user_id, friend_id, status) VALUES (?, ?, 'pending')",
            (user_id, friend_id)
        )
        await db.commit()
        return True

async def accept_friend(user_id: int, requester_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE friends SET status = 'accepted' WHERE user_id = ? AND friend_id = ? AND status = 'pending'",
            (requester_id, user_id)
        )
        await db.commit()
        return True

# --- Omad G'ildiragi (Wheel of Fortune) ---
async def claim_spin(user_id: int, reward_coins: int, reward_item: str = None) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        now_str = datetime.now().isoformat()
        await db.execute(
            "UPDATE users SET coins = coins + ?, last_spin_claim = ? WHERE user_id = ?",
            (reward_coins, now_str, user_id)
        )
        if reward_item:
            await db.execute(
                "INSERT INTO inventory (user_id, item_key, quantity) VALUES (?, ?, 1) "
                "ON CONFLICT(user_id, item_key) DO UPDATE SET quantity = quantity + 1",
                (user_id, reward_item)
            )
        await db.commit()
        return True

# --- Matchmaking Queue ---
async def join_queue(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        now_str = datetime.now().isoformat()
        await db.execute(
            "INSERT OR REPLACE INTO webapp_matchmaking_queue (user_id, joined_at) VALUES (?, ?)",
            (user_id, now_str)
        )
        await db.commit()

async def leave_queue(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM webapp_matchmaking_queue WHERE user_id = ?", (user_id,))
        await db.commit()

async def get_queue():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT user_id FROM webapp_matchmaking_queue ORDER BY joined_at ASC") as cursor:
            return [row['user_id'] for row in await cursor.fetchall()]

async def clear_queue(user_ids: list):
    if not user_ids:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        placeholders = ",".join(["?" for _ in user_ids])
        await db.execute(f"DELETE FROM webapp_matchmaking_queue WHERE user_id IN ({placeholders})", tuple(user_ids))
        await db.commit()

# --- WebApp Games (Matchrooms) ---
async def create_webapp_game(game_id: str, players: list):
    async with aiosqlite.connect(DB_PATH) as db:
        now_str = datetime.now().isoformat()
        await db.execute(
            "INSERT INTO webapp_games (game_id, phase, phase_ends_at, created_at) VALUES (?, 'lobby', NULL, ?)",
            (game_id, now_str)
        )
        for p in players:
            await db.execute(
                "INSERT INTO webapp_game_players (game_id, user_id, role, is_alive, has_voted, target_id) "
                "VALUES (?, ?, ?, 1, 0, NULL)",
                (game_id, p["user_id"], p["role"])
            )
        await db.commit()

async def get_webapp_game(game_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM webapp_games WHERE game_id = ?", (game_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def update_webapp_game_phase(game_id: str, phase: str, ends_at: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE webapp_games SET phase = ?, phase_ends_at = ? WHERE game_id = ?",
            (phase, ends_at, game_id)
        )
        await db.execute(
            "UPDATE webapp_game_players SET has_voted = 0, target_id = NULL WHERE game_id = ?",
            (game_id,)
        )
        await db.commit()

async def get_webapp_game_players(game_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT gp.*, u.username, u.first_name 
            FROM webapp_game_players gp
            JOIN users u ON gp.user_id = u.user_id
            WHERE gp.game_id = ?
        """, (game_id,)) as cursor:
            return [dict(row) for row in await cursor.fetchall()]

async def submit_webapp_vote(game_id: str, voter_id: int, target_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE webapp_game_players SET has_voted = 1, target_id = ? WHERE game_id = ? AND user_id = ?",
            (target_id, game_id, voter_id)
        )
        await db.commit()

async def submit_webapp_action(game_id: str, user_id: int, target_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE webapp_game_players SET target_id = ? WHERE game_id = ? AND user_id = ?",
            (target_id, game_id, user_id)
        )
        await db.commit()

async def update_webapp_player_status(game_id: str, user_id: int, is_alive: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE webapp_game_players SET is_alive = ? WHERE game_id = ? AND user_id = ?",
            (is_alive, game_id, user_id)
        )
        await db.commit()

async def check_player_active_webapp_game(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT gp.game_id, g.phase
            FROM webapp_game_players gp
            JOIN webapp_games g ON gp.game_id = g.game_id
            WHERE gp.user_id = ? AND g.phase != 'ended'
        """, (user_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

# --- WebApp Messages ---
async def send_webapp_message(game_id: str, sender_id: int, sender_name: str, message_text: str, is_mafia_only: int):
    async with aiosqlite.connect(DB_PATH) as db:
        now_str = datetime.now().isoformat()
        await db.execute("""
            INSERT INTO webapp_game_messages (game_id, sender_id, sender_name, message_text, is_mafia_only, sent_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (game_id, sender_id, sender_name, message_text, is_mafia_only, now_str))
        await db.commit()

async def get_webapp_messages(game_id: str, include_mafia_only: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if include_mafia_only:
            query = "SELECT * FROM webapp_game_messages WHERE game_id = ? ORDER BY message_id ASC"
            params = (game_id,)
        else:
            query = "SELECT * FROM webapp_game_messages WHERE game_id = ? AND is_mafia_only = 0 ORDER BY message_id ASC"
            params = (game_id,)
            
        async with db.execute(query, params) as cursor:
            return [dict(row) for row in await cursor.fetchall()]
