import discord
from discord.ext import commands
from discord import app_commands
import random
from datetime import datetime
import time
import asyncio
import json
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

start_time = time.time()

def charger_warns():
    try:
        with open("warns.json", "r", encoding="utf-8") as fichier:
            return json.load(fichier)
    except FileNotFoundError:
        return {}


def sauvegarder_warns():
    with open("warns.json", "w", encoding="utf-8") as fichier:
        json.dump(warns, fichier, indent=4, ensure_ascii=False)


warns = charger_warns()

def charger_config():
    try:
        with open("config.json", "r", encoding="utf-8") as fichier:
            return json.load(fichier)
    except FileNotFoundError:
        return {}


def sauvegarder_config():
    with open("config.json", "w", encoding="utf-8") as fichier:
        json.dump(config, fichier, indent=4, ensure_ascii=False)


config = charger_config()

async def envoyer_panels_tickets():
    global config
    config = charger_config()

    for guild in bot.guilds:
        guild_id = str(guild.id)
        guild_config = config.get(guild_id, {})
        tickets_config = guild_config.get("tickets", {})

        if not tickets_config.get("enabled"):
            continue

        message_channel_id = tickets_config.get("message_channel_id", "")
        button_label = tickets_config.get("button_label", "Ouvrir un ticket")

        if not message_channel_id:
            continue

        try:
            channel = guild.get_channel(int(message_channel_id))
        except ValueError:
            continue

        if channel is None:
            continue

        embed = discord.Embed(
           title="🎫 Besoin d’aide ?",
           description=(
               "Clique sur le bouton ci-dessous pour contacter le staff.\n\n"
               "📌 **Comment ça marche ?**\n"
               "Un salon privé sera créé entre toi et le staff."
           ),
           color=0xd96b1c
        )

        embed.set_footer(text="Bovi • Système de tickets")

        view = TicketPanelView(button_label)

        old_message_id = tickets_config.get("panel_message_id")

        if old_message_id:
            try:
                old_message = await channel.fetch_message(int(old_message_id))
                await old_message.edit(embed=embed, view=view)
                continue
            except:
                pass

        message = await channel.send(embed=embed, view=view)

        config[guild_id]["tickets"]["panel_message_id"] = str(message.id)
        sauvegarder_config()


class TicketPanelView(discord.ui.View):
    def __init__(self, button_label="Ouvrir un ticket"):
        super().__init__(timeout=None)

        self.add_item(
            discord.ui.Button(
                label=button_label,
                emoji="🎫",
                style=discord.ButtonStyle.primary,
                custom_id="bovi_open_ticket"
            )
        )


class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(
            discord.ui.Button(
                label="Fermer le ticket",
                emoji="🔒",
                style=discord.ButtonStyle.danger,
                custom_id="bovi_close_ticket"
            )
        )


@bot.event
async def on_interaction(interaction: discord.Interaction):
    global config

    if interaction.type != discord.InteractionType.component:
        return

    custom_id = interaction.data.get("custom_id")

    if custom_id == "bovi_open_ticket":
        config = charger_config()

        guild = interaction.guild
        member = interaction.user
        guild_id = str(guild.id)

        guild_config = config.get(guild_id, {})
        tickets_config = guild_config.get("tickets", {})

        if not tickets_config.get("enabled"):
            await interaction.response.send_message(
                "❌ Les tickets ne sont pas activés sur ce serveur.",
                ephemeral=True
            )
            return

        category_id = tickets_config.get("category_id", "")
        staff_role_id = tickets_config.get("staff_role_id", "")
        open_message = tickets_config.get(
            "open_message",
            "Explique ton problème, le staff va te répondre bientôt."
        )

        if not category_id:
            await interaction.response.send_message(
                "❌ Aucune catégorie de tickets n’est configurée.",
                ephemeral=True
            )
            return

        try:
            category = guild.get_channel(int(category_id))
        except ValueError:
            category = None

        if category is None:
            await interaction.response.send_message(
                "❌ La catégorie de tickets est introuvable.",
                ephemeral=True
            )
            return

        existing_channel = discord.utils.get(
            guild.text_channels,
            name=f"ticket-{member.name.lower()}"
        )

        if existing_channel:
            await interaction.response.send_message(
                f"❌ Tu as déjà un ticket ouvert : {existing_channel.mention}",
                ephemeral=True
            )
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True
            )
        }

        staff_role_ids = tickets_config.get("staff_role_ids", [])

        if not staff_role_ids and tickets_config.get("staff_role_id"):
            staff_role_ids = [tickets_config.get("staff_role_id")]

        for staff_role_id in staff_role_ids:
            try:
                staff_role = guild.get_role(int(staff_role_id))

                if staff_role:
                    overwrites[staff_role] = discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=True,
                        read_message_history=True,
                        manage_channels=True
                    )

            except ValueError:
                pass

        ticket_channel = await guild.create_text_channel(
            name=f"ticket-{member.name}",
            category=category,
            overwrites=overwrites,
            reason="Création d'un ticket avec Bovi"
        )

        embed = discord.Embed(
            title="🎫 Ticket ouvert",
            description=f"{member.mention}, {open_message}",
            color=0xd96b1c
        )

        embed.set_footer(text="Bovi • Ticket")

        await ticket_channel.send(
            content=member.mention,
            embed=embed,
            view=CloseTicketView()
        )

        await interaction.response.send_message(
            f"✅ Ton ticket a été créé : {ticket_channel.mention}",
            ephemeral=True
        )

    elif custom_id == "bovi_close_ticket":
        channel = interaction.channel

        if not channel.name.startswith("ticket-"):
            await interaction.response.send_message(
                "❌ Ce salon n’est pas un ticket.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "🔒 Fermeture du ticket dans 5 secondes...",
            ephemeral=True
        )

        await asyncio.sleep(5)
        await channel.delete(reason="Ticket fermé avec Bovi")

