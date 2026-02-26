# cogs/economy.py
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
from services.economy_service import EconomyService


class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ADMINS = [1383299653637898241, 836076392244445194]  # IDs permitidos

    # ================== /BALANCE ==================
    @app_commands.command(name="balance", description="Ver tu balance de coins")
    async def balance(self, interaction: discord.Interaction):

        await EconomyService.ensure_user(interaction.user.id, str(interaction.user))
        await EconomyService.ensure_guild(interaction.guild.id, interaction.guild.name)

        balance = await EconomyService.get_balance(
            interaction.user.id,
            interaction.guild.id
        )

        embed = discord.Embed(
            title="💰 Tu Balance",
            description=f"Tienes **{balance} coins**",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )

        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text="Sistema de economía • Coins")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ================== /GIVECOINS ==================
    @app_commands.command(name="givecoins", description="Dar coins a un usuario")
    @app_commands.describe(
        member="Usuario que recibirá coins",
        amount="Cantidad de coins",
        reason="Razón de la entrega"
    )
    async def givecoins(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        amount: int,
        reason: str = "Sin especificar"
    ):

        if interaction.user.id not in self.ADMINS:
            await interaction.response.send_message(
                "❌ No tienes permisos para usar este comando.",
                ephemeral=True
            )
            return

        if amount <= 0:
            await interaction.response.send_message(
                "❌ La cantidad debe ser mayor a 0.",
                ephemeral=True
            )
            return

        await EconomyService.ensure_user(member.id, str(member))
        await EconomyService.ensure_guild(interaction.guild.id, interaction.guild.name)

        await EconomyService.add_balance_to_user(
            member.id,
            interaction.guild.id,
            amount
        )

        new_balance = await EconomyService.get_balance(
            member.id,
            interaction.guild.id
        )

        embed = discord.Embed(
            title="💰 Entrega de Coins",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(name="👤 Usuario", value=member.mention, inline=False)
        embed.add_field(name="💵 Cantidad", value=str(amount), inline=True)
        embed.add_field(name="📊 Total actual", value=str(new_balance), inline=True)
        embed.add_field(name="📌 Razón", value=reason, inline=False)
        embed.add_field(name="🏦 Entregado por", value=interaction.user.mention, inline=False)

        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="Sistema de economía • Coins")

        await interaction.response.send_message(embed=embed)

        # 🔄 Actualizar ranking
        ranking_cog = self.bot.get_cog("Ranking")
        if ranking_cog:
            await ranking_cog.update_ranking_message()

    # ================== /REMOVECOINS ==================
    @app_commands.command(name="removecoins", description="Quitar coins a un usuario")
    @app_commands.describe(
        member="Usuario al que se le quitarán coins",
        amount="Cantidad a retirar",
        reason="Razón del retiro"
    )
    async def removecoins(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        amount: int,
        reason: str = "Sin especificar"
    ):

        if interaction.user.id not in self.ADMINS:
            await interaction.response.send_message(
                "❌ No tienes permisos para usar este comando.",
                ephemeral=True
            )
            return

        if amount <= 0:
            await interaction.response.send_message(
                "❌ La cantidad debe ser mayor a 0.",
                ephemeral=True
            )
            return

        await EconomyService.ensure_user(member.id, str(member))
        await EconomyService.ensure_guild(interaction.guild.id, interaction.guild.name)

        current_balance = await EconomyService.get_balance(
            member.id,
            interaction.guild.id
        )

        if current_balance < amount:
            await interaction.response.send_message(
                f"❌ {member.display_name} no tiene suficientes coins.\n"
                f"Balance actual: **{current_balance} coins**",
                ephemeral=True
            )
            return

        await EconomyService.add_balance_to_user(
            member.id,
            interaction.guild.id,
            -amount
        )

        new_balance = await EconomyService.get_balance(
            member.id,
            interaction.guild.id
        )

        embed = discord.Embed(
            title="➖ Retiro de Coins",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(name="👤 Usuario", value=member.mention, inline=False)
        embed.add_field(name="💵 Cantidad retirada", value=str(amount), inline=True)
        embed.add_field(name="📊 Total actual", value=str(new_balance), inline=True)
        embed.add_field(name="📌 Razón", value=reason, inline=False)
        embed.add_field(name="🏦 Retirado por", value=interaction.user.mention, inline=False)

        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="Sistema de economía • Coins")

        await interaction.response.send_message(embed=embed)

        # 🔄 Actualizar ranking
        ranking_cog = self.bot.get_cog("Ranking")
        if ranking_cog:
            await ranking_cog.update_ranking_message()

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message(
                "❌ Solo administradores pueden usar este comando.",
                ephemeral=True
            )



async def setup(bot):
    await bot.add_cog(Economy(bot))
