import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv

from database.connection import db
from database.models import create_tables

load_dotenv()

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class MyBot(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db = None  # Placeholder para la DB

    async def setup_hook(self):
        self.tree.clear_commands(guild=None)
        print("🧹 Slash commands limpiados")
        print("🔄 Conectando base de datos...")
        await db.connect()
        await create_tables(db.pool)
        self.db = db  # Guardamos la DB en el bot
        print("✅ Base de datos lista")

        await self.load_all_cogs()

        GUILD_ID = 1415990627195289612  # coloca tu ID real aquí

        guild = discord.Object(id=GUILD_ID)

        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

        print("✅ Slash commands sincronizados en servidor (modo dev)")

        print("✅ Slash commands sincronizados")

    async def load_all_cogs(self):
        for file in os.listdir("./cogs"):
            if file.endswith(".py"):
                await self.load_extension(f"cogs.{file[:-3]}")
                print(f"📦 Cog cargado: {file}")

    # Evento de unión a un servidor
    async def on_guild_join(self, guild):
        async with self.db.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO guilds (id, name)
                VALUES ($1, $2)
                ON CONFLICT (id) DO NOTHING
                """,
                guild.id, guild.name
            )

bot = MyBot(command_prefix="?", intents=intents)

@bot.event
async def on_ready():
    print(f"🚀 Bot online como {bot.user}")

@bot.event
async def on_command_error(ctx, error):
    print("ERROR:", error)
    await ctx.send(f"Ocurrió un error: {error}")

async def main():
    async with bot:
        await bot.start(TOKEN)

asyncio.run(main())