@bot.event
async def on_ready():
    print(f"{bot.user} est connecté !")

    bot.add_view(TicketPanelView())
    bot.add_view(CloseTicketView())

    await envoyer_panels_tickets()

    activity = discord.Activity(
        type=discord.ActivityType.watching,
        name="Utilise /aide"
    )
    await bot.change_presence(activity=activity)

@bot.event
async def on_member_join(member):
    global config
    config = charger_config()

    guild_id = str(member.guild.id)

    if guild_id not in config:
        return

    guild_config = config[guild_id]

    # =========================
    # RÔLE AUTOMATIQUE
    # =========================
    autorole_config = guild_config.get("autorole", {})
    autorole_enabled = autorole_config.get("enabled", False)
    role_id = autorole_config.get("role_id", "")

    if autorole_enabled and role_id:
        try:
            role = member.guild.get_role(int(role_id))

            if role:
                await member.add_roles(role)
            else:
                print("Rôle automatique introuvable.")

        except discord.Forbidden:
            print("Bovi n'a pas la permission de donner ce rôle.")
        except discord.HTTPException:
            print("Erreur Discord lors de l'ajout du rôle.")
        except ValueError:
            print("ID du rôle automatique invalide.")

    # =========================
    # MESSAGE DE BIENVENUE
    # =========================
    welcome_config = guild_config.get("welcome", {})
    welcome_enabled = welcome_config.get("enabled", False)
    welcome_channel_id = welcome_config.get("channel_id", "")

    # Ancien système avec /setwelcome
    old_welcome_channel = guild_config.get("welcome_channel")

    channel_id = welcome_channel_id or old_welcome_channel

    if not welcome_enabled and not old_welcome_channel:
        return

    if not channel_id:
        return

    try:
        channel = member.guild.get_channel(int(channel_id))
    except ValueError:
        print("ID du salon bienvenue invalide.")
        return

    if channel is None:
        return

    embed = discord.Embed(
        title=f"👋 Bienvenue sur {member.guild.name} !",
        description=f"Bienvenue {member.mention} !\nContent de t’avoir parmi nous.",
        color=0xd96b1c
    )

    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"Bovi • {member.guild.member_count} membres")

    await channel.send(embed=embed)


@bot.event
async def on_member_remove(member):
    guild_id = str(member.guild.id)

    if guild_id not in config:
        return

    guild_config = config[guild_id]

    # Nouveau système du panel
    goodbye_config = guild_config.get("goodbye", {})
    goodbye_enabled = goodbye_config.get("enabled", False)
    goodbye_channel_id = goodbye_config.get("channel_id", "")

    # Ancien système avec /setgoodbye
    old_goodbye_channel = guild_config.get("goodbye_channel")

    channel_id = goodbye_channel_id or old_goodbye_channel

    if not goodbye_enabled and not old_goodbye_channel:
        return

    if not channel_id:
        return

    channel = member.guild.get_channel(int(channel_id))

    if channel is None:
        return

    embed = discord.Embed(
        title="👋 Au revoir",
        description=f"{member.name} a quitté **{member.guild.name}**.\nOn espère te revoir bientôt.",
        color=0xd96b1c
    )

    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"Bovi • {member.guild.member_count} membres")

    await channel.send(embed=embed)


