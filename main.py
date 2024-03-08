import discord
from discord.ext import commands
import sqlite3
import requests
import random
from PIL import Image

# Initialize bot
bot = commands.Bot(command_prefix='!')

# Jikan API base URL
JIKAN_API_BASE_URL = "https://api.jikan.moe/v3"

# Connect to SQLite database
conn = sqlite3.connect('bot_database.db')
c = conn.cursor()

# Create tables if they don't exist
c.execute('''CREATE TABLE IF NOT EXISTS users (
             user_id INTEGER PRIMARY KEY,
             username TEXT,
             alt_of INTEGER,
             verification_code TEXT
             )''')

c.execute('''CREATE TABLE IF NOT EXISTS characters (
             id INTEGER PRIMARY KEY,
             name TEXT,
             description TEXT,
             image_url TEXT,
             rarity TEXT
             )''')

# Function to fetch anime character data from Jikan API
def fetch_character_data():
    response = requests.get(f"{JIKAN_API_BASE_URL}/character/1")
    if response.status_code == 200:
        return response.json()
    else:
        return None

# Function to create embeds for character data
def create_character_embed(character):
    embed = discord.Embed(title=character['name'], description=character['about'], color=random.randint(0, 0xFFFFFF))
    embed.set_image(url=character['image_url'])
    embed.add_field(name='Rarity', value=character['rarity'], inline=True)
    # Add more fields as needed
    return embed

# Command to fetch a random character and display as embed
@bot.command()
async def random_character(ctx):
    character_data = fetch_character_data()
    if character_data:
        random_character = random.choice(character_data)
        embed = create_character_embed(random_character)
        await ctx.send(embed=embed)
    else:
        await ctx.send("Failed to fetch character data.")

# Command to send verification code
@bot.command()
async def verify(ctx):
    verification_code = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=6))
    c.execute("INSERT INTO users (user_id, username, verification_code) VALUES (?, ?, ?)",
              (ctx.author.id, str(ctx.author), verification_code))
    conn.commit()
    await ctx.send(f"Verification code sent! Check your DMs for the code.")
    await ctx.author.send(f"Your verification code: {verification_code}")

# Command to verify user using the code
@bot.command()
async def check_verify(ctx, code: str):
    c.execute("SELECT * FROM users WHERE user_id=?", (ctx.author.id,))
    user = c.fetchone()
    if user and user[3] == code:
        await ctx.send("Verification successful!")
    else:
        await ctx.send("Verification failed.")

# Command to drop 3 anime characters
@bot.command()
async def drop_characters(ctx):
    character_data = fetch_character_data()
    if character_data:
        # Assuming character data is a list of characters
        characters_to_drop = random.sample(character_data, 3)
        for character in characters_to_drop:
            embed = create_character_embed(character)
            await ctx.send(embed=embed)
    else:
        await ctx.send("Failed to fetch character data.")

# Event to detect alts
@bot.event
async def on_message(message):
    # Implementation of alt detection
    await bot.process_commands(message)

# Run the bot
bot.run('MTIxNTQ2ODYwMjQyMjA2NzI3MQ.GavQEs.7HNmKh3YJjP-WaY0UcCH95KTj7WLcBY0oIEGjc')

# Close database connection
conn.close()