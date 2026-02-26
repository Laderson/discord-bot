# services/events/valentine_service.py
import discord


class ValentineService:

    @staticmethod
    async def send_to_role(guild: discord.Guild, role_name: str):

        role = discord.utils.get(guild.roles, name=role_name)

        if not role:
            return 0  # Rol no encontrado

        sent_count = 0

        embed = discord.Embed(
            title="<:77758aestheticbar:1472345210259509413> Feliz San Valentín, familia MVP <:35872heartbow:1472345221881921760>",
            color=discord.Color.from_rgb(255, 105, 180)
        )

        embed.add_field(
            name="\u200b",  # Campo sin título
            value=(
                "<:65597vday:1472345217368723516> Hoy celebramos algo más que una fecha; "
                "celebramos el privilegio de encontrarnos, de coincidir y de seguir construyendo "
                "este espacio que ya sentimos como hogar. Gracias por ser parte de cada risa compartida, "
                "cada charla, cada momento en el que alguien tiende la mano, convierte lo cotidiano "
                "en algo simplemente mágico. <:3670axolotlheart:1472345218631078034>"
            ),
            inline=False
        )

        embed.add_field(
            name="\u200b",
            value=(
                "<:7118heartflower:1472345226696724632> Ustedes son esa chispa que hace que siempre ansiemos volver.\n"
                "El compañerismo que vive aquí no se finge ni se fuerza; nace de la autenticidad de cada uno."
            ),
            inline=False
        )

        embed.add_field(
            name="\u200b",
            value="<:8500heartsearch:1472345225128317021> Todos tienen algo irrepetible que mejora nuestros días.",
            inline=False
        )

        embed.add_field(
            name="\u200b",
            value="“Lo esencial es invisible a los ojos.”\n— Antoine de Saint-Exupéry",
            inline=False
        )

        embed.add_field(
            name="\u200b",
            value=(
                "<:98036heartletter:1472345219856072745> La unión, el apoyo sincero, la amistad que crece sin hacer ruido, "
                "pero que se siente enorme. <a:75435hellokittybooty:1472345215464374373>"
            ),
            inline=False
        )

        embed.add_field(
            name="\u200b",
            value="<:70930aestheticbar:1472345216538378312> Hoy y siempre, esta es y será su casa <:77758aestheticbar:1472345210259509413>",
            inline=False
        )

        embed.set_image(
            url="https://media.giphy.com/media/MDJ9IbxxvDUQM/giphy.gif"
        )

        embed.set_footer(
            text="💖 Comunidad MVP • San Valentín 2026",
            icon_url=guild.icon.url if guild.icon else None
        )



        # 🖼 GIF arriba (puedes cambiar el link si quieres otro)
        embed.set_image(
            url="https://i.imgur.com/eNqrHC2.gif"
        )

        # 🏷 Footer personalizado
        embed.set_footer(
            text="💖 Comunidad MVP • San Valentín 2026",
            icon_url=guild.icon.url if guild.icon else None
        )

        for member in role.members:

            if member.bot:
                continue

            try:
                await member.send(embed=embed)
                sent_count += 1

            except discord.Forbidden:
                continue

            except Exception:
                continue

        return sent_count
