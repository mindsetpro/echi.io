import discord
from discord.ext import commands, tasks
import sqlite3
import requests
import random
from PIL import Image
import os

# Initialize bot
intents = discord.Intents.all()
intents.members = True
intents.guilds = True
bot = commands.Bot(command_prefix='e!',intents=intents)

# Jikan API base URL
JIKAN_API_BASE_URL = "https://api.jikan.moe/v4"

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
def fetch_all_characters():
    all_characters = []

    for page in range(1, 401):
        response = requests.get(f"{JIKAN_API_BASE_URL}/characters/{page}")
        if response.status_code == 200:
            characters = response.json()['characters']
            if not characters:
                break  # No more characters to fetch
            all_characters.extend(characters)
        else:
            return None

    return all_characters

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
    character_data = fetch_all_characters()
    if character_data:
        random_character = random.choice(character_data)
        embed = create_character_embed(random_character)
        await ctx.send(embed=embed)
    else:
        await ctx.send("Failed to fetch character data.")

# Command to send verification code
@bot.command()
async def sc(ctx):
    verification_code = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=6))
    c.execute("INSERT INTO users (user_id, username, verification_code) VALUES (?, ?, ?)",
              (ctx.author.id, str(ctx.author), verification_code))
    conn.commit()
    await ctx.send(f"Verification code sent! Check your DMs for the code.")
    await ctx.author.send(f"Your verification code: {verification_code}")

# Command to verify user using the code
@bot.command()
async def verify(ctx, code: str):
    c.execute("SELECT * FROM users WHERE user_id=?", (ctx.author.id,))
    user = c.fetchone()
    if user and user[3] == code:
        await ctx.send("Verification successful!")
    else:
        await ctx.send("Verification failed.")

# Command to drop 1 anime character
class ClaimCharacterView(discord.ui.View):
    def __init__(self, character):
        super().__init__()
        self.character = character

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.primary)
    async def claim_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.send_message(f"Claimed {self.character}!")

@bot.command()
async def dr(ctx):
    character_data = fetch_all_characters()
    if character_data:
        # Assuming character data is a list of characters
        characters_to_drop = random.sample(character_data, 1)
        for character in characters_to_drop:
            embed = create_character_embed(character)
            view = ClaimCharacterView(character)
            await ctx.send(embed=embed, view=view)
    else:
        await ctx.send("Failed to fetch character data.")

# Command to check if the user is verified
async def is_verified(ctx):
    c.execute("SELECT * FROM users WHERE user_id=?", (ctx.author.id,))
    user = c.fetchone()
    if user and user[3] is not None:
        return True
    else:
        await ctx.send("You are not verified. Please use `e!sc` to get verified.")
        return False

# Command to get character details by ID
@bot.command()
async def c(ctx, char_id: int):
    c.execute("SELECT * FROM characters WHERE id=?", (char_id,))
    character = c.fetchone()
    if character:
        embed = discord.Embed(title=character[1], description=character[2], color=random.randint(0, 0xFFFFFF))
        embed.set_image(url=character[3])
        embed.add_field(name='Rarity', value=character[4], inline=True)
        await ctx.send(embed=embed)
    else:
        await ctx.send("Character not found.")

# Command to send the most recently received card's details
@bot.command()
async def v(ctx):
    c.execute("SELECT * FROM characters ORDER BY id DESC LIMIT 1")
    character = c.fetchone()
    if character:
        embed = discord.Embed(title=character[1], description=character[2], color=random.randint(0, 0xFFFFFF))
        embed.set_image(url=character[3])
        embed.add_field(name='Rarity', value=character[4], inline=True)
        await ctx.send(embed=embed)
    else:
        await ctx.send("No character found.")

# Command to list all characters with pagination
@bot.command()
async def co(ctx):
    c.execute("SELECT * FROM characters")
    characters = c.fetchall()
    if characters:
        characters_per_page = 10
        pages = [characters[i:i+characters_per_page] for i in range(0, len(characters), characters_per_page)]
        current_page = 0

        async def show_page(page_num):
            page = pages[page_num]
            embed = discord.Embed(title="Character List", color=random.randint(0, 0xFFFFFF))
            for character in page:
                embed.add_field(name=character[1], value=f"ID: {character[0]}, Rarity: {character[4]}", inline=False)
            embed.set_footer(text=f"Page {page_num+1}/{len(pages)}")
            return embed

        message = await ctx.send(embed=await show_page(current_page))

        async def paginate(page_num):
            await message.edit(embed=await show_page(page_num))

        if len(pages) > 1:
            for direction in ('\u2B05', '\u27A1'):
                await message.add_reaction(direction)

            def check(reaction, user):
                return user == ctx.author and reaction.message == message and str(reaction.emoji) in ('\u2B05', '\u27A1')

            while True:
                reaction, user = await bot.wait_for('reaction_add', check=check)
                if str(reaction.emoji) == '\u2B05':
                    current_page = (current_page - 1) % len(pages)
                elif str(reaction.emoji) == '\u27A1':
                    current_page = (current_page + 1) % len(pages)
                await reaction.remove(user)
                await paginate(current_page)
    else:
        await ctx.send("No characters found.")

# Event to detect alts
@bot.event
async def on_message(message):
    if message.author.bot:
        return  # Ignore messages from bots

    # Check if the user is in the database
    c.execute("SELECT * FROM users WHERE user_id=?", (message.author.id,))
    user = c.fetchone()
    if user:
        if user[2] is not None:
            await message.author.send(f"Hello {message.author.name}, You have been detected as an alt of user {user[2]}. You are not allowed to use this bot.")
            # Log the user in a separate database for users not allowed to use the bot
            c.execute("INSERT INTO blacklisted_users (user_id) VALUES (?)", (message.author.id,))
            conn.commit()
            return  # Stop further processing of the message

    await bot.process_commands(message)

# Fetch the token from environment variables
token = os.environ.get('token')

# Check if the token is available
if token is None:
    print("Please set the 'token' environment variable.")
else:
    # Run the bot
    bot.run(token)

# Close database connection
conn.close()
