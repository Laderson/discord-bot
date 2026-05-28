import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import random

from services.ranking_service import add_points

from services.dynamics.loteria_service import (
    CARDS,
    assign_card_to_user,
    assign_cards_to_all,
    get_participant_card,
    get_card_winners
)

from services.dynamics.base_service import (
    start_dynamic,
    end_dynamic,
    add_participant,
    add_dynamic_points,
    get_dynamic_winner,
    get_active_dynamic,
    is_participant,
    get_dynamic_participants
)

LOTERIA_BANNER_URL = "https://i0.wp.com/salondivertido.com/wp-content/uploads/2022/09/portada-lot-ch.png?fit=480%2C270&ssl=1"

LOTERIA_STATE = {}


def get_card_emoji(guild: discord.Guild, card_name: str):
    formatted = (
        card_name.lower()
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ñ", "n")
        .replace(" ", "_")
    )

    emoji = discord.utils.get(guild.emojis, name=formatted)
    return str(emoji) if emoji else "🎴"


class LoteriaJoinView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="🎟️ Unirse a la Lotería", style=discord.ButtonStyle.success, custom_id="loteria_join")
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):

        state = LOTERIA_STATE.get(interaction.guild.id)

        if not state:
            return await interaction.response.send_message("❌ No hay una lotería activa", ephemeral=True)

        if state["running"]:
            return await interaction.response.send_message("🚫 El canto ya comenzó", ephemeral=True)

        if await is_participant(interaction.guild.id, interaction.user.id):
            return await interaction.response.send_message("⚠️ Ya estás inscrito", ephemeral=True)

        await add_participant(interaction.guild.id, interaction.user.id)

        card = await assign_card_to_user(interaction.guild.id, interaction.user.id)

        embed = discord.Embed(
            title="🎴 Carta asignada",
            description=f"{interaction.user.mention}\n\n{get_card_emoji(interaction.guild, card)} **{card}**",
            color=discord.Color.green()
        )

        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        await interaction.response.send_message(embed=embed, ephemeral=True)


