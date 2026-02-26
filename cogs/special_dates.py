# cogs/special_dates_cog.py
import discord
from discord import app_commands
from discord.ext import commands

from services.events.valentine_service import ValentineService


class SpecialDatesCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="evento",
        description="Envía mensaje interno de San Valentín a un rol específico."
    )
    @app_commands.describe(rol="Selecciona el rol que recibirá el mensaje")
    async def evento(
        self,
        interaction: discord.Interaction,
        rol: discord.Role
    ):

        # 🔒 Verificar admin
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ Solo administradores pueden usar este comando.",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        # Enviar mensaje al rol seleccionado
        enviados = await ValentineService.send_to_role(
            interaction.guild,
            rol.name
        )

        await interaction.followup.send(
            f"✅ Evento ejecutado correctamente.\n\n"
            f"🎯 Rol: **{rol.name}**\n"
            f"📩 Mensajes enviados: **{enviados}**",
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(SpecialDatesCog(bot))
