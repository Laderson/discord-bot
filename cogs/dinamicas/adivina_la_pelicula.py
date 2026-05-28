import discord
import random
from discord.ext import commands
from discord import app_commands
import asyncio

from services.ranking_service import add_points

from services.dynamics.pelicula_service import (
    get_questions_pool,
    get_next_question,
    is_correct_answer
)

from services.dynamics.base_service import (
    get_active_dynamic,
    reset_dynamic_participants,
    start_dynamic,
    end_dynamic,
    add_participant,
    add_dynamic_points,
    get_dynamic_participants
)

DYNAMIC_CODE = "GUESS_MOVIE"
START_GIF = "https://i.imgur.com/DO3qmvJ.gif"
END_GIF = "https://i.imgur.com/9mPJDTO.gif"


# -----------------------------
# BOTÓN JOIN
# -----------------------------
class GuessJoinView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="🎟️ Unirse al juego", style=discord.ButtonStyle.success)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):

        if not self.cog.active:
            return await interaction.response.send_message("❌ No hay juego activo", ephemeral=True)

        if not self.cog.join_open:
            return await interaction.response.send_message("🚫 El juego ya comenzó", ephemeral=True)

        participants = await get_dynamic_participants(interaction.guild.id)

        if any(p["user_id"] == interaction.user.id for p in participants):
            return await interaction.response.send_message("⚠️ Ya estás dentro", ephemeral=True)

        await add_participant(interaction.guild.id, interaction.user.id)

        await interaction.response.send_message("✅ Te uniste al juego", ephemeral=True)


class GuessMovieCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.active = False
        self.join_open = False
        self.game_task = None

        self.current_answer = None
        self.guild_id = None

        self.round = 0
        self.max_rounds = 3

        self.winners_this_round = []
        self.answered_users = set()

        self.questions_pool = []


    async def send_live_ranking(self, channel):
        participants = await get_dynamic_participants(self.guild_id)

        if not participants:
            return

        participants = sorted(participants, key=lambda x: x["points"], reverse=True)

        desc = "📊 **Ranking en vivo:**\n\n"

        for i, p in enumerate(participants[:10], 1):
            member = channel.guild.get_member(p["user_id"])
            name = member.display_name if member else "Desconocido"

            desc += f"**{i}.** {name} — {p['points']} pts\n"

        embed = discord.Embed(
            title="📊 Estado del juego",
            description=desc,
            color=discord.Color.orange()
        )

        await channel.send(embed=embed)

    # -----------------------------
    # START
    # -----------------------------
    @app_commands.command(name="start_guess", description="Inicia la dinámica")
    @app_commands.describe(rondas="Cantidad de rondas del juego (1-10)")
    @app_commands.checks.has_permissions(administrator=True)
    async def start_guess(self, interaction: discord.Interaction, rondas: int = 3):

        if self.active:
            return await interaction.response.send_message("⚠️ Ya hay un juego activo", ephemeral=True)

        if rondas < 1 or rondas > 10:
            return await interaction.response.send_message(
                "⚠️ Las rondas deben estar entre 1 y 10",
                ephemeral=True
            )

        await start_dynamic(interaction.guild.id, DYNAMIC_CODE)
        await reset_dynamic_participants(interaction.guild.id)

        self.active = True
        self.join_open = True
        self.guild_id = interaction.guild.id

        self.round = 0
        self.max_rounds = rondas  # 🔥 ahora sí dinámico

        self.questions_pool = get_questions_pool()

        embed = discord.Embed(
            title="🎬 Adivina la Película",
            description=(
                "🎮 **Cómo jugar:**\n"
                "• Presiona el botón para unirte\n"
                "• También puedes responder directamente\n"
                "🏆 **Puntos:**\n"
                "🥇 5 pts | 🥈 3 pts | 🥉 1 pt\n\n"
                "⏳ Usa `/begin_guess` para comenzar"
            ),
            color=discord.Color.purple()
        )

        embed.add_field(
            name="📊 Rondas",
            value=f"{rondas} rondas",
            inline=False
        )

        embed.set_image(url=START_GIF)

        await interaction.response.send_message(embed=embed, view=GuessJoinView(self))

    # -----------------------------
    # BEGIN
    # -----------------------------
    @app_commands.command(name="begin_guess", description="Inicia el juego")
    @app_commands.checks.has_permissions(administrator=True)
    async def begin_guess(self, interaction: discord.Interaction):

        await interaction.response.defer()

        if not self.active:
            return await interaction.followup.send("❌ No hay juego activo", ephemeral=True)

        if not self.join_open:
            return await interaction.followup.send("⚠️ El juego ya inició", ephemeral=True)

        # 🔥 obtener participantes
        participants = await get_dynamic_participants(interaction.guild.id)

        if not participants:
            return await interaction.followup.send(
                "❌ No hay participantes.\nUsa el botón para unirte primero.",
                ephemeral=True
            )

        self.join_open = False

        # 🔥 construir lista bonita
        mentions = []
        for i, p in enumerate(participants, 1):
            member = interaction.guild.get_member(p["user_id"])

            if member:
                mentions.append(f"**{i}.** {member.mention}")
            else:
                mentions.append(f"**{i}.** Usuario desconocido")

        embed = discord.Embed(
            title="🎬 ¡El juego comienza!",
            description=(
                "👥 **Participantes:**\n\n"
                + "\n".join(mentions) +
                "\n\n🔥 ¡Prepárense para la primera ronda!"
            ),
            color=discord.Color.blue()
        )

        await interaction.followup.send(embed=embed)

        # 🚀 iniciar juego
        self.game_task = asyncio.create_task(self.game_loop(interaction.channel))

    # -----------------------------
    # END MANUAL
    # -----------------------------
    @app_commands.command(name="end_guess", description="Finaliza el juego")
    @app_commands.checks.has_permissions(administrator=True)
    async def end_guess(self, interaction: discord.Interaction):

        await interaction.response.defer(ephemeral=True)

        dynamic = await get_active_dynamic(interaction.guild.id)

        if not dynamic or dynamic["code"] != DYNAMIC_CODE:
            return await interaction.followup.send(
                "❌ No hay juego activo"
            )

        if self.game_task and not self.game_task.done():
            self.game_task.cancel()

        self.active = False
        self.join_open = False

        await end_dynamic(interaction.guild.id)

        await interaction.followup.send(
            "🏁 Juego finalizado manualmente"
        )

    # -----------------------------
    # GAME LOOP
    # -----------------------------
    async def game_loop(self, channel):

        try:
            while self.active and self.round < self.max_rounds:

                self.round += 1
                self.winners_this_round = []
                self.answered_users = set()

                question = get_next_question(self.questions_pool)
                if not question:
                    break

                self.current_answer = question["answer"]

                total_time = 20
                remaining_time = total_time

                embed = discord.Embed(
                    title=f"🎬 Ronda {self.round}",
                    color=discord.Color.blue()
                )

                if question["type"] == "text":
                    base_text = f"💬 **{question['question']}**"
                else:
                    base_text = "¿Qué película es?"
                    embed.set_image(url=question["question"])

                embed.description = f"{base_text}\n\n⏳ Tiempo: {remaining_time}s"

                msg = await channel.send(embed=embed)

                while remaining_time > 0 and self.active:

                    await asyncio.sleep(1)
                    remaining_time -= 1

                    if len(self.winners_this_round) >= 3:
                        break

                    if remaining_time == 10:
                        hint = self.generate_hint(self.current_answer, 0.3)
                        embed.clear_fields()
                        embed.add_field(name="💡 Pista", value=f"```{hint}```", inline=False)

                    if remaining_time == 5:
                        hint = self.generate_hint(self.current_answer, 0.6)
                        embed.clear_fields()
                        embed.add_field(name="🔥 Súper pista", value=f"```{hint}```", inline=False)

                    progress = "🟩" * remaining_time + "⬜" * (total_time - remaining_time)

                    embed.description = (
                        f"{base_text}\n\n{progress}\n⏳ Tiempo: {remaining_time}s"
                    )

                    try:
                        await msg.edit(embed=embed)
                    except Exception as e:
                        print("Edit error:", e)

                if not self.winners_this_round and self.active:
                    await channel.send(embed=discord.Embed(
                        title="⏰ Tiempo terminado",
                        description=f"La respuesta era:\n**{self.current_answer}**",
                        color=discord.Color.red()
                    ))

                await asyncio.sleep(2)
                await self.send_live_ranking(channel)

            if self.active:
                await self.end_game(channel)

        except asyncio.CancelledError:
            print("Juego cancelado correctamente")

    # -----------------------------
    # RESPUESTAS
    # -----------------------------
    @commands.Cog.listener()
    async def on_message(self, message):

        if not self.active or not self.current_answer:
            return

        if message.author.bot:
            return

        if not message.guild or message.guild.id != self.guild_id:
            return

        if message.author.id in self.answered_users:
            return

        if len(self.winners_this_round) >= 3:
            return

        if not is_correct_answer(message.content, self.current_answer):
            return

        await add_participant(message.guild.id, message.author.id)

        pos = len(self.winners_this_round)
        points = [5, 3, 1][pos]

        await add_dynamic_points(message.guild.id, message.author.id, points)

        self.winners_this_round.append(message.author.id)
        self.answered_users.add(message.author.id)

        try:
            await message.delete()
        except discord.Forbidden:
            print("No tengo permisos para borrar mensajes")
        except discord.NotFound:
            pass

        await message.channel.send(embed=discord.Embed(
            description=f"🎉 {message.author.mention} acertó\n🏆 **+{points} puntos**",
            color=discord.Color.green()
        ))

    # -----------------------------
    # FINAL
    # -----------------------------
    async def end_game(self, channel):

        self.active = False

        participants = await get_dynamic_participants(self.guild_id)

        embed = discord.Embed(
            title="🏆 Resultados finales",
            color=discord.Color.gold()
        )

        if not participants:
            embed.description = "No hubo participantes."
        else:
            # 🔥 ordenar por puntos de la dinámica
            participants = sorted(participants, key=lambda x: x["points"], reverse=True)

            medals = ["🥇", "🥈", "🥉"]
            rewards = [5, 3, 1]  

            desc = ""
            reward_text = ""

            for i, user in enumerate(participants[:3]):
                user_id = user["user_id"]
                dyn_points = user["points"]

                # 🎯 mostrar puntos de la dinámica
                desc += f"{medals[i]} <@{user_id}> - {dyn_points} pts\n"

                # 🔥 sumar al ranking global
                await add_points(self.guild_id, user_id, rewards[i])

                reward_text += f"{medals[i]} <@{user_id}> +{rewards[i]} pts global\n"

            embed.description = desc

            embed.add_field(
                name="🏆 Recompensas Globales",
                value=reward_text,
                inline=False
            )

        embed.set_image(url=END_GIF)

        await channel.send(embed=embed)

        # 🔥 cerrar dinámica
        await end_dynamic(self.guild_id)

        # 🔄 actualizar ranking
        ranking_cog = self.bot.get_cog("Ranking")
        if ranking_cog:
            await ranking_cog.update_all_rankings()

        # 🧼 reset limpio
        self.current_answer = None
        self.guild_id = None
        self.round = 0
        self.questions_pool = []
        self.game_task = None

    # -----------------------------
    def generate_hint(self, answer: str, reveal_ratio=0.15):
        words = answer.split()
        result = []

        for word in words:
            revealed = max(1, int(len(word) * reveal_ratio))  # 🔥 pocas letras
            indexes = random.sample(range(len(word)), revealed)

            new_word = ""

            for i, char in enumerate(word):
                if i == 0 or i in indexes:
                    new_word += char.upper()
                else:
                    new_word += "_"

            result.append(new_word)

        return "   ".join([" ".join(list(w)) for w in result])


async def setup(bot):
    await bot.add_cog(GuessMovieCog(bot))