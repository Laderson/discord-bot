import asyncio

import discord
from discord import state
from discord.ext import commands
from discord import app_commands

from services.dynamics.base_service import (
    add_dynamic_points,
    start_dynamic,
    end_dynamic,
    get_active_dynamic,
    add_participant,
    get_dynamic_participants,
    reset_dynamic_participants
)

from services.dynamics.hangman_service import (
    get_random_word,
    create_progress,
    render_progress,
    get_hangman
)
from services.ranking_service import add_points

DYNAMIC_CODE = "HANGMAN"

START_GIF = "https://media.tenor.com/2roX3uxz_68AAAAC/hangman.gif"


# -----------------------------
# VIEW
# -----------------------------
class HangmanJoinView(discord.ui.View):

    def __init__(self, cog):
        super().__init__(timeout=None)
        self.guild_id = None
        self.cog = cog  

    @discord.ui.button(
        label="🎟️ Unirse al juego",
        style=discord.ButtonStyle.success
    )
    async def join(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        # verificar dinámica activa en BD
        dynamic = await get_active_dynamic(interaction.guild.id)

        if not dynamic or dynamic["code"] != DYNAMIC_CODE:
            return await interaction.response.send_message(
                "❌ No hay un ahorcado activo",
                ephemeral=True
            )

        participants = await get_dynamic_participants(interaction.guild.id)

        if any(p["user_id"] == interaction.user.id for p in participants):
            return await interaction.response.send_message(
                "⚠️ Ya estás dentro",
                ephemeral=True
            )

        await add_participant(
            interaction.guild.id,
            interaction.user.id
        )

        await interaction.response.send_message(
            "✅ Te uniste al Ahorcado",
            ephemeral=True
        )


# -----------------------------
# COG
# -----------------------------
class HangmanCog(commands.Cog):

    def __init__(self, bot):
        self.round = 0
        self.max_rounds = 3
        self.bot = bot
        self.player_states = {}
        self.started = False
        self.guild_id = None
        self.round_winners = []

    # -----------------------------
    # START
    # -----------------------------
    @app_commands.command(
        name="start_hangman",
        description="Inicia el lobby del ahorcado"
    )
    @app_commands.describe(
        rondas="Cantidad de rondas"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def start_hangman(
        self,
        interaction: discord.Interaction,
        rondas: int = 3
    ):

        await interaction.response.defer()

        # verificar si ya hay dinámica activa
        dynamic = await get_active_dynamic(interaction.guild.id)

        if dynamic:
            return await interaction.followup.send(
                f"⚠️ Ya hay una dinámica activa: **{dynamic['name']}**",
                ephemeral=True
            )
        
        if rondas < 1 or rondas > 20:
            return await interaction.followup.send(
                "⚠️ Las rondas deben ser entre 1 y 20",
                ephemeral=True
            )
        
        # iniciar dinámica
        await start_dynamic(
            interaction.guild.id,
            DYNAMIC_CODE
        )

        self.started = False
        self.guild_id = interaction.guild.id

        self.round = 0
        self.max_rounds = rondas

        # limpiar participantes anteriores
        await reset_dynamic_participants(
            interaction.guild.id
        )

        embed = discord.Embed(
            title="🪓 EL AHORCADO HA COMENZADO",
            description=(
                "```ansi\n"
                "\u001b[2;31mSobrevive más rondas que los demás...\u001b[0m\n"
                "```\n"
                "🎟️ Pulsa el botón para entrar.\n"
                "💀 Cada jugador tendrá su propio destino.\n"
                "🏆 Solo los mejores sobrevivirán.\n\n"
                f"🔥 Rondas: **{rondas}**"
            ),
            color=discord.Color.dark_red()
        )

        embed.set_footer(
            text="Presiona el botón verde para unirte"
        )

        # OPCIONAL:
        # comenta esto temporalmente para probar
        embed.set_image(url=START_GIF)

        await interaction.followup.send(
            embed=embed,
            view=HangmanJoinView(self)
        )

    # -----------------------------
    # START ROUND
    # -----------------------------
    async def start_round(self, channel):
        self.round_winners = []
        self.round += 1

        embed = discord.Embed(
            title=f"🩸 ROUND {self.round}/{self.max_rounds}",
            description=(
                "━━━━━━━━━━━━━━━━━━\n"
                "🪓 Nuevas palabras fueron asignadas.\n"
                "⌛ Tienen una oportunidad para sobrevivir.\n"
                "━━━━━━━━━━━━━━━━━━"
            ),
            color=discord.Color.red()
        )

        embed.set_thumbnail(
            url="https://cdn-icons-png.flaticon.com/512/616/616494.png"
        )

        await channel.send(embed=embed)
        await channel.send(
            "⏳ Tienen una nueva palabra.\n"
            "Usen `/guess letra` para jugar."
        )

        # 🔥 reset de jugadores vivos
        for user_id, state in self.player_states.items():

            if state["dead"]:
                continue

            word = get_random_word()

            state["word"] = word
            state["progress"] = create_progress(word)
            state["used_letters"] = []
            state["errors"] = 0
            state["won"] = False

            member = channel.guild.get_member(user_id)

            if not member:
                continue

            progress = render_progress(
                state["progress"]
            )

            player_embed = discord.Embed(
                title=f"🪓 {member.display_name}",
                description=(
                    f"```{get_hangman(0)}```\n"
                    f"```{progress}```\n\n"
                    f"❌ Errores: 0/6"
                ),
                color=discord.Color.orange()
            )

            # borrar mensaje anterior
            try:
                if state["message_id"]:

                    old_msg = await channel.fetch_message(
                        state["message_id"]
                    )

                    await old_msg.delete()

            except Exception as e:
                print(f"Error eliminando mensaje: {e}")

            # crear nuevo tablero
            msg = await channel.send(
                embed=player_embed
            )

            state["message_id"] = msg.id

            # cancelar timer anterior
            if state["timer_task"]:
                state["timer_task"].cancel()

            state["timer_start"] = asyncio.get_event_loop().time()

            # iniciar timer nuevo
            state["timer_task"] = asyncio.create_task(
                self.player_timer(channel, user_id)
            )
            

    # -----------------------------
    # END
    # -----------------------------
    @app_commands.command(
        name="end_hangman",
        description="Finaliza el ahorcado"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def end_hangman(
        self,
        interaction: discord.Interaction
    ):

        dynamic = await get_active_dynamic(interaction.guild.id)

        if not dynamic or dynamic["code"] != DYNAMIC_CODE:
            return await interaction.response.send_message(
                "❌ No hay un ahorcado activo",
                ephemeral=True
            )

        await end_dynamic(interaction.guild.id)

        await interaction.response.send_message(
            "🏁 El ahorcado terminó"
        )

    async def player_timer(self, channel, user_id):

        state = self.player_states.get(user_id)

        if not state:
            return
        
        if state["active_timer"]:
            return

        try:
            state["active_timer"] = True

            for remaining in range(15, 0, -1):

                # jugador muerto o ganó
                if state["dead"] or state["won"]:
                    return

                progress = render_progress(
                    state["progress"]
                )

                member = channel.guild.get_member(user_id)

                if not member:
                    return

                embed = discord.Embed(
                    title=f"🪓 {member.display_name}",
                    description=(
                        f"```{get_hangman(state['errors'])}```\n"
                        f"```{progress}```\n\n"
                        f"❤️ Vidas restantes: "
                        f"**{6 - state['errors']}**\n"

                        f"❌ Errores: "
                        f"**{state['errors']}/6**\n\n"

                        f"📚 Letras usadas:\n"
                        f"`{' '.join(state['used_letters']) if state['used_letters'] else 'Ninguna'}`\n\n"

                        f"⏰ Tiempo restante: "
                        f"**{remaining}s**"
                    ),
                    color=discord.Color.orange()
                )

                try:

                    msg = await channel.fetch_message(
                        state["message_id"]
                    )

                    await msg.edit(embed=embed)

                except Exception as e:
                    print(f"Error editando mensaje: {e}")

                await asyncio.sleep(1)

            state["active_timer"] = False

        except asyncio.CancelledError:
            state["active_timer"] = False
            return

        # --------------------------------
        # TIEMPO AGOTADO
        # --------------------------------

        state["errors"] += 1

        member = channel.guild.get_member(user_id)

        if not member:
            return

        # murió
        if state["errors"] >= 6:

            state["dead"] = True
            state["active_timer"] = False

            if state["timer_task"]:
                state["timer_task"].cancel()

            embed = discord.Embed(
                title="⏰ Tiempo agotado",
                description=(
                    f"{member.mention} no respondió a tiempo.\n\n"
                    f"```{get_hangman(6)}```\n"
                    f"La palabra era:\n"
                    f"**{state['word'].upper()}**"
                ),
                color=discord.Color.red()
            )

        else:

            progress = render_progress(
                state["progress"]
            )

            embed = discord.Embed(
                title=f"⏰ {member.display_name}",
                description=(
                    f"```{get_hangman(state['errors'])}```\n"
                    f"```{progress}```\n\n"
                    f"❌ Perdió una vida por tardar más de 15 segundos"
                ),
                color=discord.Color.red()
            )

        try:

            msg = await channel.fetch_message(
                state["message_id"]
            )

            await msg.edit(embed=embed)

        except Exception as e:
            print(f"Error editando mensaje: {e}")

        await self.check_game_end(channel)

        # reiniciar timer si sigue vivo
        if not state["dead"] and not state["won"]:

            state["timer_task"] = asyncio.create_task(
                self.player_timer(channel, user_id)
            )


    # -----------------------------
    # CHECK ROUND END
    # -----------------------------
    async def check_game_end(self, channel):

        alive_players = []
        unfinished_players = []

        for user_id, state in self.player_states.items():

            # ☠️ ignorar muertos
            if state["dead"]:
                continue

            alive_players.append(user_id)

            # 🔥 sigue jugando ronda
            if not state["won"]:
                unfinished_players.append(user_id)

        # ☠️ todos muertos
        if not alive_players:

            return await self.finish_game(
                channel,
                []
            )

        # 🏆 solo queda uno vivo
        if len(alive_players) == 1:

            return await self.finish_game(
                channel,
                alive_players
            )

        # ✅ ronda terminada
        if not unfinished_players:

            await self.send_live_ranking(channel)

            await asyncio.sleep(5)

            # 🔥 max rounds
            if self.round >= self.max_rounds:

                return await self.finish_game(
                    channel,
                    alive_players
                )

            # 🚀 siguiente ronda
            await self.start_round(channel)

    # -----------------------------
    # BEGIN
    # -----------------------------
    @app_commands.command(
        name="begin_hangman",
        description="Comienza la partida de ahorcado"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def begin_hangman(
        self,
        interaction: discord.Interaction
    ):
    
        
        await interaction.response.defer()

        dynamic = await get_active_dynamic(interaction.guild.id)

        if not dynamic or dynamic["code"] != DYNAMIC_CODE:
            return await interaction.followup.send(
                "❌ No hay un ahorcado activo",
                ephemeral=True
            )

        if self.started:
            return await interaction.followup.send(
                "⚠️ El juego ya comenzó",
                ephemeral=True
            )

        participants = await get_dynamic_participants(
            interaction.guild.id
        )

        if not participants:
            return await interaction.followup.send(
                "❌ No hay participantes",
                ephemeral=True
            )

        self.started = True

        # 🔥 crear estado individual
        self.player_states = {}

        player_list = []

        for p in participants:

            user_id = p["user_id"]

            word = get_random_word()

            self.player_states[user_id] = {
                "word": word,
                "progress": create_progress(word),
                "used_letters": [],
                "errors": 0,
                "dead": False,
                "message_id": None,
                "timer_task": None,
                "active_timer": False,
                "won": False
                
            }

            member = interaction.guild.get_member(user_id)

            if member:
                player_list.append(f"• {member.mention}")

        embed = discord.Embed(
            title="💀 Ahorcado iniciado",
            description=(
                "🎮 El juego comenzó\n\n"
                "👥 Participantes:\n"
                + "\n".join(player_list)
            ),
            color=discord.Color.red()
        )

        await interaction.followup.send(embed=embed)

        await self.start_round(interaction.channel)

    # -----------------------------
    # GUESS
    # -----------------------------
    @app_commands.command(
        name="guess",
        description="Adivina una letra"
    )
    @app_commands.describe(
        letra="Letra a probar"
    )
    async def guess(
        self,
        interaction: discord.Interaction,
        letra: str
    ):

        await interaction.response.defer(ephemeral=True)

        dynamic = await get_active_dynamic(interaction.guild.id)

        if not dynamic or dynamic["code"] != DYNAMIC_CODE:
            return await interaction.followup.send(
                "❌ No hay un ahorcado activo"
            )

        if not self.started:
            return await interaction.followup.send(
                "⚠️ El juego no comenzó"
            )

        state = self.player_states.get(interaction.user.id)

        if not state:
            return await interaction.followup.send(
                "❌ No estás participando"
            )

        if state["dead"]:
            return await interaction.followup.send(
                "☠️ Ya estás eliminado"
            )

        if state["won"]:
            return await interaction.followup.send(
                "🏆 Ya completaste esta ronda"
            )

        # -----------------------------
        # REINICIAR TIMER
        # -----------------------------
        if state["timer_task"]:
            state["timer_task"].cancel()

        state["active_timer"] = False

        state["timer_task"] = asyncio.create_task(
            self.player_timer(
                interaction.channel,
                interaction.user.id
            )
        )

        letra = letra.lower().strip()

        if len(letra) != 1:
            return await interaction.followup.send(
                "⚠️ Solo puedes usar UNA letra"
            )

        if letra in state["used_letters"]:
            msg = await interaction.followup.send(
                "⚠️ Ya usaste esa letra",
                wait=True
            )

            await asyncio.sleep(1)

            await msg.delete()

            return

        state["used_letters"].append(letra)

        word = state["word"]

        # -----------------------------
        # LETRA CORRECTA
        # -----------------------------
        if letra in word:

            await add_dynamic_points(
                interaction.guild.id,
                interaction.user.id,
                1
            )

            for i, char in enumerate(word):

                if char == letra:
                    state["progress"][i] = letra.upper()

            # -----------------------------
            # VICTORIA
            # -----------------------------
            if "_" not in state["progress"]:

                await add_dynamic_points(
                    interaction.guild.id,
                    interaction.user.id,
                    5
                )

                bonus_text = ""
                bonus_reward = ""

                if not self.round_winners:

                    await add_dynamic_points(
                        interaction.guild.id,
                        interaction.user.id,
                        2
                    )

                    bonus_text = "\n🥇 Primer ganador: +2 pts bonus"
                    bonus_reward = "• +2 pts primer ganador\n"

                self.round_winners.append(
                    interaction.user.id
                )

                state["won"] = True
                state["active_timer"] = False

                if state["timer_task"]:
                    state["timer_task"].cancel()

                embed = discord.Embed(
                    title="🏆 PALABRA COMPLETADA",
                    description=(
                        f"🎉 <@{interaction.user.id}> logró sobrevivir.\n\n"
                        f"🔤 Palabra:\n"
                        f"```{word.upper()}```\n"
                        f"💰 Recompensas:\n"
                        f"• +5 pts palabra\n"
                        f"{bonus_reward}"
                    ),
                    color=discord.Color.green()
                )

                try:

                    msg = await interaction.channel.fetch_message(
                        state["message_id"]
                    )

                    await msg.edit(embed=embed)

                except Exception as e:
                    print(f"Error editando mensaje: {e}")

                await self.check_game_end(
                    interaction.channel
                )

                msg = await interaction.followup.send(
                    f"🎉 ¡Completaste la palabra!"
                    f"\n🏆 +5 pts"
                    f"{bonus_text}",
                    wait=True
                )

                await asyncio.sleep(1)

                await msg.delete()

                return

        # -----------------------------
        # LETRA INCORRECTA
        # -----------------------------
        else:

            state["errors"] += 1

            # -----------------------------
            # MUERTE
            # -----------------------------
            if state["errors"] >= 6:

                state["dead"] = True
                state["active_timer"] = False

                if state["timer_task"]:
                    state["timer_task"].cancel()

                embed = discord.Embed(
                    title="☠️ Has muerto",
                    description=(
                        f"```ansi\n"
                        f"{get_hangman(6)}\n"
                        f"```\n\n"
                        f"La palabra era:\n"
                        f"**{word.upper()}**"
                    ),
                    color=discord.Color.red()
                )

                try:

                    msg = await interaction.channel.fetch_message(
                        state["message_id"]
                    )

                    await msg.edit(embed=embed)

                except Exception as e:
                    print(f"Error editando mensaje: {e}")

                await self.check_game_end(
                    interaction.channel
                )

                msg = await interaction.followup.send(
                    "☠️ Has sido eliminado",
                    wait=True
                )

                await asyncio.sleep(1)

                await msg.delete()

                return

        # -----------------------------
        # ACTUALIZAR TABLERO
        # -----------------------------
        progress = render_progress(
            state["progress"]
        )

        embed = discord.Embed(
            title=f"🪓 {interaction.user.display_name}",
            description=(
                f"```ansi\n"
                f"{get_hangman(state['errors'])}\n"
                f"```\n"
                f"🔤 Palabra:\n"
                f"```{progress}```\n"
                f"❤️ Vidas restantes: "
                f"**{6 - state['errors']}**\n"
                f"❌ Errores: "
                f"**{state['errors']}/6**\n\n"
                f"📚 Letras usadas:\n"
                f"`{' '.join(state['used_letters']) if state['used_letters'] else 'Ninguna'}`"
            ),
            color=discord.Color.orange()
        )

        embed.set_footer(
            text="Usa /guess <letra>"
        )

        try:

            msg = await interaction.channel.fetch_message(
                state["message_id"]
            )

            await msg.edit(embed=embed)

        except Exception as e:
            print(f"Error editando mensaje: {e}")

        msg = await interaction.followup.send(
            "✅ Letra procesada",
            wait=True
        )

        await asyncio.sleep(1)

        await msg.delete()

    # -----------------------------
    # LIVE RANKING
    # -----------------------------
    async def send_live_ranking(self, channel):

        participants = await get_dynamic_participants(
            self.guild_id
        )

        if not participants:
            return

        participants = sorted(
            participants,
            key=lambda x: x["points"],
            reverse=True
        )

        desc = ""

        medals = ["🥇", "🥈", "🥉"]

        for i, p in enumerate(participants[:10]):

            member = channel.guild.get_member(
                p["user_id"]
            )

            if not member:
                continue

            medal = medals[i] if i < 3 else "🏅"

            desc += (
                f"{medal} "
                f"{member.mention} "
                f"- {p['points']} pts\n"
            )

        embed = discord.Embed(
            title="📊 Ranking Actual",
            description=desc,
            color=discord.Color.gold()
        )

        await channel.send(embed=embed)


    # -----------------------------
    # FINISH GAME
    # -----------------------------
    async def finish_game(self, channel, winners):

        embed = discord.Embed(
            title="👑 FIN DEL AHORCADO",
            description=(
                "━━━━━━━━━━━━━━━━━━\n"
                "💀 La dinámica terminó.\n"
                "🏆 Estos fueron los supervivientes.\n"
                "━━━━━━━━━━━━━━━━━━"
            ),
            color=discord.Color.gold()
        )

        if winners:

            desc = ""

            rewards = [10, 5, 3]

            for i, user_id in enumerate(winners[:3]):

                reward = rewards[i]

                desc += (
                    f"🏅 <@{user_id}> "
                    f"+{reward} pts global\n"
                )

                # 🔥 ranking global
                await add_points(
                    self.guild_id,
                    user_id,
                    reward
                )

            participants = await get_dynamic_participants(
                self.guild_id
            )

            participants = sorted(
                participants,
                key=lambda x: x["points"],
                reverse=True
            )

            ranking_text = ""

            for i, p in enumerate(participants[:10], 1):

                ranking_text += (
                    f"**{i}.** <@{p['user_id']}> "
                    f"- {p['points']} pts\n"
                )

            embed.add_field(
                name="🎖️ Recompensas Globales",
                value=desc,
                inline=False
            )

            embed.add_field(
                name="📊 Ranking Final",
                value=ranking_text,
                inline=False
            )

        else:

            embed.description = (
                "☠️ Nadie logró sobrevivir."
            )

        await channel.send(embed=embed)

        # 🔥 cerrar dinámica
        await end_dynamic(self.guild_id)

        # cancelar todos los timers
        for state in self.player_states.values():

            if state["timer_task"]:
                state["timer_task"].cancel()

        # 🔥 reset
        self.started = False
        self.player_states = {}
        self.round = 0
        self.guild_id = None
        self.round_winners = []


async def setup(bot):
    await bot.add_cog(HangmanCog(bot))