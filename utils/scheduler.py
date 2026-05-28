import discord

from datetime import datetime, timedelta
from discord.ext import tasks
from discord.utils import utcnow
from services.ai.story_ai_service import improve_story



HISTORIA_CHANNEL_ID = 1502517317618372689


# =========================
# PUBLICAR HISTORIA SEMANAL
# =========================
async def publish_weekly_story(bot):

    channel = await bot.fetch_channel(HISTORIA_CHANNEL_ID)

    print(f"📚 Canal encontrado: {channel.name}")

    one_week_ago = utcnow() - timedelta(days=7)

    messages = []

    print("📥 Leyendo historial...")

    async for message in channel.history(limit=None, after=one_week_ago):

        print(f"Mensaje leído: {message.content}")

        if message.author.bot:
            continue

        content = message.content.strip()

        if not content:
            continue

        if message.pinned: 
            continue

        messages.append(content)

    if not messages:
        print("❌ No se encontraron mensajes")
        return

    raw_story = " ".join(messages) 
    print("🧠 Mejorando historia con Gemini...") 
    story = await improve_story(raw_story)

    embed = discord.Embed(
        title="📖 Historia semanal",
        description=story[:4000],
        color=discord.Color.purple()
    )

    await channel.send(embed=embed)

    print("✅ Historia publicada")



# =========================
# LOOP AUTOMÁTICO
# =========================
def start_story_scheduler(bot):

    @tasks.loop(minutes=1)
    async def weekly_story_task():

        now = datetime.now()

        # 🟣 SOLO DOMINGO
        if now.weekday() == 6 and now.hour == 20 and now.minute < 2:
            return

        # evitar spam dentro del mismo minuto
        if now.minute != 0:
            return

        print("📖 Publicando historia semanal (DOMINGO)...")

        await publish_weekly_story(bot)

    weekly_story_task.start()