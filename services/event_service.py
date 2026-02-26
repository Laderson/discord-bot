from database.connection import db

async def is_event_active(guild_id: int):
    async with db.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT 1 FROM rounds_config
            WHERE guild_id = $1 AND is_active = TRUE
        """, guild_id)
        return row is not None

async def stop_event(guild_id: int):
    async with db.acquire() as conn:
        await conn.execute("""
            UPDATE rounds_config
            SET is_active = FALSE
            WHERE guild_id = $1
        """, guild_id)

async def stop_event(guild_id: int):
    async with db.pool.acquire() as conn:
        await conn.execute(
            "UPDATE events SET active=FALSE WHERE guild_id=$1",
            guild_id
        )

