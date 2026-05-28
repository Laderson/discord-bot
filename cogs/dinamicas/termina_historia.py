import discord
import re

from discord.ext import commands

HISTORIA_CHANNEL_ID = 1502517317618372689


class TerminaHistoria(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):

        if message.author.bot:
            return

        if not message.guild:
            return

        # validar canal
        if message.channel.id != HISTORIA_CHANNEL_ID:
            return

        # normalizar espacios
        content = " ".join(message.content.split())

        # validar texto real
        if not re.search(r"[a-zA-ZáéíóúÁÉÍÓÚñÑ]", content):
            await message.delete()
            return

        # contar palabras reales
        words = re.findall(r"\b\w+\b", content, re.UNICODE)

        # validar cantidad
        if len(words) < 2 or len(words) > 1000:

            await message.delete()

            return await message.channel.send(
                f"{message.author.mention} ❌ Debes escribir entre 2 y 1000 palabras.",
                delete_after=5
            )

        # evitar doble turno
        async for msg in message.channel.history(limit=2):

            if msg.id == message.id:
                continue

            if msg.author.id == message.author.id:

                await message.delete()

                return await message.channel.send(
                    f"{message.author.mention} ❌ Debes esperar otro turno.",
                    delete_after=5
                )


async def setup(bot):
    await bot.add_cog(TerminaHistoria(bot))