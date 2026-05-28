# services/dynamics/emoji_game_service.py
import random

import discord

from services.dynamics.base_service import get_dynamic_participants

# Estado de la dinámica por servidor
EMOJI_GAME_STATE = {}

# -----------------------------
# Inicializar dinámica en memoria
# -----------------------------
async def start_emoji_game(guild_id, rounds=10):
    EMOJI_GAME_STATE[guild_id] = {
        "current_round": 0,
        "total_rounds": rounds,
        "choices": {},  # {user_id: emoji}
        "participants_points": {}  # Puntos acumulados de cada participante
    }

# -----------------------------
# Terminar dinámica
# -----------------------------
async def end_emoji_game(guild_id):
    EMOJI_GAME_STATE.pop(guild_id, None)

# -----------------------------
# Registrar elección de usuario
# -----------------------------
def add_user_choice(guild_id, user_id, emoji):
    """Guarda el emoji elegido por el usuario (solo 1 por persona)"""
    state = EMOJI_GAME_STATE.get(guild_id)
    if not state:
        return False
    if user_id in state["choices"]:
        return False
    state["choices"][user_id] = emoji
    return True

# -----------------------------
# Iniciar dinámica en un canal
# -----------------------------
async def start_emoji_dynamic(guild_id, channel, total_rounds=10):
    # 1️⃣ Obtener participantes desde la DB
    participants = await get_dynamic_participants(guild_id)
    if not participants:
        await channel.send("❌ No hay participantes para iniciar la dinámica.")
        return False

    # 2️⃣ Inicializar dinámica en memoria
    await start_emoji_game(guild_id, rounds=total_rounds)

    # 3️⃣ Inicializar puntos de los participantes
    EMOJI_GAME_STATE[guild_id]["participants_points"] = {p["user_id"]: 0 for p in participants}

    # 4️⃣ Informar inicio de la dinámica
    participant_mentions = ", ".join(f"<@{p['user_id']}>" for p in participants)
    embed = discord.Embed(
        title="🎨 ¡La dinámica de Emojis ha comenzado!",
        description=f"Participantes: {participant_mentions}\nSerán {total_rounds} rondas. ¡Buena suerte!",
        color=discord.Color.purple()
    )
    embed.set_image(url="https://media.giphy.com/media/3o7aD2saalBwwftBIY/giphy.gif")
    await channel.send(embed=embed)

    return True

# -----------------------------
# Calcular ganadores de la ronda y acumular puntos
# -----------------------------
def get_winners(guild_id):
    state = EMOJI_GAME_STATE.get(guild_id)

    if not state or not state["choices"]:
        return []

    # 🔥 USAR TODOS LOS EMOJIS, NO SOLO LOS ELEGIDOS
    all_emojis = ["🐾", "🦋", "🏆", "🎨"]

    # Elegir 3 emojis ganadores aleatorios
    winning_emojis = random.sample(all_emojis, k=min(3, len(all_emojis)))

    # Guardar en el estado
    state["winning_emojis"] = winning_emojis

    points_map = {
        winning_emojis[0]: 5,
        winning_emojis[1]: 3 if len(winning_emojis) > 1 else 0,
        winning_emojis[2]: 1 if len(winning_emojis) > 2 else 0
    }

    winners = []

    for user_id, emoji in state["choices"].items():
        points = points_map.get(emoji, 0)

        if points > 0:
            winners.append({
                "user_id": user_id,
                "emoji": emoji,
                "points": points
            })

            # acumular puntos
            state["participants_points"].setdefault(user_id, 0)
            state["participants_points"][user_id] += points

    return winners

# -----------------------------
# Avanzar ronda y limpiar elecciones
# -----------------------------
def next_round(guild_id):
    state = EMOJI_GAME_STATE.get(guild_id)
    if not state:
        return False
    state["current_round"] += 1
    state["choices"] = {}
    return state["current_round"]