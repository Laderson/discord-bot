# services/shop_services.py
from database.connection import db

async def get_available_products():
    """Devuelve todos los productos disponibles de la tienda, ordenados por precio descendente"""
    async with db.pool.acquire() as conn:
        return await conn.fetch(
            """
            SELECT id, name, price, description, category
            FROM shop_items
            WHERE available = TRUE
            ORDER BY price DESC
            """
        )

async def get_product_by_name(product_name):
    async with db.pool.acquire() as conn:
        return await conn.fetchrow(
            "SELECT id, name, price, description, category FROM shop_items WHERE name = $1 AND available = TRUE",
            product_name
        )

async def buy_product(user_id, product_id, guild_id):
    """Resta coins del usuario en un servidor específico y registra la compra"""
    async with db.pool.acquire() as conn:
        async with conn.transaction():
            # Obtener precio y nombre del producto
            product = await conn.fetchrow(
                "SELECT id, name, price FROM shop_items WHERE id = $1 AND available = TRUE",
                product_id
            )
            if not product:
                return False, "Producto no encontrado"

            # Obtener balance del usuario en este servidor
            balance = await conn.fetchval(
                "SELECT balance FROM wallets WHERE user_id = $1 AND guild_id = $2",
                user_id, guild_id
            )
            if balance is None:
                return False, "No tienes wallet en este servidor"

            if balance < product['price']:
                return False, "No tienes suficientes coins en este servidor"

            # Restar coins
            await conn.execute(
                "UPDATE wallets SET balance = balance - $1 WHERE user_id = $2 AND guild_id = $3",
                product['price'], user_id, guild_id
            )

            return True, f"Has comprado {product['name']} por {product['price']} coins ✅"

async def get_product_by_id(product_id):
    """Devuelve un producto por su ID"""
    async with db.pool.acquire() as conn:
        return await conn.fetchrow(
            "SELECT id, name, price, description, category FROM shop_items WHERE id = $1 AND available = TRUE",
            product_id
        )
