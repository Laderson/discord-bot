# cogs/emoji_game.py

import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import random

from services.dynamics.base_service import (
    start_dynamic,
    end_dynamic,
    add_participant,
    get_dynamic_participants,
    is_participant,
    get_active_dynamic
)

from services.dynamics.emoji_service import EMOJI_GAME_STATE

from services.dynamics.emoji_service import (
    next_round,
    end_emoji_game,
    add_user_choice,
    get_winners
)

from services.ranking_service import add_points


# ---------------------------
# ESTADO ÚNICO EN MEMORIA
# ---------------------------

AVAILABLE_EMOJIS = ["🐾", "🦋", "🏆", "🎨"]


# ---------------------------
# VIEW JOIN
# ---------------------------
class EmojiJoinView(discord.ui.View):
    def __init__(self, cog, guild_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.guild_id = guild_id
        self.message = None

    @discord.ui.button(label="🎨 Unirse a la dinámica", style=discord.ButtonStyle.green)
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):

        state = EMOJI_GAME_STATE.get(self.guild_id)

        # 🔴 BLOQUEO FUERTE
        if state.get("running", False) or state.get("current_round", 1) > 1:
            return await interaction.response.send_message(
                "🚫 No puedes unirte, la partida ya comenzó.",
                ephemeral=True
            )

        if not state:
            return await interaction.response.send_message("❌ No hay dinámica activa", ephemeral=True)

        if state["running"]:
            return await interaction.response.send_message("🚫 La dinámica ya comenzó", ephemeral=True)

        if await is_participant(self.guild_id, interaction.user.id):
            return await interaction.response.send_message("⚠️ Ya estás inscrito", ephemeral=True)

        await add_participant(self.guild_id, interaction.user.id)

        if interaction.user.id in state["participants"]:
            return await interaction.response.send_message(
                "⚠️ Ya estás dentro.",
                ephemeral=True
            )

        state["participants"].append(interaction.user.id)

        # Confirmación tipo lotería
        embed = discord.Embed(
            title="✅ Te uniste",
            description=f"{interaction.user.mention} ahora participa 🎉",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        await interaction.response.send_message(embed=embed, ephemeral=True)

        # Actualizar lista
        mentions = [f"<@{uid}>" for uid in state["participants"]]

        new_embed = discord.Embed(
            title="🎨 Dinámica de Emojis",
            description=(
                "🎮 **¿Cómo jugar?**\n"
                "• Presiona **Unirse** para participar\n"
                "• En cada ronda aparecerán varios emojis\n"
                "• Reacciona con **UNO** de ellos\n"
                "• Si aciertas un emoji ganador, ganas puntos\n\n"
                "🏆 **Sistema de puntos:**\n"
                "🥇 Mejor emoji → más puntos\n"
                "🥈 Segundo → puntos medios\n"
                "🥉 Tercero → puntos bajos\n\n"
                "📊 Al final:\n"
                "Los 3 mejores reciben puntos globales\n\n"
                "👇 **Únete ahora**\n\n"
                "👥 Participantes:"
            ),
            color=discord.Color.purple()
        )

        new_embed.set_image(url="https://media.giphy.com/media/3o7aD2saalBwwftBIY/giphy.gif")

        if self.message:
            await self.message.edit(embed=new_embed)


# ---------------------------
# COG
# ---------------------------
class EmojiGame(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_messages = {}

    # =========================
    # START
    # =========================
    @app_commands.command(name="start_emoji", description="Crear dinámica de emojis")
    @app_commands.checks.has_permissions(administrator=True)
    async def start_game(self, interaction: discord.Interaction):

        active = await get_active_dynamic(interaction.guild.id)

        if active:
            return await interaction.response.send_message(
                f"❌ Ya hay una dinámica activa: **{active['name']}**",
                ephemeral=True
            )

        guild_id = interaction.guild.id

        await start_dynamic(guild_id, "EMOJI_GAME")

        EMOJI_GAME_STATE[guild_id] = {
            "total_rounds": 10,
            "current_round": 1,
            "running": False,
            "participants": [],
            "choices": {},
            "participants_points": {}
        }

        embed = discord.Embed(
            title="🎨 Dinámica de Emojis",
            description=(
                "🎮 **¿Cómo jugar?**\n"
                "• Presiona **Unirse** para participar\n"
                "• En cada ronda aparecerán varios emojis\n"
                "• Reacciona con **UNO** de ellos\n"
                "• Si aciertas un emoji ganador, ganas puntos\n\n"
                "🏆 **Sistema de puntos:**\n"
                "🥇 Mejor emoji → más puntos\n"
                "🥈 Segundo → puntos medios\n"
                "🥉 Tercero → puntos bajos\n\n"
                "📊 Al final:\n"
                "Los 3 mejores reciben puntos globales\n\n"
                "👇 **Únete ahora**\n\n"
                "👥 Participantes:"
            ),
            color=discord.Color.purple()
        )

        embed.set_image(url="https://media.giphy.com/media/3o7aD2saalBwwftBIY/giphy.gif")

        view = EmojiJoinView(self, guild_id)
        msg = await interaction.channel.send(embed=embed, view=view)

        view.message = msg

        await interaction.response.send_message("✅ Dinámica creada", ephemeral=True)

    # =========================
    # BEGIN
    # =========================
    @app_commands.command(name="begin_emoji", description="Iniciar juego")
    async def begin_emoji(self, interaction: discord.Interaction):

        guild_id = interaction.guild.id
        state = EMOJI_GAME_STATE.get(guild_id)

        if not state:
            return await interaction.response.send_message("❌ No hay dinámica creada", ephemeral=True)

        if state["running"]:
            return await interaction.response.send_message("⚠️ Ya inició", ephemeral=True)

        if not state["participants"]:
            return await interaction.response.send_message("❌ No hay participantes", ephemeral=True)

        state["running"] = True

        # 🔒 Desactivar botones visualmente
        for view in self.bot.persistent_views:
            if isinstance(view, EmojiJoinView) and view.guild_id == guild_id:
                for item in view.children:
                    item.disabled = True
                if view.message:
                    await view.message.edit(view=view)

        await interaction.response.send_message("🚀 ¡Comienza el juego!")

        asyncio.create_task(self.game_loop(interaction.channel, guild_id))

    # =========================
    # LOOP
    # =========================
    async def game_loop(self, channel, guild_id):

        state = EMOJI_GAME_STATE.get(guild_id)

        while state and state["running"] and state["current_round"] <= state["total_rounds"]:

            rnd = state["current_round"]
            total = state["total_rounds"]

            # 📊 Barra de progreso de rondas
            progress = int((rnd / total) * 10)
            progress_bar = "🟩" * progress + "⬜" * (10 - progress)

            embed = discord.Embed(
                title=f"🎨 Ronda {rnd}/{total}",
                description=(
                    f"📊 Progreso:\n{progress_bar}\n\n"
                    f"Reacciona con un emoji:\n{' '.join(AVAILABLE_EMOJIS)}\n\n"
                    f"⏳ Tiempo restante: **5s**"
                ),
                color=discord.Color.blue()
            )

            msg = await channel.send(embed=embed)
            self.active_messages[guild_id] = msg.id

            for emoji in AVAILABLE_EMOJIS:
                await msg.add_reaction(emoji)

            # ⏳ CONTADOR VISUAL
            for t in [4, 3, 2, 1]:
                await asyncio.sleep(1)

                embed.description = (
                    f"📊 Progreso:\n{progress_bar}\n\n"
                    f"Reacciona con un emoji:\n{' '.join(AVAILABLE_EMOJIS)}\n\n"
                    f"⏳ Tiempo restante: **{t}s**"
                )

                try:
                    await msg.edit(embed=embed)
                except:
                    pass

            await asyncio.sleep(1)

            await self.end_round(channel, guild_id)

            state = EMOJI_GAME_STATE.get(guild_id)
            if not state:
                break

    # =========================
    # END ROUND
    # =========================
    async def end_round(self, channel, guild_id):

        state = EMOJI_GAME_STATE.get(guild_id)

        if not state:
            return

        if not state.get("choices"):
            await channel.send("❌ Nadie eligió emoji en esta ronda")
            state["current_round"] += 1
            return

        # 🎯 Obtener ganadores (ahora maneja 3 emojis internamente)
        winners = get_winners(guild_id)

        winning_emojis = state.get("winning_emojis", [])

        medals = ["🥇", "🥈", "🥉"]

        emojis_text = ""
        for i, emoji in enumerate(winning_emojis):
            emojis_text += f"{medals[i]} {emoji}\n"

        embed = discord.Embed(
            title=f"🏆 Ronda {state['current_round']}",
            description=f"🎯 Emojis ganadores:\n{emojis_text or 'Sin emojis'}",
            color=discord.Color.gold()
        )

        if not winners:
            embed.add_field(name="Resultado", value="Nadie acertó 😢", inline=False)
        else:
            desc = ""

            for w in winners:
                user = channel.guild.get_member(w["user_id"])

                if user:
                    # ⚠️ ya no sumamos puntos aquí (ya se hace en el service)
                    desc += f"{user.mention} +{w['points']} pts\n"

            embed.add_field(name="Ganadores", value=desc, inline=False)

        await channel.send(embed=embed)

        # 📊 Ranking
        ranking = sorted(state["participants_points"].items(), key=lambda x: x[1], reverse=True)

        ranking_text = ""
        for i, (uid, pts) in enumerate(ranking, 1):
            user = channel.guild.get_member(uid)
            if user:
                ranking_text += f"{i}. {user.display_name} — {pts} pts\n"

        await channel.send(embed=discord.Embed(
            title="📊 Ranking",
            description=ranking_text or "Sin puntos aún",
            color=discord.Color.orange()
        ))

        # 🧹 limpiar elecciones
        state["choices"] = {}

        # ⏭️ siguiente ronda
        state["current_round"] += 1

        if state["current_round"] > state["total_rounds"]:
            await self.end_game(channel, guild_id)



    @app_commands.command(name="end_emoji", description="Finaliza la dinámica de emojis")
    @app_commands.checks.has_permissions(administrator=True)
    async def end_emoji_command(self, interaction: discord.Interaction):

        await interaction.response.defer(ephemeral=True)

        guild_id = interaction.guild.id
        state = EMOJI_GAME_STATE.get(guild_id)

        try:
            # 🧯 Cerrar DB SIEMPRE primero (rápido)
            await end_dynamic(guild_id)

            if not state:
                return await interaction.followup.send(
                    "⚠️ No había dinámica en memoria, pero se cerró en la BD.",
                    ephemeral=True
                )

            # 🛑 detener loop
            state["running"] = False

            # ⚡ RESPONDER RÁPIDO (IMPORTANTE)
            await interaction.followup.send(
                "⏳ Cerrando dinámica...",
                ephemeral=True
            )

            # =========================
            # TODO LO PESADO DESPUÉS
            # =========================

            ranking = sorted(
                state["participants_points"].items(),
                key=lambda x: x[1],
                reverse=True
            )

            if ranking:
                desc = ""

                for i, (uid, pts) in enumerate(ranking, 1):
                    user = interaction.guild.get_member(uid)

                    if not user:
                        continue

                    desc += f"{i}. {user.mention} — {pts} pts\n"

                    # 🏆 BONUS TOP 3 (protegido)
                    if i <= 3:
                        try:
                            await add_points(guild_id, uid, [5, 3, 1][i - 1])
                        except Exception as e:
                            print(f"[ERROR add_points] {e}")

                await interaction.channel.send(embed=discord.Embed(
                    title="🏁 Dinámica finalizada",
                    description=desc,
                    color=discord.Color.red()
                ))
            else:
                await interaction.channel.send("⚠️ La dinámica terminó sin participantes.")

            # 🧠 limpieza final
            await end_emoji_game(guild_id)

            EMOJI_GAME_STATE.pop(guild_id, None)
            self.active_messages.pop(guild_id, None)

        except Exception as e:
            print(f"[ERROR end_emoji] {e}")

            try:
                await end_dynamic(guild_id)
            except:
                pass

            if interaction.response.is_done():
                await interaction.followup.send(
                    "❌ Error al cerrar la dinámica.",
                    ephemeral=True
                )

    # =========================
    # REACCIONES
    # =========================

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):

        if user.bot:
            return

        guild_id = reaction.message.guild.id
        state = EMOJI_GAME_STATE.get(guild_id)

        if not state:
            return

        # 🔒 SOLO MENSAJE ACTIVO
        if self.active_messages.get(guild_id) != reaction.message.id:
            return

        # 🔒 SOLO EMOJIS VÁLIDOS
        if str(reaction.emoji) not in AVAILABLE_EMOJIS:
            await reaction.message.remove_reaction(reaction.emoji, user)
            return

        # 🔥 FILTRO CLAVE (ESTO ES LO QUE TE FALTABA)
        if user.id not in state["participants"]:
            await reaction.message.remove_reaction(reaction.emoji, user)

            try:
                await user.send("🚫 Debes unirte a la dinámica antes de participar.")
            except:
                pass

            return

        # ✅ REGISTRAR ELECCIÓN
        add_user_choice(guild_id, user.id, str(reaction.emoji))

        # Quitar reacción para evitar múltiples elecciones
        await reaction.message.remove_reaction(reaction.emoji, user)

    # =========================
    # END GAME
    # =========================
    async def end_game(self, channel, guild_id):

        state = EMOJI_GAME_STATE.get(guild_id)

        if not state:
            return

        ranking = sorted(
            state["participants_points"].items(),
            key=lambda x: x[1],
            reverse=True
        )

        medals = ["🥇", "🥈", "🥉"]
        rewards = [5, 3, 1]

        desc = ""
        rewards_text = ""

        top_user = None

        for i, (uid, pts) in enumerate(ranking, 1):
            user = channel.guild.get_member(uid)

            if not user:
                continue

            medal = medals[i-1] if i <= 3 else "🔹"

            desc += f"{medal} {user.mention} — **{pts} pts**\n"

            # 🎯 guardar top 1
            if i == 1:
                top_user = user

            # 🏆 puntos globales
            if i <= 3:
                await add_points(guild_id, uid, rewards[i - 1])
                rewards_text += f"{medals[i-1]} {user.mention} +{rewards[i-1]} pts global\n"

        # 🎨 EMBED FINAL
        embed = discord.Embed(
            title="🏁 ¡Juego terminado!",
            description=desc or "Sin resultados",
            color=discord.Color.gold()
        )

        if rewards_text:
            embed.add_field(
                name="🏆 Recompensas Globales",
                value=rewards_text,
                inline=False
            )

        # 🥇 Imagen del ganador
        if top_user:
            embed.set_thumbnail(url=top_user.display_avatar.url)
            embed.set_footer(text=f"Ganador: {top_user.display_name} 🏆")

        embed.set_image(url="https://media.giphy.com/media/l3vRlT2k2L35Cnn5C/giphy.gif")

        await channel.send(embed=embed)

        # LIMPIEZA TOTAL
        await end_emoji_game(guild_id)
        await end_dynamic(guild_id)

        EMOJI_GAME_STATE.pop(guild_id, None)
        self.active_messages.pop(guild_id, None)


# ---------------------------
# SETUP
# ---------------------------
async def setup(bot):
    await bot.add_cog(EmojiGame(bot))