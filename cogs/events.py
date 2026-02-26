import discord
from discord.ext import commands

from services.dynamics.rounds_service import (
    add_points,
    advance_round,
    clear_event,
    finish_rounds,
    get_active_round,
    get_table,
    remove_points,
    start_rounds
)
from services.event_service import is_event_active, stop_event


class Events(commands.Cog, name="Events"):
    def __init__(self, bot):
        self.bot = bot

    # ==============================
    # INICIAR DINÁMICA
    # ==============================
    @commands.command(name="Dinamyc")
    async def iniciar(self, ctx, rondas: int):
        if await is_event_active(ctx.guild.id):
            return await ctx.send("❌ Ya hay una dinámica activa.")

        await start_rounds(ctx.guild.id, rondas)

        await ctx.send(
            f"🎮 **Dinámica iniciada**\n"
            f"🔢 Total de rondas: **{rondas}**"
        )


    # ==============================
    # DAR PUNTOS
    # ==============================
    @commands.command(name="givepoints")
    async def dar_puntos(self, ctx, member: discord.Member, puntos: int):
        config = await get_active_round(ctx.guild.id)

        if not config:
            return await ctx.send("❌ No hay ninguna dinámica activa.")

        current_round = config["current_round"]
        total_rounds = config["total_rounds"]

        if current_round > total_rounds:
            await finish_rounds(ctx.guild.id)
            return await ctx.send("🏁 La dinámica ya terminó.")

        await add_points(ctx.guild.id, member.id, puntos)
        await advance_round(ctx.guild.id)

        if current_round + 1 > total_rounds:
            await finish_rounds(ctx.guild.id)
            await ctx.send("🏁 **Última ronda completada. Dinámica finalizada.**")
        else:
            await ctx.send(
                f"✅ {member.mention} ganó **{puntos} puntos**\n"
                f"🔢 Ronda **{current_round}/{total_rounds}**"
            )



    # ==============================
    # QUITAR PUNTOS
    # ==============================
    @commands.command(name="quitarpuntos")
    async def quitar_puntos(self, ctx, member: discord.Member, puntos: int):
        await remove_points(ctx.guild.id, member.id, puntos)
        await ctx.send(f"➖ {puntos} puntos retirados a {member.mention}")

    # ==============================
    # TABLA
    # ==============================
    @commands.command(name="tabla")
    async def tabla(self, ctx):
        rows = await get_table(ctx.guild.id)

        if not rows:
            return await ctx.send("No hay puntos aún.")

        text = ""
        for i, r in enumerate(rows, start=1):
            user = ctx.guild.get_member(r["user_id"])
            name = user.display_name if user else "Usuario desconocido"
            text += f"**{i}.** {name} — {r['points']} pts\n"

        embed = discord.Embed(
            title="📊 Tabla de la Dinámica",
            description=text,
            color=discord.Color.blurple()
        )
        embed.set_image(url="https://i.imgur.com/0iGnfQZ.jpeg")

        await ctx.send(embed=embed)

    # ==============================
    # CANCELAR
    # ==============================
    @commands.command(name="cancelardinamica")
    async def cancelar(self, ctx):
        await clear_event(ctx.guild.id)
        await stop_event(ctx.guild.id)

        await ctx.send("❌ Dinámica cancelada.")

    # ==============================
    # FINALIZAR
    # ==============================
    @commands.command(name="finalizardinamica")
    async def finalizar(self, ctx):
        await stop_event(ctx.guild.id)

        embed = discord.Embed(
            title="🏁 Dinámica Finalizada",
            description="Los puntos han sido registrados.",
            color=discord.Color.red()
        )
        embed.set_image(url="https://i.imgur.com/o3g27t8.jpeg")

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Events(bot))
