import discord
from discord.ext import commands
from discord.ext import tasks
from discord.utils import find
from discord import app_commands

from dotenv import load_dotenv
import re
import os

load_dotenv()
TOKEN = os.environ['TOKEN']
AGENDA_URL = os.environ['AGENDA_URL']

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.command(name='updateInfo')
async def update_chapters(ctx, channel: discord.TextChannel):
    # Read the markdown file and parse it to extract the chapter parts
    with open('infoChannel.md', 'r') as f:
        markdown_file = f.read()
    # Split the markdown text into sections based on the "##" header
    sections = re.split(r'\n##\s+', markdown_file)[1:]
    # Extract the title and description from each section
    chapter_parts = []
    for section in sections:
        title, description = section.split('\n', 1)
        chapter_parts.append({'title': title, 'description': description})
    # Get the channel to send the embeds to
    channel = bot.get_channel(1122874143596089354)
    # For each chapter part, create an embed with the relevant information
    for part in chapter_parts:
        embed = discord.Embed(title=part['title'], description=part['description'],color=0x00A8E8)
        # Send the embed to the specified channel
        await channel.send(embed=embed)


bot.run(TOKEN)