@bot.event
async def on_guild_join(guild):
    salon_logs = bot.get_channel(1518166096685957150)  # remplace par l'ID de ton salon logs

    if salon_logs is None:
        return

    embed = discord.Embed(
        title="📥 Bovi ajouté à un serveur",
        description="Bovi vient d'être ajouté dans un nouveau serveur.",
        color=0xff8a00
    )

    embed.add_field(name="📛 Nom du serveur", value=guild.name, inline=True)
    embed.add_field(name="👥 Membres", value=guild.member_count, inline=True)
    embed.add_field(name="🆔 ID du serveur", value=guild.id, inline=False)

    if guild.owner:
        embed.add_field(name="👑 Propriétaire", value=f"{guild.owner} | `{guild.owner.id}`", inline=False)

    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    await salon_logs.send("<@1104695464902799440>", embed=embed)


@bot.event
async def on_guild_remove(guild):
    salon_logs = bot.get_channel(1518166096685957150)  # ID du salon logs

    if salon_logs is None:
        return

    embed = discord.Embed(
        title="📤 Bovi retiré d'un serveur",
        description="Bovi vient d'être retiré d'un serveur.",
        color=0xff3b1f
    )

    embed.add_field(name="📛 Nom du serveur", value=guild.name, inline=True)
    embed.add_field(name="👥 Membres", value=guild.member_count, inline=True)
    embed.add_field(name="🆔 ID du serveur", value=guild.id, inline=False)

    if guild.owner:
        embed.add_field(name="👑 Propriétaire", value=f"{guild.owner} | `{guild.owner.id}`", inline=False)

    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    await salon_logs.send("<@1104695464902799440>", embed=embed)


# --------------------------------------------------
# COMMANDES SLASH
# --------------------------------------------------


@bot.tree.command(name="ping", description="Affiche la latence de Bovi.")
async def slash_ping(interaction: discord.Interaction):
    latence = round(bot.latency * 1000)

    embed = discord.Embed(
        title="🏓 Pong !",
        description=f"Latence : **{latence} ms**",
        color=0xff8a00
    )

    await interaction.response.send_message(embed=embed)


@bot.command()
async def syncslash(ctx):
    TON_ID = 1104695464902799440  # remplace par TON ID Discord

    if ctx.author.id != TON_ID:
        await ctx.send("❌ Cette commande est réservée au créateur de Bovi.")
        return

    await bot.tree.sync()
    await ctx.send("✅ Commandes slash synchronisées.")


@bot.tree.command(name="botinfo", description="Affiche les informations de Bovi.")
async def slash_botinfo(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 Informations sur Bovi",
        description="Ton oiseau, ton ami, ton bot.",
        color=0xff8a00
    )

    embed.add_field(name="📛 Nom", value="Bovi", inline=True)
    embed.add_field(name="👑 Créateur", value="Venōx爱", inline=True)
    embed.add_field(name="⚙️ Bibliothèque", value="discord.py", inline=True)
    embed.add_field(name="🚀 Version", value="1.0", inline=True)

    embed.set_footer(text="Bovi • Bot Discord")

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="aide", description="Affiche le lien vers l'aide de Bovi.")
async def slash_aide(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📚 Aide de Bovi",
        description="Besoin d'aide avec Bovi ? Consulte la documentation officielle.",
        color=0xff8a00
    )

    embed.add_field(
        name="🏠 Accueil",
        value="https://venox-dev918.github.io/Bovi/index.html",
        inline=False
    )

    embed.add_field(
        name="🔗 Documentation",
        value="https://venox-dev918.github.io/Bovi/documentation.html",
        inline=False
    )

    embed.add_field(
        name="⚙️ Dashboard",
        value="https://proudly-rocket-testimonials-mag.trycloudflare.com",
        inline=False
    )

    embed.add_field(
        name="💬 Serveur support",
        value="https://discord.gg/WU2StEpNuw",
        inline=False
    )

    await interaction.response.send_message(embed=embed)



