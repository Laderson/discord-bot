from database.connection import db

# ==============================
# INICIAR DINÁMICA POR RONDAS
# ==============================
async def start_rounds(guild_id: int, total_rounds: int):
    await db.execute("""
        INSERT INTO rounds_config (
            guild_id,
            total_rounds,
            current_round,
            is_active,
            started_at
        )
        VALUES ($1, $2, 1, TRUE, NOW())
        ON CONFLICT (guild_id)
        DO UPDATE SET
            total_rounds = $2,
            current_round = 1,
            is_active = TRUE,
            started_at = NOW()
    """, guild_id, total_rounds)


# ==============================
# OBTENER DINÁMICA ACTIVA
# ==============================
async def get_active_round(guild_id: int):
    return await db.fetchrow("""
        SELECT *
        FROM rounds_config
        WHERE guild_id = $1 AND is_active = TRUE
    """, guild_id)


# ==============================
# AVANZAR RONDA
# ==============================
async def advance_round(guild_id: int):
    await db.execute("""
        UPDATE rounds_config
        SET current_round = current_round + 1
        WHERE guild_id = $1
    """, guild_id)


# ==============================
# FINALIZAR DINÁMICA
# ==============================
async def finish_rounds(guild_id: int):
    await db.execute("""
        UPDATE rounds_config
        SET is_active = FALSE
        WHERE guild_id = $1
    """, guild_id)


# ==============================
# SUMAR PUNTOS A USUARIO
# ==============================
async def add_points(guild_id: int, user_id: int, amount: int):
    await db.execute("""
        INSERT INTO event_points (guild_id, user_id, points)
        VALUES ($1, $2, $3)
        ON CONFLICT (guild_id, user_id)
        DO UPDATE SET points = event_points.points + $3
    """, guild_id, user_id, amount)


# ==============================
# RESTAR PUNTOS
# ==============================
async def remove_points(guild_id: int, user_id: int, amount: int):
    await add_points(guild_id, user_id, -amount)


# ==============================
# TABLA DE POSICIONES
# ==============================
async def get_table(guild_id: int):
    return await db.fetch("""
        SELECT user_id, points
        FROM event_points
        WHERE guild_id = $1
        ORDER BY points DESC
    """, guild_id)


# ==============================
# LIMPIAR EVENTO
# ==============================
async def clear_event(guild_id: int):
    await db.execute("DELETE FROM event_points WHERE guild_id = $1", guild_id)
    await db.execute("DELETE FROM rounds_config WHERE guild_id = $1", guild_id)
