# services/ranking_services.py
from database.connection import db

async def get_top_weekly(guild_id, limit=5):
    async with db.pool.acquire() as conn:
        return await conn.fetch(
            """
            SELECT user_id, weekly_points
            FROM user_points
            WHERE guild_id = $1
            ORDER BY weekly_points DESC, user_id ASC
            LIMIT $2
            """,
            guild_id, limit
        )

async def get_top_monthly(guild_id, limit=5):
    async with db.pool.acquire() as conn:
        return await conn.fetch(
            """
            SELECT user_id, monthly_points
            FROM user_points
            WHERE guild_id = $1
            ORDER BY monthly_points DESC, user_id ASC
            LIMIT $2
            """,
            guild_id, limit
        )
    
async def get_top_coins(guild_id: int, limit: int = 5):
    """Obtiene el top de usuarios por balance en un servidor"""
    async with db.pool.acquire() as conn:
        return await conn.fetch(
            """
            SELECT u.username, w.balance, w.user_id
            FROM wallets w
            JOIN users u ON w.user_id = u.id
            WHERE w.guild_id = $1
            ORDER BY w.balance DESC
            LIMIT $2
            """,
            guild_id, limit
        )

async def get_total_users(guild_id):
    async with db.pool.acquire() as conn:
        return await conn.fetchval(
            "SELECT COUNT(*) FROM user_points WHERE guild_id = $1",
            guild_id
        )