@bot.tree.command(name="serverinfo", description="Affiche les informations du serveur.")
async def slash_serverinfo(interaction: discord.Interaction):
    serveur = interaction.guild

    embed = discord.Embed(
        title=f"🏠 Informations sur {serveur.name}",
        description="Voici les informations du serveur.",
        color=0xff8a00
    )

    embed.add_field(name="📛 Nom", value=serveur.name, inline=True)
    embed.add_field(name="👑 Propriétaire", value=serveur.owner.mention, inline=True)
    embed.add_field(name="👥 Membres", value=serveur.member_count, inline=True)
    embed.add_field(name="🆔 ID", value=serveur.id, inline=True)
    embed.add_field(name="💬 Salons", value=len(serveur.channels), inline=True)
    embed.add_field(name="📅 Créé le", value=serveur.created_at.strftime("%d/%m/%Y"), inline=True)

    if serveur.icon:
        embed.set_thumbnail(url=serveur.icon.url)

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="userinfo", description="Affiche les informations d'un utilisateur.")
async def slash_userinfo(interaction: discord.Interaction, membre: discord.Member = None):
    if membre is None:
        membre = interaction.user

    embed = discord.Embed(
        title=f"👤 Informations sur {membre.name}",
        description="Voici les informations de l'utilisateur.",
        color=0xff8a00
    )

    embed.add_field(name="📛 Nom", value=membre.name, inline=True)
    embed.add_field(name="🏷️ Pseudo serveur", value=membre.display_name, inline=True)
    embed.add_field(name="🆔 ID", value=membre.id, inline=True)
    embed.add_field(name="🤖 Bot ?", value="Oui" if membre.bot else "Non", inline=True)
    embed.add_field(name="📅 Compte créé le", value=membre.created_at.strftime("%d/%m/%Y"), inline=True)

    if membre.joined_at:
        embed.add_field(name="📥 A rejoint le", value=membre.joined_at.strftime("%d/%m/%Y"), inline=True)

    embed.add_field(name="🎭 Rôle le plus haut", value=membre.top_role.mention, inline=True)

    embed.set_thumbnail(url=membre.display_avatar.url)

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="avatar", description="Affiche l'avatar d'un utilisateur.")
async def slash_avatar(interaction: discord.Interaction, membre: discord.Member = None):
    if membre is None:
        membre = interaction.user

    embed = discord.Embed(
        title=f"🖼️ Avatar de {membre.display_name}",
        color=0xff8a00
    )

    embed.set_image(url=membre.display_avatar.url)

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="servericon", description="Affiche l'icône du serveur.")
async def slash_servericon(interaction: discord.Interaction):
    serveur = interaction.guild

    if serveur.icon is None:
        await interaction.response.send_message("❌ Ce serveur n'a pas d'icône.", ephemeral=True)
        return

    embed = discord.Embed(
        title=f"🖼️ Icône de {serveur.name}",
        color=0xff8a00
    )

    embed.set_image(url=serveur.icon.url)

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="members", description="Affiche les statistiques des membres.")
async def slash_members(interaction: discord.Interaction):
    serveur = interaction.guild

    total = serveur.member_count
    bots = sum(1 for membre in serveur.members if membre.bot)
    humains = total - bots

    embed = discord.Embed(
        title=f"👥 Membres de {serveur.name}",
        description="Voici les statistiques des membres du serveur.",
        color=0xff8a00
    )

    embed.add_field(name="👥 Total", value=total, inline=True)
    embed.add_field(name="🙋 Humains", value=humains, inline=True)
    embed.add_field(name="🤖 Bots", value=bots, inline=True)
    embed.add_field(name="🎭 Rôles", value=len(serveur.roles), inline=True)
    embed.add_field(name="💬 Salons", value=len(serveur.channels), inline=True)

    if serveur.icon:
        embed.set_thumbnail(url=serveur.icon.url)

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="uptime", description="Affiche depuis combien de temps Bovi est en ligne.")
async def slash_uptime(interaction: discord.Interaction):
    temps_total = int(time.time() - start_time)

    jours = temps_total // 86400
    heures = (temps_total % 86400) // 3600
    minutes = (temps_total % 3600) // 60
    secondes = temps_total % 60

    embed = discord.Embed(
        title="⏱️ Uptime de Bovi",
        description="Bovi est actuellement en ligne.",
        color=0xff8a00
    )

    embed.add_field(name="📅 Jours", value=jours, inline=True)
    embed.add_field(name="🕒 Heures", value=heures, inline=True)
    embed.add_field(name="⏰ Minutes", value=minutes, inline=True)
    embed.add_field(name="⏳ Secondes", value=secondes, inline=True)

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="date", description="Affiche la date et l'heure.")
async def slash_date(interaction: discord.Interaction):
    maintenant = datetime.now()

    embed = discord.Embed(
        title="📅 Date et heure",
        description="Voici la date et l'heure actuelles.",
        color=0xff8a00
    )

    embed.add_field(name="📆 Date", value=maintenant.strftime("%d/%m/%Y"), inline=True)
    embed.add_field(name="🕒 Heure", value=maintenant.strftime("%H:%M:%S"), inline=True)

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="de", description="Lance un dé de 1 à 6.")
async def slash_de(interaction: discord.Interaction):
    resultat = random.randint(1, 6)

    embed = discord.Embed(
        title="🎲 Lancer de dé",
        description=f"Le dé est tombé sur **{resultat}** !",
        color=0xff8a00
    )

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="pileouface", description="Lance une pièce.")
async def slash_pileouface(interaction: discord.Interaction):
    resultat = random.choice(["Pile", "Face"])

    embed = discord.Embed(
        title="🪙 Pile ou face",
        description=f"La pièce est tombée sur **{resultat}** !",
        color=0xff8a00
    )

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="ball", description="Pose une question à la boule magique.")
async def slash_ball(interaction: discord.Interaction, question: str):
    reponses = [
        "Oui, carrément 😎",
        "Non 😭",
        "Peut-être 🤔",
        "Je pense que oui 🔥",
        "Je pense que non",
        "Impossible à savoir",
        "Demande plus tard",
        "Bien sûr 😌"
    ]

    resultat = random.choice(reponses)

    embed = discord.Embed(
        title="🎱 Boule magique",
        description=f"**Question :** {question}\n**Réponse :** {resultat}",
        color=0xff8a00
    )

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="randommember", description="Choisit un membre au hasard.")
async def slash_randommember(interaction: discord.Interaction):
    membres = [membre for membre in interaction.guild.members if not membre.bot]

    if len(membres) == 0:
        await interaction.response.send_message("❌ Je n'ai trouvé aucun membre humain.", ephemeral=True)
        return

    membre_choisi = random.choice(membres)

    embed = discord.Embed(
        title="🎉 Membre aléatoire",
        description=f"Le membre choisi est {membre_choisi.mention} !",
        color=0xff8a00
    )

    embed.set_thumbnail(url=membre_choisi.display_avatar.url)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="say", description="Envoie un message avec Bovi.")
