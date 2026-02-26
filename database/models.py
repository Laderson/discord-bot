async def create_tables(pool):
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                coins INTEGER DEFAULT 0,
                weekly_points INTEGER DEFAULT 0,
                monthly_points INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
