import discord
from discord.ext import commands, tasks
from datetime import datetime
import pytz
import os

# Set the time zone to GMT+8
gmt8 = pytz.timezone('Asia/Singapore')

# Initialize the bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Server name mappings
server_names = {
    'a1': 'Altinova-1',
    'a2': 'Altinova-2',
    'h1': 'Heidel-1',
    'h2': 'Heidel-2',
    'g1': 'Grana-1',
    'g2': 'Grana-2',
    'v1': 'Velia-1',
    'v2': 'Velia-2',
    'r1': 'Rulupee-1',
    'r2': 'Rulupee-2',
    'cal': 'Calpheon',
    'bal': 'Balenos',
    'ser': 'Serendia',
    'med': 'Mediah',
    'val': 'Valencia',
    'kama': 'Kamasylvia',
    'o1': 'Odyllita-1'
}

# Initialize variables
guild_quests = {}
daily_quest_limit = 10
quests_added_today = 0

# Function to reset the quest count at midnight (GMT+8)
@tasks.loop(minutes=1)
async def reset_quest_limit():
    now = datetime.now(gmt8)
    if now.hour == 0 and now.minute == 0:
        global quests_added_today
        quests_added_today = 0
        print("Daily quest limit has been reset.")

# Event when bot is ready
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    if not reset_quest_limit.is_running():
        reset_quest_limit.start()  # Start the task loop once the bot is ready

# Remove the default help command
bot.remove_command('help')

@bot.command(name='gqa')
async def add_quest(ctx, server: str, *, quest_name: str):
    global quests_added_today
    server = server.lower()

    # Check if the server abbreviation is valid
    if server in server_names:
        server_full_name = server_names[server]
    else:
        # Send a message with the list of valid server abbreviations
        valid_servers = '\n'.join([f'{abbr} = {full_name}' for abbr, full_name in server_names.items()])
        await ctx.send(f'Unknown server abbreviation "{server}".\nHere is a list of valid server abbreviations:\n{valid_servers}')
        return

    # Check if the quest limit has been reached
    if quests_added_today >= daily_quest_limit:
        await ctx.send(f'You have reached the daily quest limit of {daily_quest_limit}. Try again tomorrow.')
        return

    # Check if a quest already exists for the server
    if server_full_name in guild_quests:
        await ctx.send(f'A quest is already in progress for {server_full_name}. Please complete or remove it first.')
    else:
        guild_quests[server_full_name] = {'name': quest_name, 'status': 'ongoing'}
        quests_added_today += 1
        await ctx.send(f'Added quest "{quest_name}" to server "{server_full_name}".')

# Track claimed quests for the day
claimed_quests_today = 0

@bot.command(name='gql')
async def list_quests(ctx, server: str = None):
    # Prepare the embed
    embed_color = discord.Color.blue()  # Default color
    embed = discord.Embed(title='Guild Quest Status', description=f'{quests_added_today}/{daily_quest_limit} quests added today\n{claimed_quests_today}/10 claimed quests today', color=embed_color)

    # Sort quests based on their status in the order of "ongoing", "claimed", "done"
    status_order = {'ongoing': 1, 'claimed': 2, 'done': 3}

    # If a specific server is requested
    if server:
        server = server.lower()
        if server in server_names:
            server_full_name = server_names[server]
        else:
            await ctx.send(f'Unknown server abbreviation "{server}".')
            return

        if server_full_name in guild_quests:
            quest = guild_quests[server_full_name]

            # Dynamic color based on status
            if quest['status'] == 'ongoing':
                embed.color = discord.Color.green()
            elif quest['status'] == 'done':
                embed.color = discord.Color.blue()
            elif quest['status'] == 'claimed':
                embed.color = discord.Color.gold()

            # Display quest details in one line with emoji beside it
            embed.add_field(
                name="\u200b",  # Blank field name to omit "Quest in <server>"
                value=f"🔹 **Server:** {server_full_name} | **Quest:** {quest['name']} | **Status:** `{quest['status'].upper()}`", 
                inline=False
            )
        else:
            embed.add_field(name="\u200b", value='No quests currently', inline=False)
    # If no server is specified, list all quests
    else:
        if guild_quests:
            # Sort the quests based on their status order: ongoing, claimed, done
            sorted_quests = sorted(guild_quests.items(), key=lambda x: status_order.get(x[1]['status'], 4))

            # Adding quest details with emoji identifiers inline for each quest
            for srv, quest in sorted_quests:
                # Dynamic color based on status
                if quest['status'] == 'ongoing':
                    embed.color = discord.Color.green()
                elif quest['status'] == 'done':
                    embed.color = discord.Color.blue()
                elif quest['status'] == 'claimed':
                    embed.color = discord.Color.gold()

                # Show the quest details with emoji beside it
                embed.add_field(
                    name="\u200b",  # Blank field name to omit "Quest in <server>"
                    value=f"🔹 **Server:** {srv} | **Quest:** {quest['name']} | **Status:** `{quest['status'].upper()}`", 
                    inline=False
                )
        else:
            embed.add_field(name='No Quests', value='There are no active quests currently.', inline=False)

    # Send the embed
    await ctx.send(embed=embed)

@bot.command(name='gqu')
async def update_quest(ctx, server: str, status: str):
    global claimed_quests_today
    server = server.lower()

    # Expand shortened server name
    if server in server_names:
        server_full_name = server_names[server]
    else:
        # Send a message with the list of valid server abbreviations
        valid_servers = '\n'.join([f'{abbr} = {full_name}' for abbr, full_name in server_names.items()])
        await ctx.send(f'Unknown server abbreviation "{server}".\nHere is a list of valid server abbreviations:\n{valid_servers}')
        return

    status = status.lower()
    valid_statuses = ['ongoing', 'done', 'claimed']

    if status not in valid_statuses:
        await ctx.send(f'Invalid status. Choose from: {", ".join(valid_statuses)}.')
        return

    if server_full_name in guild_quests:
        if status == 'claimed':
            # Check if the claimed quest limit has been reached
            if claimed_quests_today >= 10:
                await ctx.send(f'The limit of 10 claimed quests has been reached for today.')
                return

            # Remove the quest once it is claimed
            claimed_quests_today += 1
            del guild_quests[server_full_name]
            await ctx.send(f'Quest in server "{server_full_name}" has been claimed and removed from the list.')

        else:
            guild_quests[server_full_name]['status'] = status
            await ctx.send(f'Quest in server "{server_full_name}" updated to "{status}".')
    else:
        await ctx.send(f'No quest found for server "{server_full_name}".')


@bot.command(name='help')
async def help_command(ctx):
    embed = discord.Embed(title="Guild Quest Bot Commands", color=discord.Color.blue())

    # Adding the commands and their descriptions
    embed.add_field(name="!gqa <server> <quest_name>", 
                    value="Add a quest to the specified server. Only one quest can be added per server.", 
                    inline=False)
    embed.add_field(name="!gqu <server> <status>", 
                    value="Update the status of a quest in the specified server. Statuses can be 'ongoing', 'done', or 'claimed'.", 
                    inline=False)
    embed.add_field(name="!gql", 
                    value="List all quests and their statuses. It is automatically sorted for the ongoing to be always on top.", 
                    inline=False)
    embed.add_field(name="!help", 
                    value="Displays this help message.", 
                    inline=False)

    await ctx.send(embed=embed)

    
bot.run(os.getenv('DISCORD_BOT_TOKEN'))