import discord
from discord.ext import commands
from discord.ext import tasks
from discord.utils import find

from datetime import datetime, timedelta, timezone
import ics
from markdownify import markdownify
from dotenv import load_dotenv
from PIL import Image
from io import BytesIO
import os
import requests
import random

from oasis import getGrades
from tesla import getInternships, getInternshipInfos
from bus import getNextBuses, stations


load_dotenv()
TOKEN = os.environ['TOKEN']
AGENDA_URL = os.environ['AGENDA_URL']

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

@tasks.loop(minutes=30)
async def tesla():
    internships = getInternships()

    ### Polytech
    guild = find(lambda g: 'PEIP' in g.name, bot.guilds)
    channel = find(lambda c: 'tesla' in c.name, guild.text_channels)
    
    previousListings = [
        int(message.embeds[0].footer.text)
        async for message in channel.history(limit=None)
        if len(message.embeds)
    ]
    
    newListings = [l for l in internships if not int(l['id']) in previousListings]
    
    if len(newListings):
        await channel.send('||@everyone||')
    
    for listing in newListings:
        infosListing = getInternshipInfos(listing['id'])
        embed = discord.Embed(
            title = f"Nouveau stage Tesla : {infosListing['title']}",
            color = 0xC90000,
            url = f'https://www.tesla.com/fr_FR/careers/search/job/{listing["id"]}',
            description = markdownify(
                infosListing['description']
                .replace('</div>', '</div> ')
            ),
            timestamp = datetime.now()
        )
        embed.set_thumbnail(url='https://www.tesla.com/themes/custom/tesla_frontend/assets/favicons/favicon-196x196.png')
        embed.set_footer(text=listing['id'])
        embed.add_field(name ='Localisation', value=infosListing['location'], inline=False)
        embed.add_field(name ='Département', value=infosListing['department'], inline=False)
        
        await channel.send(embed=embed)
        print(infosListing['title'])


@tasks.loop(minutes=30)
async def grades():
    grades = getGrades()

    ### Polytech
    guild = find(lambda g: 'PEIP' in g.name, bot.guilds)
    channel = find(lambda c: 'nouvelles-notes' in c.name, guild.text_channels)
    
    ### New Grades
    previousGrades = [
        message.embeds[0].footer.text
        async for message in channel.history(limit=None)
        if len(message.embeds)
        and message.embeds[0].title.startswith('Nouvelle note')
    ]
    
    newGrades = [
        grade for grade in grades
        if not f"{grade['subject-id']} - {grade['name']}" in previousGrades
        and grade['grade'] is not None
    ]
    
    if len(newGrades):
        await channel.send('||@everyone||')
    
    for grade in newGrades:
        embed = discord.Embed(
            title=f"Nouvelle note en **{grade['subject']}** !",
            color=0x00A8E8,
            url='https://oasis.polytech.universite-paris-saclay.fr/',
            description=grade['name'],
            timestamp=grade['date'],
        )

        oasis_icon = 'https://oasis.polytech.universite-paris-saclay.fr/prod/bo/picture/favicon/polytech_paris_oasis/favicon-194x194.png'
        embed.set_thumbnail(url=oasis_icon)
        embed.set_footer(text = f"{grade['subject-id']} - {grade['name']}")

        await channel.send(embed=embed)
        print(f"{grade['subject-id']} - {grade['name']}")
    
    
    ### Pending grades
    previousPendingGrades = [
        message.embeds[0].footer.text
        async for message in channel.history(limit=None)
        if len(message.embeds)
        and 'bientôt' in message.embeds[0].title.lower()
    ]
    
    newPendingGrades = [
        grade for grade in grades
        if not f"{grade['subject-id']} - {grade['name']}" in previousPendingGrades
        and grade['grade'] is None
    ]

    for grade in newPendingGrades:
        embed = discord.Embed(
            title=f"*Une note devrait bientôt être disponible en **{grade['subject']}***  👀",
            color=0x00A8E8,
            url='https://oasis.polytech.universite-paris-saclay.fr/',
            description=grade['name'],
            timestamp=grade['date'],
        )
        embed.set_footer(text = f"{grade['subject-id']} - {grade['name']}")

        await channel.send(embed=embed)
        print(f"[ SOON ] {grade['subject-id']} - {grade['name']}")


