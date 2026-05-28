import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Select, Button

from services.shop_service import (
    get_available_products,
    buy_product,
    get_product_by_id
)

TICKET_PANEL_URL = "https://discord.com/channels/1415990627195289612/1417315766482636970/1433229390237667382"


# =========================
# SELECT PERSISTENTE
# =========================
class ShopSelect(Select):
    def __init__(self, cog, products):
        self.cog = cog

        options = [
            discord.SelectOption(
                label=p['name'],
                description=f"Precio: {p['price']} coins",
                value=str(p['id'])
            )
            for p in products
        ]

        super().__init__(
            placeholder="Selecciona un producto...",
            options=options,
            custom_id="shop_select"
        )

    async def callback(self, interaction: discord.Interaction):

        product_id = int(self.values[0])
        user_id = interaction.user.id
        username = interaction.user.display_name
        guild_id = interaction.guild.id

        success, message = await buy_product(
            user_id,
            product_id,
            guild_id
        )

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

            await interaction.response.send_message(
                embed=ticket_embed,
                ephemeral=True
            )

            # Ranking
            ranking_cog = self.cog.bot.get_cog("Ranking")
            if ranking_cog:
                await ranking_cog.update_ranking_message()

            # Notificar admins
            notify = discord.Embed(
                title="🛒 Nueva Compra",
                description=(
                    f"**{username}** compró **{product['name']}** "
                    f"por {product['price']} coins ✅\n"
                    f"{product['description']}"
                ),
                color=discord.Color.gold()
            )

            for member in interaction.guild.members:
                if member.guild_permissions.administrator:
                    try:
                        await member.send(embed=notify)
                    except discord.Forbidden:
                        pass

        else:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=message,
                    color=discord.Color.red()
                ),
                ephemeral=True
            )


# =========================
# VIEW PERSISTENTE
# =========================
class ShopView(View):
    def __init__(self, cog, page_index: int, pages):
        super().__init__(timeout=None)
        self.cog = cog
        self.page_index = page_index
        self.pages = pages

        self.add_buttons()

    def add_buttons(self):

        if self.page_index > 0:
            prev = Button(
                label="Anterior",
                style=discord.ButtonStyle.secondary,
                custom_id=f"shop_prev_{self.page_index}"
            )

            async def prev_callback(interaction: discord.Interaction):
                await self.cog.send_page(
                    interaction,
                    self.page_index - 1,
                    self.pages,
                    edit=True
                )

            prev.callback = prev_callback
            self.add_item(prev)

        if self.page_index < len(self.pages) - 1:
            next_btn = Button(
                label="Siguiente",
                style=discord.ButtonStyle.secondary,
                custom_id=f"shop_next_{self.page_index}"
            )

            async def next_callback(interaction: discord.Interaction):
                await self.cog.send_page(
                    interaction,
                    self.page_index + 1,
                    self.pages,
                    edit=True
                )

            next_btn.callback = next_callback
            self.add_item(next_btn)


# =========================
# COG
# =========================
class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def send_page(self, interaction, page_index, pages, edit=False):

        page_titles = ["🌟 Comunidad", "🏠 Servidor", "🔍 Detalles"]

        embed = discord.Embed(
            title="🌟 Tienda MVP",
            color=discord.Color.dark_purple()
        )

        embed.set_footer(text=f"Página {page_index + 1}/{len(pages)}")
        embed.set_thumbnail(
            url="https://images3.memedroid.com/images/UPLOADED738/63ad8328dd7a1.jpeg"
        )

        view = ShopView(self, page_index, pages)

        # ===== PRODUCTOS =====
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
                view.add_item(ShopSelect(self, page_products))

        # ===== DETALLES =====
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

        if edit:
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            await interaction.response.send_message(embed=embed, view=view)

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

        await self.send_page(interaction, 0, pages)


# =========================
# SETUP
# =========================
async def setup(bot):
    cog = Shop(bot)
    await bot.add_cog(cog)

    # 🔥 REGISTRO DE VIEW PERSISTENTE
    bot.add_view(ShopView(cog, 0, []))