@app_commands.default_permissions(administrator=True)
async def slash_say(interaction: discord.Interaction, message: str):
    embed = discord.Embed(
        description=message,
        color=0xff8a00
    )

    embed.set_author(
        name=f"Message de {interaction.user.display_name}",
        icon_url=interaction.user.display_avatar.url
    )

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="poll", description="Crée un sondage simple.")
@app_commands.default_permissions(administrator=True)
async def slash_poll(interaction: discord.Interaction, question: str):
    embed = discord.Embed(
        title="📊 Sondage",
        description=question,
        color=0xff8a00
    )

    embed.set_author(
        name=f"Sondage de {interaction.user.display_name}",
        icon_url=interaction.user.display_avatar.url
    )

    await interaction.response.send_message(embed=embed)

    message = await interaction.original_response()
    await message.add_reaction("✅")
    await message.add_reaction("❌")


@bot.tree.command(name="annonce", description="Envoie une annonce avec Bovi.")
@app_commands.default_permissions(administrator=True)
async def slash_annonce(interaction: discord.Interaction, message: str):
    embed = discord.Embed(
        title="📣 Annonce",
        description=message,
        color=0xff8a00
    )

    embed.set_author(
        name=f"Annonce de {interaction.user.display_name}",
        icon_url=interaction.user.display_avatar.url
    )

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="clear", description="Supprime un nombre de messages.")
@app_commands.default_permissions(manage_messages=True)
async def slash_clear(interaction: discord.Interaction, nombre: int):
    if nombre <= 0:
        await interaction.response.send_message("❌ Le nombre doit être supérieur à 0.", ephemeral=True)
        return

    if nombre > 100:
        await interaction.response.send_message("❌ Tu ne peux pas supprimer plus de 100 messages d'un coup.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    messages_supprimes = await interaction.channel.purge(limit=nombre)

    await interaction.followup.send(
        f"✅ {len(messages_supprimes)} message(s) supprimé(s).",
        ephemeral=True
    )


@bot.tree.command(name="kick", description="Expulse un membre du serveur.")
@app_commands.default_permissions(kick_members=True)
async def slash_kick(interaction: discord.Interaction, membre: discord.Member, raison: str = "Aucune raison"):
    try:
        await membre.kick(reason=raison)

        embed = discord.Embed(
            title="👢 Membre expulsé",
            description=f"{membre.mention} a été expulsé du serveur.",
            color=0xff8a00
        )

        embed.add_field(name="📌 Raison", value=raison, inline=False)

        await interaction.response.send_message(embed=embed)

    except discord.Forbidden:
        await interaction.response.send_message("❌ Je n'ai pas la permission d'expulser ce membre.", ephemeral=True)


@bot.tree.command(name="ban", description="Bannit un membre du serveur.")
@app_commands.default_permissions(ban_members=True)
async def slash_ban(interaction: discord.Interaction, membre: discord.Member, raison: str = "Aucune raison"):
    try:
        await membre.ban(reason=raison)

        embed = discord.Embed(
            title="🔨 Membre banni",
            description=f"{membre.mention} a été banni du serveur.",
            color=0xff8a00
        )

        embed.add_field(name="📌 Raison", value=raison, inline=False)

        await interaction.response.send_message(embed=embed)

    except discord.Forbidden:
        await interaction.response.send_message("❌ Je n'ai pas la permission de bannir ce membre.", ephemeral=True)


@bot.tree.command(name="unban", description="Débannit un utilisateur avec son ID.")
@app_commands.default_permissions(ban_members=True)
async def slash_unban(interaction: discord.Interaction, user_id: str):
    try:
        user_id = int(user_id)
        user = await bot.fetch_user(user_id)

        await interaction.guild.unban(user)

        embed = discord.Embed(
            title="🔓 Utilisateur débanni",
            description=f"{user} a été débanni du serveur.",
            color=0xff8a00
        )

        await interaction.response.send_message(embed=embed)

    except ValueError:
        await interaction.response.send_message("❌ L'ID doit être un nombre.", ephemeral=True)

    except discord.NotFound:
        await interaction.response.send_message("❌ Utilisateur introuvable ou pas banni.", ephemeral=True)

    except discord.Forbidden:
        await interaction.response.send_message("❌ Je n'ai pas la permission de débannir.", ephemeral=True)


@bot.tree.command(name="warn", description="Avertit un membre.")
@app_commands.default_permissions(kick_members=True)
async def slash_warn(interaction: discord.Interaction, membre: discord.Member, raison: str = "Aucune raison"):
    membre_id = str(membre.id)

    if membre_id not in warns:
        warns[membre_id] = []

    warns[membre_id].append(raison)
    sauvegarder_warns()

    embed = discord.Embed(
        title="⚠️ Membre averti",
        description=f"{membre.mention} a reçu un avertissement.",
        color=0xff8a00
    )

    embed.add_field(name="📌 Raison", value=raison, inline=False)
    embed.add_field(name="📊 Total de warns", value=len(warns[membre_id]), inline=True)

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="warnings", description="Affiche les avertissements d'un membre.")
@app_commands.default_permissions(kick_members=True)
async def slash_warnings(interaction: discord.Interaction, membre: discord.Member):
    membre_id = str(membre.id)

    if membre_id not in warns or len(warns[membre_id]) == 0:
        await interaction.response.send_message(f"✅ {membre.mention} n'a aucun avertissement.", ephemeral=True)
        return

    liste_warns = ""

    for numero, raison in enumerate(warns[membre_id], start=1):
        liste_warns += f"**{numero}.** {raison}\n"

    embed = discord.Embed(
        title=f"⚠️ Warns de {membre.display_name}",
        description=liste_warns,
        color=0xff8a00
    )

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="serveurs", description="Affiche les serveurs où Bovi est présent.")
async def slash_serveurs(interaction: discord.Interaction):
    TON_ID = 1104695464902799440  # remplace par TON ID Discord

    if interaction.user.id != TON_ID:
        await interaction.response.send_message("❌ Cette commande est réservée au créateur de Bovi.", ephemeral=True)
        return

    nombre_serveurs = len(bot.guilds)
    total_membres = sum(guild.member_count for guild in bot.guilds)

    embed = discord.Embed(
        title="🌍 Serveurs de Bovi",
        description="Voici les statistiques actuelles de Bovi.",
        color=0xff8a00
    )

    embed.add_field(name="📌 Nombre de serveurs", value=nombre_serveurs, inline=True)
    embed.add_field(name="👥 Membres au total", value=total_membres, inline=True)

    await interaction.response.send_message(embed=embed, ephemeral=True)
    
bot.run(TOKEN)
