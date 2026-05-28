import random
from database.connection import db
from services.dynamics.base_service import get_active_dynamic

CARDS = ["El Gallo","El Diablito","La Dama","El Catrín","El Paraguas","La Sirena",
         "La Escalera","La Botella","El Barril","El Árbol","El Melón","El Valiente",
         "El Gorrito","La Muerte","La Pera","La Bandera","El Bandolón","El Violoncello",
         "La Garza","El Pájaro","La Mano","La Bota","La Luna","El Cotorro","El Borracho",
         "El Negrito","El Corazón","La Sandía","El Tambor","El Camarón","Las Jaras","El Músico",
         "La Araña","El Soldado","La Estrella","El Cazo","El Mundo","El Apache","El Nopal","El Alacrán",
         "La Rosa","La Calavera","La Campana","El Cantarito","El Venado","El Sol","La Corona","La Chalupa",
         "El Pino","El Pescado","La Palma","La Maceta","El Arpa","La Rana"]


# =========================
# RANDOM
# =========================
def get_random_card():
    return random.choice(CARDS)


# =========================
# DB ACCESS
# =========================
async def get_participant_card(guild_id: int, user_id: int):
    async with db.pool.acquire() as conn:
        dynamic = await get_active_dynamic(guild_id)
        if not dynamic:
            return None

        row = await conn.fetchrow(
            """
            SELECT extra->>'card' AS card
            FROM dynamic_participants
            WHERE guild_id = $1
              AND user_id = $2
              AND dynamic_id = $3
            """,
            guild_id,
            user_id,
            dynamic["id"]
        )

        return row["card"] if row else None


async def set_participant_card(guild_id: int, user_id: int, card: str):
    async with db.pool.acquire() as conn:
        dynamic = await get_active_dynamic(guild_id)
        if not dynamic:
            raise ValueError("No hay dinámica activa")

        await conn.execute(
            """
            UPDATE dynamic_participants
            SET extra = jsonb_set(
                COALESCE(extra, '{}'::jsonb),
                '{card}',
                to_jsonb($1::text),
                true
            )
            WHERE guild_id = $2
              AND user_id = $3
              AND dynamic_id = $4
            """,
            card,
            guild_id,
            user_id,
            dynamic["id"]
        )


# =========================
# NUEVAS FUNCIONES (CLAVE)
# =========================
async def assign_card_to_user(guild_id: int, user_id: int):
    card = get_random_card()
    await set_participant_card(guild_id, user_id, card)
    return card


async def assign_cards_to_all(guild_id: int, participants: list):
    for p in participants:
        card = get_random_card()
        await set_participant_card(guild_id, p["user_id"], card)


async def get_card_winners(guild_id: int, participants: list, card: str):
    winners = []

    for p in participants:
        player_card = await get_participant_card(guild_id, p["user_id"])
        if player_card == card:
            winners.append(p["user_id"])

    return winners