from database.connection import db

class EconomyService:

    @staticmethod
    async def ensure_user(user_id: int, username: str):
        async with db.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO users (id, username)
                VALUES ($1, $2)
                ON CONFLICT (id) DO NOTHING
            """, user_id, username)

    @staticmethod
    async def ensure_guild(guild_id: int, name: str):
        async with db.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO guilds (id, name)
                VALUES ($1, $2)
                ON CONFLICT (id) DO NOTHING
            """, guild_id, name)

    @staticmethod
    async def get_balance(user_id: int, guild_id: int):
        async with db.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO wallets (user_id, guild_id, balance)
                VALUES ($1, $2, 0)
                ON CONFLICT (user_id, guild_id) DO NOTHING
            """, user_id, guild_id)

            result = await conn.fetchrow("""
                SELECT balance FROM wallets
                WHERE user_id = $1 AND guild_id = $2
            """, user_id, guild_id)

            return result["balance"]


    @staticmethod
    async def add_balance(user_id: int, guild_id: int, amount: int):
        async with db.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO wallets (user_id, guild_id, balance)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id, guild_id)
                DO UPDATE SET balance = wallets.balance + $3
            """, user_id, guild_id, amount)
    
    @staticmethod
    async def add_balance_to_user(user_id: int, guild_id: int, amount: int):
        """Agrega coins a un usuario específico (para admins o roles permitidos)"""
        await EconomyService.ensure_user(user_id, "Desconocido")  # Garantiza que exista la fila
        await EconomyService.add_balance(user_id, guild_id, amount)

    
        
    
