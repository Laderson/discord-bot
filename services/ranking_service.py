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
    
# ================== OBTENER PUNTOS DE UN USUARIO ==================
async def get_user_points(guild_id: int, user_id: int):
    """
    Devuelve los puntos semanales y mensuales de un usuario en un servidor.
    Retorna un dict: {"weekly_points": int, "monthly_points": int}
    """
    async with db.pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT weekly_points, monthly_points
            FROM user_points
            WHERE guild_id = $1 AND user_id = $2
            """,
            guild_id, user_id
        )

    if row:
        return {"weekly_points": row["weekly_points"], "monthly_points": row["monthly_points"]}
    return {"weekly_points": 0, "monthly_points": 0}
    
async def add_points(guild_id: int, user_id: int, points: int):
    async with db.pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO user_points (guild_id, user_id, weekly_points, monthly_points)
            VALUES ($1, $2, $3, $3)
            ON CONFLICT (guild_id, user_id)
            DO UPDATE SET
                weekly_points = user_points.weekly_points + $3,
                monthly_points = user_points.monthly_points + $3
        """, guild_id, user_id, points)

# ================== REMOVER PUNTOS ==================
async def remove_points(guild_id: int, user_id: int, points: int):
    """
    Resta puntos al ranking global del usuario.
    No permite que los puntos queden negativos.
    """
    async with db.pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO user_points (guild_id, user_id, weekly_points, monthly_points)
            VALUES ($1, $2, 0, 0)
            ON CONFLICT (guild_id, user_id)
            DO UPDATE SET
                weekly_points = GREATEST(user_points.weekly_points - $3, 0),
                monthly_points = GREATEST(user_points.monthly_points - $3, 0)
        """, guild_id, user_id, points)