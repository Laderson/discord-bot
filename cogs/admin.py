import discord
from discord import app_commands
from discord.ext import commands
from services.dynamics.base_service import get_active_dynamic

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="dynamic_status", description="Verifica si hay una dinámica activa")
    async def dynamic_status(self, interaction: discord.Interaction):

        dynamic = await get_active_dynamic(interaction.guild.id)

        if not dynamic:
            embed = discord.Embed(
                title="📴 Sin dinámica activa",
                description="Actualmente no hay ninguna dinámica en curso.",
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed)

        embed = discord.Embed(
            title="🟢 Dinámica activa",
            description=(
                f"🎮 **Nombre:** {dynamic['name']}\n"
                f"🧩 **Código:** `{dynamic['code']}`"
            ),
            color=discord.Color.green()
        )

        await interaction.response.send_message(embed=embed)

    @commands.command()
    async def ping(self, ctx):
        await ctx.send("Pong 🏓")

async def setup(bot):
    await bot.add_cog(Admin(bot))