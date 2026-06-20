import discord
from discord.ext import commands
import random
from datetime import datetime

import os

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


@bot.event
async def on_ready():
    print(f"{bot.user} est connecté !")

    activity = discord.Activity(
        type=discord.ActivityType.watching,
        name="Utilise !aide"
    )
    await bot.change_presence(activity=activity)

@bot.command()
async def ping(ctx):
    await ctx.send("🏓 Pong !")
    

@bot.command()
async def aide(ctx):
    await ctx.send("""
📚 **Commandes disponibles**

🏓 !ping → Joue une partie contre le bot
📖 !aide → Affiche cette liste
🏠 !serverinfo → Infos du serveur
👤 !userinfo → Infos sur ton compte
🤖 !botinfo → Infos sur le bot
🖼 !avatar → Affiche ton avatar
📅 !date → Affiche la date et l'heure
🎲 !de → Lance un dé
🪙 !pileouface → Lance une pièce
🧹 !clear → Supprime des messages
👢 !kick → Expulse un membre
🔨 !ban → Bannit un membre
""")


@bot.command()
async def serverinfo(ctx):
    serveur = ctx.guild

    await ctx.send(f"""
🏠 Nom : {serveur.name}
👥 Membres : {serveur.member_count}
🆔 ID : {serveur.id}
""")


@bot.command()
async def userinfo(ctx):
    membre = ctx.author

    await ctx.send(f"""
👤 Nom : {membre.name}
🆔 ID : {membre.id}
📅 Compte créé le : {membre.created_at.strftime('%d/%m/%Y')}
""")


@bot.command()
async def botinfo(ctx):
    await ctx.send("""
🤖 **Informations sur Bovi**

📛 Nom : Bovi
👨 Créateur : Venox
⚙️ Bibliothèque : discord.py
🚀 Version : 1.0
""")
    

@bot.command()
async def avatar(ctx):
    await ctx.send(ctx.author.display_avatar.url)


@bot.command()
async def date(ctx):
    maintenant = datetime.now()
    await ctx.send(f"📅 Nous sommes le {maintenant.strftime('%d/%m/%Y à %H:%M:%S')}")


@bot.command()
async def de(ctx):
    resultat = random.randint(1, 6)
    await ctx.send(f"🎲 Tu as obtenu : {resultat}")


@bot.command()
async def pileouface(ctx):
    resultat = random.choice(["Pile", "Face"])
    await ctx.send(f"🪙 Résultat : {resultat}")


@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send("🧹 Bovi a supprimé les messages !", delete_after=5)


@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, membre: discord.Member, *, raison="Aucune raison"):
    await membre.kick(reason=raison)
    await ctx.send(f"👢 {membre} a été expulsé.")


@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, membre: discord.Member, *, raison="Aucune raison"):
    await membre.ban(reason=raison)
    await ctx.send(f"🔨 BOVI a banni {membre}.")


@bot.command()
async def test(ctx):
    await ctx.send("Bovi fonctionne !")
    
bot.run(TOKEN)
