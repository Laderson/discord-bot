# cogs/ranking.py
from enum import member

import discord
from discord.ext import commands, tasks
from datetime import datetime
from discord import app_commands
from services.ranking_service import (
    get_top_weekly,
    get_top_monthly,
    get_total_users,
    get_top_coins,
    get_user_points,
    remove_points
)

RANKING_CHANNEL_ID = 1461258291916308541

TOP_MESSAGE_ID = 1490487617991737354
COINS_MESSAGE_ID = 1490487638610804876


class Ranking(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.auto_update_ranking.start()

    def cog_unload(self):
        self.auto_update_ranking.cancel()

    # ================== LOOP ==================
    @tasks.loop(minutes=3)
    async def auto_update_ranking(self):
        print("⏰ Actualizando rankings...")

        try:
            await self.update_top_message()
            print("✅ TOP actualizado")
        except Exception as e:
            print(f"❌ Error TOP: {e}")

        try:
            await self.update_coins_message()
            print("✅ COINS actualizado")
        except Exception as e:
            print(f"❌ Error COINS: {e}")

    @auto_update_ranking.before_loop
    async def before_auto_update(self):
        await self.bot.wait_until_ready()

    @auto_update_ranking.error
    async def auto_update_error(self, error):
        print(f"🔥 ERROR LOOP: {error}")

    # ================== SLASH COMMAND TOP ==================
    @app_commands.command(name="top", description="Ver rankings del servidor")
    async def top(self, interaction: discord.Interaction):
        embed = await self.build_top_embed(interaction.guild)
        await interaction.response.send_message(embed=embed)

    # ================== SLASH COMMAND COINS ==================
    @app_commands.command(name="topcoins", description="Ver ranking de coins")
    async def topcoins(self, interaction: discord.Interaction):
        embed = await self.build_topcoins_embed(interaction.guild)
        await interaction.response.send_message(embed=embed)

    # ================== /REMOVEPOINTS (ADMIN) ==================
    @app_commands.command(
        name="removepoints",
        description="Quitar puntos a un usuario del ranking"
    )
    @app_commands.checks.has_permissions(administrator=False)
    @app_commands.describe(
        member="Usuario al que se le quitarán puntos",
        amount="Cantidad de puntos a quitar",
        reason="Razón del retiro"
    )
    async def removepoints(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        amount: int,
        reason: str = "Sin especificar"
    ):
        from services.ranking_service import remove_points

        if amount <= 0:
            await interaction.response.send_message(
                "❌ La cantidad debe ser mayor a 0.",
                ephemeral=True
            )
            return

        # Quitar los puntos usando el service
        await remove_points(interaction.guild.id, member.id, amount)

        # Obtener puntos actuales
        current_points = await get_user_points(interaction.guild.id, member.id)

        embed = discord.Embed(
            title="➖ Retiro de Puntos",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(name="👤 Usuario", value=member.mention, inline=False)
        embed.add_field(name="⭐ Puntos retirados", value=str(amount), inline=True)
        embed.add_field(
            name="📊 Total actual",
            value=f"Semanal: `{current_points['weekly_points']}` | Mensual: `{current_points['monthly_points']}`",
            inline=True
        )
        embed.add_field(name="📌 Razón", value=reason, inline=False)
        embed.add_field(name="🏦 Retirado por", value=interaction.user.mention, inline=False)

        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="Sistema de ranking • Puntos")

        await interaction.response.send_message(embed=embed)

        # 🔄 Actualizar ranking
        ranking_cog = self.bot.get_cog("Ranking")
        if ranking_cog:
            await ranking_cog.update_all_rankings()

    # ================== EMBED TOP ==================
    async def build_top_embed(self, guild: discord.Guild):
        guild_id = guild.id

        top_weekly = await get_top_weekly(guild_id)
        top_monthly = await get_top_monthly(guild_id)
        total_users = await get_total_users(guild_id)

        embed = discord.Embed(
            title="🏆 Rankings del Servidor",
            description=f"Servidor: **{guild.name}**",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
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
                lines.append(f"{medal(i)} **{name}** — `{points} pts`")

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

        embed.set_footer(text=f"Usuarios en ranking: {total_users}")
        return embed

    # ================== EMBED COINS ==================
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

    # ================== UPDATE TOP ==================
    async def update_top_message(self):
        channel = self.bot.get_channel(RANKING_CHANNEL_ID)
        if not channel:
            print("❌ Canal TOP no encontrado")
            return

        try:
            message = await channel.fetch_message(TOP_MESSAGE_ID)
        except discord.NotFound:
            print("❌ Mensaje TOP no encontrado")
            return

        embed = await self.build_top_embed(channel.guild)
        await message.edit(embed=embed)

    # ================== UPDATE COINS ==================
    async def update_coins_message(self):
        channel = self.bot.get_channel(RANKING_CHANNEL_ID)
        if not channel:
            print("❌ Canal COINS no encontrado")
            return

        try:
            message = await channel.fetch_message(COINS_MESSAGE_ID)
        except discord.NotFound:
            print("❌ Mensaje COINS no encontrado")
            return

        embed = await self.build_topcoins_embed(channel.guild)
        await message.edit(embed=embed)

    # ================== UPDATE GLOBAL ==================
    async def update_all_rankings(self):
        await self.update_top_message()
        await self.update_coins_message()


async def setup(bot):
    await bot.add_cog(Ranking(bot))