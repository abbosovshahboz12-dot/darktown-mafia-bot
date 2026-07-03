import aiosqlite
import os
import math

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
