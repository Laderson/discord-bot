# cogs/shop.py
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Select, Button
from services.shop_service import get_available_products, buy_product, get_product_by_id

ADMIN_ID = [1336868688430895175, 1383299653637898241]
TICKET_PANEL_URL = "https://discord.com/channels/1415990627195289612/1417315766482636970/1433229390237667382"


class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="tienda", description="Abre la tienda MVP")
    async def tienda(self, interaction: discord.Interaction):

        products = await get_available_products()
        if not products:
            await interaction.response.send_message(
                "La tienda está vacía 😢",
                ephemeral=True
            )
            return

        pages = [
            [p for p in products if p['category'] == 'comunidad'],
            [p for p in products if p['category'] == 'servidor'],
            "DETALLES"
        ]

        page_titles = ["🌟 Comunidad", "🏠 Servidor", "🔍 Detalles"]

        async def send_page(page_index: int, edit_interaction=None):

            embed = discord.Embed(
                title="🌟 Tienda MVP",
                color=discord.Color.dark_purple()
            )

            embed.set_footer(text=f"Página {page_index + 1}/{len(pages)}")
            embed.set_thumbnail(
                url="https://images3.memedroid.com/images/UPLOADED738/63ad8328dd7a1.jpeg"
            )

            view = View(timeout=None)

            # ===== PÁGINAS DE PRODUCTOS =====
            if page_index in (0, 1):

                embed.description = "¡Selecciona un producto para canjear tus coins! 💎"

                embed.set_image(
                    url="https://i.imgur.com/oLLBfyN.jpeg"
                    if page_index == 0
                    else "https://i.imgur.com/0iGnfQZ.jpeg"
                )

                page_products = pages[page_index]
                text = ""

                for p in page_products:
                    text += (
                        f"🛒 **{p['name']}** — 💰 {p['price']}\n"
                        f"✨ {p['description']}\n\n"
                    )

                embed.add_field(
                    name=page_titles[page_index],
                    value=text or "No hay productos",
                    inline=False
                )

                if page_products:
                    options = [
                        discord.SelectOption(
                            label=p['name'],
                            description=f"Precio: {p['price']} coins",
                            value=str(p['id'])
                        ) for p in page_products
                    ]

                    select = Select(
                        placeholder="Selecciona un producto...",
                        options=options
                    )

                    async def select_callback(select_interaction: discord.Interaction):

                        product_id = int(select.values[0])
                        user_id = select_interaction.user.id
                        username = select_interaction.user.display_name
                        guild_id = select_interaction.guild.id  # ⚡ usar el guild correcto

                        success, message = await buy_product(user_id, product_id, guild_id)

                        if success:

                            product = await get_product_by_id(product_id)

                            ticket_embed = discord.Embed(
                                title="🎫 Ticket de Compra",
                                description=(
                                    "Tu compra fue registrada correctamente ✅\n\n"
                                    "**Siguiente paso:**\n"
                                    "👉 Abre un ticket usando el panel oficial\n"
                                    "Un banquero verificará tu compra."
                                ),
                                color=discord.Color.blurple()
                            )

                            ticket_embed.add_field(
                                name="🛒 Producto",
                                value=f"**{product['name']}**\n💰 {product['price']} coins",
                                inline=False
                            )

                            ticket_embed.add_field(
                                name="📩 Abrir ticket",
                                value=f"[Haz clic aquí para abrir tu ticket]({TICKET_PANEL_URL})",
                                inline=False
                            )

                            ticket_embed.set_footer(
                                text="Sistema de compras • Tienda MVP"
                            )

                            await select_interaction.response.send_message(
                                embed=ticket_embed,
                                ephemeral=True
                            )

                            # 🔄 Actualizar ranking
                            ranking_cog = self.bot.get_cog("Ranking")
                            if ranking_cog:
                                await ranking_cog.update_ranking_message()

                            # 📩 Notificar a todos los admins
                            notify = discord.Embed(
                                title="🛒 Nueva Compra",
                                description=(
                                    f"**{username}** compró **{product['name']}** "
                                    f"por {product['price']} coins ✅\n"
                                    f"{product['description']}"
                                ),
                                color=discord.Color.gold()
                            )

                            for admin_id in ADMIN_ID:
                                try:
                                    admin = await self.bot.fetch_user(admin_id)
                                    if admin:
                                        await admin.send(embed=notify)
                                except Exception:
                                    pass

                        else:
                            await select_interaction.response.send_message(
                                embed=discord.Embed(
                                    description=message,
                                    color=discord.Color.red
                                ),
                                ephemeral=True
                            )

                    select.callback = select_callback
                    view.add_item(select)

            # ===== PÁGINA DETALLES =====
            else:

                embed.set_image(url="https://i.imgur.com/o3g27t8.jpeg")

                embed.add_field(
                    name="📌 Información primordial",
                    value=(
                        "• Los roles personalizados deben mantenerse con **actividad**.\n"
                        "• Al salir del servidor se revocan **roles, permisos y coins**.\n"
                        "• Canales privados inactivos serán **eliminados**.\n"
                        "• Reinicia Discord (CTRL + R) para resetear selecciones.\n"
                        "• Roles personalizados duran **toda la temática**."
                    ),
                    inline=False
                )

                embed.add_field(
                    name="❓ Preguntas frecuentes",
                    value=(
                        "**¿Cómo canjear un ítem?**\n"
                        "1️⃣ Selecciona el ítem\n"
                        "2️⃣ Se crea un ticket\n"
                        "3️⃣ Un banquero verifica\n"
                        "4️⃣ ¡Disfruta tu compra!\n\n"
                        "**¿Puedo perder coins?** Sí."
                    ),
                    inline=False
                )

                embed.add_field(
                    name="⚠️ Penalizaciones",
                    value=(
                        "• Sanción: **3 coins**\n"
                        "• Reducción 2h: **20 coins**\n"
                        "• Reducción 1h: **10 coins**\n"
                        "• Reducción 30m: **5 coins**"
                    ),
                    inline=False
                )

            # ===== BOTONES =====
            if page_index > 0:
                async def prev_callback(btn_interaction: discord.Interaction):
                    await send_page(page_index - 1, btn_interaction)

                prev = Button(label="Anterior", style=discord.ButtonStyle.secondary)
                prev.callback = prev_callback
                view.add_item(prev)

            if page_index < len(pages) - 1:
                async def next_callback(btn_interaction: discord.Interaction):
                    await send_page(page_index + 1, btn_interaction)

                next_btn = Button(label="Siguiente", style=discord.ButtonStyle.secondary)
                next_btn.callback = next_callback
                view.add_item(next_btn)

            if edit_interaction:
                await edit_interaction.response.edit_message(embed=embed, view=view)
            else:
                await interaction.response.send_message(embed=embed, view=view)

        await send_page(0)


async def setup(bot):
    await bot.add_cog(Shop(bot))
