# cogs/ranking.py
import discord
from datetime import datetime
from discord.ext import commands
from discord import app_commands
from services.ranking_service import (
    get_top_weekly,
    get_top_monthly,
    get_total_users,
    get_top_coins
)

RANKING_CHANNEL_ID = 1461258291916308541
RANKING_MESSAGE_ID = 1471664822109077567


class Ranking(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ================== SLASH COMMAND TOP ==================
    @app_commands.command(name="top", description="Ver rankings del servidor")
    async def top(self, interaction: discord.Interaction):

        guild = interaction.guild
        guild_id = guild.id

        top_weekly = await get_top_weekly(guild_id)
        top_monthly = await get_top_monthly(guild_id)
        total_users = await get_total_users(guild_id)

        embed = discord.Embed(
            title="🏆 Rankings del Servidor",
            description=f"Servidor: **{guild.name}**",
            color=discord.Color.gold()
        )

        def medal(i):
            return "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}️⃣"

        def build(top_list, key):
            if not top_list:
                return "No hay datos"
            lines = []
            for i, user in enumerate(top_list, start=1):
                member = guild.get_member(user["user_id"])
                name = member.display_name if member else f"Usuario ({user['user_id']})"
                points = user[key]
                lines.append(f"{medal(i)} {name} — {points} pts")
            return "\n".join(lines)

        embed.add_field(
            name="🌟 Top Semanal",
            value=build(top_weekly, "weekly_points"),
            inline=False
        )

        embed.add_field(
            name="🌙 Top Mensual",
            value=build(top_monthly, "monthly_points"),
            inline=False
        )

        embed.set_footer(text=f"Total de usuarios en ranking: {total_users}")

        await interaction.response.send_message(embed=embed)

    # ================== SLASH COMMAND TOPCOINS ==================
    @app_commands.command(name="topcoins", description="Ver ranking de coins del servidor")
    async def topcoins(self, interaction: discord.Interaction):

        embed = await self.build_topcoins_embed(interaction.guild)
        await interaction.response.send_message(embed=embed)

    # ================== EMBED FIJO DE TOP COINS ==================
    async def build_topcoins_embed(self, guild: discord.Guild):
        top = await get_top_coins(guild.id)

        embed = discord.Embed(
            title="💰 Top Coins",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )

        if not top:
            embed.description = "No hay usuarios con coins aún."
            return embed

        medals = ["🥇", "🥈", "🥉"]
        lines = []

        for i, user in enumerate(top):
            member = guild.get_member(user["user_id"])
            name = member.display_name if member else f"Usuario ({user['user_id']})"
            medal = medals[i] if i < 3 else f"{i+1}️⃣"
            lines.append(f"{medal} **{name}** — `{user['balance']} coins`")

        embed.description = "\n".join(lines)

        embed.add_field(
            name="📌 Información",
            value=(
                f"👥 Usuarios en ranking: **{len(top)}**\n"
                f"🏠 Servidor: **{guild.name}**"
            ),
            inline=False
        )

        embed.set_footer(text="Sistema de economía • Coins")
        return embed

    # ================== ACTUALIZAR MENSAJE FIJO ==================
    async def update_ranking_message(self):
        channel = self.bot.get_channel(RANKING_CHANNEL_ID)
        if not channel:
            return

        try:
            message = await channel.fetch_message(RANKING_MESSAGE_ID)
        except discord.NotFound:
            return

        embed = await self.build_topcoins_embed(channel.guild)
        await message.edit(embed=embed)


async def setup(bot):
    await bot.add_cog(Ranking(bot))