class LoteriaMexicana(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # =========================
    # START (ADMIN)
    # =========================
    @app_commands.command(name="loteria_start")
    @app_commands.checks.has_permissions(administrator=True)
    async def loteria_start(self, interaction: discord.Interaction, rondas: int = 1):

        if await get_active_dynamic(interaction.guild.id):
            return await interaction.response.send_message("❌ Ya hay una dinámica activa", ephemeral=True)

        await start_dynamic(interaction.guild.id, "loteria")

        LOTERIA_STATE[interaction.guild.id] = {
            "total_rounds": rondas,
            "current_round": 1,
            "called_cards": [],
            "deck": [],
            "running": False,
            "task": None
        }

        embed = discord.Embed(
            title="🎴 Lotería Mexicana",
            description=(
                f"🔢 Rondas totales: **{rondas}**\n\n"
                "🎮 **¿Cómo jugar?**\n"
                "• Presiona el botón para unirte\n"
                "• Recibirás una carta automáticamente\n"
                "• Cuando tu carta salga en el canto, usa **/loteria**\n"
                "• El primero en acertar gana la ronda 🎉\n\n"
                "💡 Tu carta se mostrará al unirte y en cada nueva ronda"
            ),
            color=discord.Color.gold()
        )

        embed.set_image(url=LOTERIA_BANNER_URL)

        await interaction.response.send_message(embed=embed, view=LoteriaJoinView(self))

    # =========================
    # TABLA
    # =========================
    async def mostrar_tabla_puntos(self, interaction):
        participants = await get_dynamic_participants(interaction.guild.id)
        if not participants:
            return

        lines = []
        for i, p in enumerate(participants, 1):
            member = interaction.guild.get_member(p["user_id"])
            if member:
                lines.append(f"**{i}.** {member.mention} — 🎯 **{p['points'] or 0} pts**")

        await interaction.channel.send(embed=discord.Embed(
            title="📊 Tabla de Puntos",
            description="\n".join(lines),
            color=discord.Color.purple()
        ))

    # =========================
    # LOOP CANTO
    # =========================
    async def _run_canto(self, interaction):
        state = LOTERIA_STATE.get(interaction.guild.id)

        if not state:
            return

        try:
            for index, card in enumerate(state["deck"], start=1):

                if not state["running"]:
                    break

                state["called_cards"].append(card)

                participants = await get_dynamic_participants(interaction.guild.id)
                winner_ids = await get_card_winners(interaction.guild.id, participants, card)

                winners = []
                for user_id in winner_ids:
                    member = interaction.guild.get_member(user_id)
                    if member:
                        winners.append(member.mention)

                desc = f"**Carta {index}/{len(state['deck'])}**\n\n"
                desc += f"{get_card_emoji(interaction.guild, card)} **{card}**"

                if winners:
                    desc += "\n\n🎯 La tiene:\n" + "\n".join(winners)

                await interaction.channel.send(
                    embed=discord.Embed(description=desc, color=discord.Color.orange())
                )

                await asyncio.sleep(3)

                if not state["running"]:
                    break

        except asyncio.CancelledError:
            return
        finally:
            state["running"] = False

    # =========================
    # CANTAR (ADMIN)
    # =========================
    @app_commands.command(name="loteria_cantar")
    @app_commands.checks.has_permissions(administrator=True)
    async def loteria_cantar(self, interaction: discord.Interaction):

        state = LOTERIA_STATE.get(interaction.guild.id)

        if not state:
            return await interaction.response.send_message("❌ No hay una lotería activa")

        if state["running"]:
            return await interaction.response.send_message("⚠️ Ya está en curso")

        participants = await get_dynamic_participants(interaction.guild.id)
        if not participants:
            return await interaction.response.send_message("❌ No hay participantes")

        state["running"] = True
        state["called_cards"] = []
        state["deck"] = random.sample(CARDS, len(CARDS))

        mentions = []
        for i, p in enumerate(participants, 1):
            member = interaction.guild.get_member(p["user_id"])
            if member:
                mentions.append(f"**{i}.** {member.mention}")

        await interaction.response.send_message(embed=discord.Embed(
            title=f"🎶 Ronda {state['current_round']}",
            description="\n".join(mentions),
            color=discord.Color.blue()
        ))

        task = asyncio.create_task(self._run_canto(interaction))
        state["task"] = task

    # =========================
    # LOTERIA (USERS)
    # =========================
    @app_commands.command(name="loteria")
    async def cantar_loteria(self, interaction: discord.Interaction):

        state = LOTERIA_STATE.get(interaction.guild.id)

        if not state:
            return await interaction.response.send_message("❌ No hay dinámica")

        if not await is_participant(interaction.guild.id, interaction.user.id):
            return await interaction.response.send_message("❌ No participas")

        card = await get_participant_card(interaction.guild.id, interaction.user.id)

        if card not in state["called_cards"]:
            return await interaction.response.send_message("❌ Tu carta no ha salido")

        if state.get("task"):
            state["task"].cancel()

        state["running"] = False

        await add_dynamic_points(interaction.guild.id, interaction.user.id, 1)

        await interaction.response.send_message(embed=discord.Embed(
            title="🎉 ¡LOTERÍA!",
            description=f"{interaction.user.mention}\n{card}",
            color=discord.Color.green()
        ))

        await self.mostrar_tabla_puntos(interaction)

        if state["current_round"] >= state["total_rounds"]:
            winner = await get_dynamic_winner(interaction.guild.id)

            if winner:
                member = interaction.guild.get_member(winner["user_id"])

                if member:
                    # 🏆 Mensaje
                    await interaction.channel.send(f"🏆 Ganador: {member.mention}")

                    # ➕ DAR PUNTOS AL RANKING GLOBAL
                    await add_points(interaction.guild.id, winner["user_id"], 5)

                    # 🔄 ACTUALIZAR RANKINGS
                    ranking_cog = self.bot.get_cog("Ranking")
                    if ranking_cog:
                        await ranking_cog.update_all_rankings()

                    # 🎉 Feedback extra
                    await interaction.channel.send(
                        f"⭐ {member.mention} ganó **+5 puntos** en el ranking global!"
                    )

            await end_dynamic(interaction.guild.id)
            LOTERIA_STATE.pop(interaction.guild.id, None)
            return

        state["current_round"] += 1
        state["called_cards"] = []

        await interaction.channel.send(f"🔄 Ronda {state['current_round']}")

        participants = await get_dynamic_participants(interaction.guild.id)
        await assign_cards_to_all(interaction.guild.id, participants)

        # 📩 Mostrar nuevas cartas (igual que cuando se unen)
        for p in participants:
            member = interaction.guild.get_member(p["user_id"])

            if not member:
                try:
                    member = await interaction.guild.fetch_member(p["user_id"])
                except:
                    continue

            new_card = await get_participant_card(interaction.guild.id, p["user_id"])

            embed = discord.Embed(
                title="🎴 Nueva carta asignada",
                description=f"{member.mention}\n\n{get_card_emoji(interaction.guild, new_card)} **{new_card}**",
                color=discord.Color.green()
            )

            embed.set_thumbnail(url=member.display_avatar.url)

            await interaction.channel.send(embed=embed)

        # 🔄 Reiniciar estado del juego
        state["running"] = True
        state["deck"] = random.sample(CARDS, len(CARDS))

        # ▶️ Volver a cantar automáticamente
        task = asyncio.create_task(self._run_canto(interaction))
        state["task"] = task

    # =========================
    # END (ADMIN)
    # =========================
    @app_commands.command(name="loteria_end")
    @app_commands.checks.has_permissions(administrator=True)
    async def loteria_end(self, interaction: discord.Interaction):

        state = LOTERIA_STATE.get(interaction.guild.id)

        if state and state.get("task"):
            state["task"].cancel()

        await end_dynamic(interaction.guild.id)
        LOTERIA_STATE.pop(interaction.guild.id, None)

        await interaction.response.send_message("🏁 Lotería finalizada")

    # =========================
    # ERROR HANDLER PERMISOS
    # =========================
    @loteria_start.error
    @loteria_cantar.error
    @loteria_end.error
    async def permisos_error(self, interaction: discord.Interaction, error):

        if isinstance(error, app_commands.errors.MissingPermissions):

            if interaction.response.is_done():
                await interaction.followup.send(
                    "🚫 Solo administradores pueden usar este comando",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "🚫 Solo administradores pueden usar este comando",
                    ephemeral=True
                )

async def setup(bot):
    await bot.add_cog(LoteriaMexicana(bot))