@tasks.loop(minutes=10)
async def nextBuses():
    '''Envoie les horaires des prochains bus sur Discord lorsque je finis les cours'''
    nextBuses = getNextBuses()
    
    r = requests.get(AGENDA_URL).text
    agenda = ics.Calendar(r)
    todayClasses = [c for c in agenda.events if c.begin.date() == datetime.now().date()]
    todayClasses.sort(key=lambda c: c.begin)
    lastClass = todayClasses[-1]
    
    ### Polytech
    guild = find(lambda g: 'PEIP' in g.name, bot.guilds)
    channel = find(lambda c: 'prochains-bus' in c.name, guild.text_channels)
    
    embed = discord.Embed()
    embed.title = "Prochains bus"
    
    for bus in nextBuses:
        if bus['direction'] == 'backward':
            delay = timedelta(seconds=bus['delay'])
            time = datetime.now() + delay
            
            ligne = bus['line']
            destination = stations[bus['destination']] if bus['destination'] in stations else ''
            embed.add_field(
                name = f"{ligne} - {destination} {'🦽' if bus['wheelchair'] else ''}",
                value = f"<t:{int(time.timestamp())}:t> (<t:{int(time.timestamp())}:R>)",
                inline = False
            )
        
    if not len(nextBuses):
        embed.description = 'Aucun bus prévu dans la prochaine heure.'
    
    messages = await channel.history(limit=None).flatten()
    if len(messages):
        await messages[0].edit(embed=embed)
    else:
        await channel.send(embed=embed)
                    
    if datetime.now(timezone.utc) <= lastClass.end and (lastClass.end - datetime.now(timezone.utc)) <= timedelta(minutes=10):
        message = await channel.send(
            '<@231806011269185536>',
            delete_after=3600
        )


@tasks.loop(seconds=30)
async def bot_presence():
    '''Shows "Playing {message}" on Discord'''
    texts = [
        ("Regarde", "vos notes 👀"),
        ("Regarde", "les polys de cours 📖"),
        ("Regarde", "des stages pour cet été 🧑‍💼"),
        ("Regarde", "ta moyenne générale 📉"),
        ("Joue à", "réviser 📚"),
        ("Écoute", "le cours 🧑‍🏫"),
    ]
    text = random.choice(texts)
    
    if text[0] == "Joue à":
        await bot.change_presence(activity=discord.Game(name=text[1]))
    elif text[0] == "Regarde":
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=text[1]))
    elif text[0] == "Écoute":
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=text[1]))

@bot.command(name='botmessage')
async def annonce(ctx, channel: discord.TextChannel, *, message: str):
    print(message)
    await channel.send(message)

@bot.command(name='wip')
async def wip(ctx):
    guild = ctx.guild
    server_name = guild.name
    new_name = '🚧 - '+server_name 
    await guild.edit(name=new_name)
    icon_url = guild.icon.url
    response = requests.get(icon_url)
    img = Image.open(BytesIO(response.content))
    file_path = os.path.join(os.path.dirname(__file__), 'original_icon.png')
    img.save(file_path, 'PNG')
    overlay = Image.open('wip.png')
    img.paste(overlay, (0, 0), overlay)
    file_path = os.path.join(os.path.dirname(__file__), 'new_icon.png')
    img.save(file_path, 'PNG')
    with open(file_path, 'rb') as f:
        await guild.edit(icon=f.read())
    os.remove(os.path.join(os.path.dirname(__file__), 'new_icon.png'))

@bot.command(name='default')
async def default(ctx):
    guild = ctx.guild
    server_name = guild.name
    new_name = server_name[4:]
    await guild.edit(name=new_name)
    file_path = os.path.join(os.path.dirname(__file__), 'original_icon.png')
    with open(file_path, 'rb') as f:
        await guild.edit(icon=f.read())
    os.remove(os.path.join(os.path.dirname(__file__), 'original_icon.png'))

@bot.event
async def on_ready():
    print('Le bot est prêt !')
    bot_presence.start()
    tesla.start()
    grades.start()
    # nextBuses.start()

bot.run(TOKEN)
