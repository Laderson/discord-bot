from database.connection import db

# -----------------------------
# Dinámicas
# -----------------------------

async def get_dynamic_by_code(code: str):
    async with db.pool.acquire() as conn:
        return await conn.fetchrow(
            "SELECT id, code, name FROM dynamics WHERE code = $1",
            code
        )

async def reset_dynamic_participants(guild_id: int):
    async with db.pool.acquire() as conn:
        await conn.execute(
            """
            DELETE FROM dynamic_participants
            WHERE guild_id = $1
            """,
            guild_id
        )

async def start_dynamic(guild_id: int, dynamic_code: str):
    async with db.pool.acquire() as conn:
        dynamic = await conn.fetchrow(
            "SELECT id FROM dynamics WHERE code = $1",
            dynamic_code
        )
        if not dynamic:
            raise ValueError("Dinámica no registrada")

        await conn.execute(
            """
            INSERT INTO guild_dynamics (guild_id, dynamic_id, is_active)
            VALUES ($1, $2, TRUE)
            ON CONFLICT (guild_id)
            DO UPDATE SET
                dynamic_id = EXCLUDED.dynamic_id,
                is_active = TRUE,
                started_at = NOW()
            """,
            guild_id,
            dynamic["id"]
        )

async def end_dynamic(guild_id: int):
    async with db.pool.acquire() as conn:
        await conn.execute("DELETE FROM guild_dynamics WHERE guild_id = $1", guild_id)
        await conn.execute("DELETE FROM dynamic_participants WHERE guild_id = $1", guild_id)
        await conn.execute("DELETE FROM dynamic_state WHERE guild_id = $1", guild_id)

async def get_active_dynamic(guild_id: int):
    async with db.pool.acquire() as conn:
        return await conn.fetchrow(
            """
            SELECT d.id, d.code, d.name
            FROM guild_dynamics gd
            JOIN dynamics d ON d.id = gd.dynamic_id
            WHERE gd.guild_id = $1 AND gd.is_active = TRUE
            """,
            guild_id
        )

async def is_participant(guild_id: int, user_id: int) -> bool:
    async with db.pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT 1
            FROM dynamic_participants dp
            JOIN guild_dynamics gd
              ON dp.guild_id = gd.guild_id
             AND dp.dynamic_id = gd.dynamic_id
            WHERE dp.guild_id = $1
              AND dp.user_id = $2
            """,
            guild_id, user_id
        )
        return row is not None

# -----------------------------
# Participantes
# -----------------------------

async def add_participant(guild_id: int, user_id: int):
    async with db.pool.acquire() as conn:
        dynamic = await get_active_dynamic(guild_id)
        if not dynamic:
            raise ValueError("No hay dinámica activa")

        await conn.execute(
            """
            INSERT INTO dynamic_participants (guild_id, user_id, dynamic_id)
            VALUES ($1, $2, $3)
            ON CONFLICT DO NOTHING
            """,
            guild_id,
            user_id,
            dynamic["id"]
        )

async def get_dynamic_participants(guild_id: int):
    async with db.pool.acquire() as conn:
        dynamic = await get_active_dynamic(guild_id)
        if not dynamic:
            return []

        return await conn.fetch(
            """
            SELECT user_id, points
            FROM dynamic_participants
            WHERE guild_id = $1
              AND dynamic_id = $2
            ORDER BY user_id
            """,
            guild_id,
            dynamic["id"]
        )

async def add_dynamic_points(guild_id: int, user_id: int, points: int):
    async with db.pool.acquire() as conn:
        dynamic = await get_active_dynamic(guild_id)
        if not dynamic:
            raise ValueError("No hay dinámica activa")

        await conn.execute(
            """
            INSERT INTO dynamic_participants (guild_id, user_id, dynamic_id, points)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (guild_id, user_id, dynamic_id)
            DO UPDATE SET
                points = dynamic_participants.points + $4
            """,
            guild_id,
            user_id,
            dynamic["id"],
            points
        )

# -----------------------------
# Ganadores
# -----------------------------

async def get_dynamic_winner(guild_id: int):
    async with db.pool.acquire() as conn:
        dynamic = await get_active_dynamic(guild_id)
        if not dynamic:
            return None

        return await conn.fetchrow(
            """
            SELECT user_id, points
            FROM dynamic_participants
            WHERE guild_id = $1 AND dynamic_id = $2
            ORDER BY points DESC
            LIMIT 1
            """,
            guild_id,
            dynamic["id"]
        )