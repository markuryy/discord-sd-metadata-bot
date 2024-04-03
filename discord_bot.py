import os
import discord
from discord.ext import commands
from sd_prompt_reader.image_data_reader import ImageDataReader
from datetime import datetime, timedelta

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.reactions = True
intents.guilds = True
intents.dm_messages = True

bot = commands.Bot(command_prefix='!', intents=intents)
excluded_channels = set()
reaction_cooldown = {}

# Variable to enable/disable star emoji reaction
ENABLE_STAR_EMOJI_REACTION = True

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    print('Bot is ready. Press Ctrl+C to stop.')

@bot.command(name='exclude')
@commands.has_permissions(administrator=True)
async def exclude_channel(ctx):
    channel = ctx.channel
    excluded_channels.add(channel.id)
    print(f"[{ctx.guild.name}] Channel {channel.name} is now excluded from image analysis.")
    await ctx.send(f'Channel {channel.mention} is now excluded from image analysis.')

@bot.command(name='include')
@commands.has_permissions(administrator=True)
async def include_channel(ctx):
    channel = ctx.channel
    if channel.id in excluded_channels:
        excluded_channels.remove(channel.id)
        print(f"[{ctx.guild.name}] Channel {channel.name} is no longer excluded from image analysis.")
        await ctx.send(f'Channel {channel.mention} is no longer excluded from image analysis.')
    else:
        print(f"[{ctx.guild.name}] Channel {channel.name} is not currently excluded.")
        await ctx.send(f'This channel is not currently excluded.')

@bot.event
async def on_message(message):
    if message.channel.id not in excluded_channels:
        await process_message(message)
    await bot.process_commands(message)

async def process_message(message):
    for attachment in message.attachments:
        if attachment.content_type.startswith('image/'):
            print(f"[{message.guild.name}] Detected image in message {message.id} from channel #{message.channel.name}")
            has_metadata = False
            try:
                image_data = await attachment.read()
                with open('temp_image', 'wb') as f:
                    f.write(image_data)
                reader = ImageDataReader('temp_image')
                if reader.tool:
                    has_metadata = True
            except Exception as e:
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                print(f"[{current_time}][{message.guild.name}] Error processing image: {e}")
            finally:
                if os.path.exists('temp_image'):
                    os.remove('temp_image')
            if has_metadata:
                await message.add_reaction('🔍')
            else:
                await message.add_reaction('✉️')
            # React with star emoji if enabled
            if ENABLE_STAR_EMOJI_REACTION:
                await message.add_reaction('⭐')

@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return

    channel = bot.get_channel(payload.channel_id)
    if channel is None or isinstance(channel, discord.DMChannel):
        await handle_dm_reaction_add(payload)
    else:
        message = await channel.fetch_message(payload.message_id)
        user = bot.get_user(payload.user_id) or await bot.fetch_user(payload.user_id)
        await handle_guild_reaction_add(message, payload.emoji, user)

async def handle_dm_reaction_add(payload):
    if str(payload.emoji) == '❌':
        channel = bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        await message.delete()

async def handle_guild_reaction_add(message, emoji, user):
    if message.channel.id in excluded_channels or user.id == bot.user.id:
        return
    
    if user.id in reaction_cooldown and reaction_cooldown[user.id] > datetime.utcnow():
        return

    if str(emoji) == '🔍':
        metadata = await get_metadata(message, user)
        if metadata:
            sent_message = await user.send(metadata)
            await sent_message.add_reaction('❌')
            reaction_cooldown[user.id] = datetime.utcnow() + timedelta(minutes=5)
    elif str(emoji) == '✉️':
        image_info = await get_image_info(message)
        if image_info:
            sent_message = await user.send(image_info)
            await sent_message.add_reaction('❌')
            reaction_cooldown[user.id] = datetime.utcnow() + timedelta(minutes=5)

@bot.event
async def on_reaction_remove(reaction, user):
    if user != bot.user and isinstance(reaction.message.channel, discord.DMChannel):
        if str(reaction.emoji) == '❌':
            await reaction.message.delete()

async def get_metadata(message, user):
    base_message_content = f"**Original Message**: {message.jump_url}\n\n"

    image_count = len(message.attachments)
    for index, attachment in enumerate(message.attachments, start=1):
        if attachment.content_type.startswith('image/'):
            # Initialize the metadata content with the base message for context.
            metadata_content = base_message_content

            try:
                # Read the image data and process it.
                image_data = await attachment.read()
                with open('temp_image', 'wb') as f:
                    f.write(image_data)

                reader = ImageDataReader('temp_image')
                metadata_content += f"**Image {index}/{image_count}**:\n"
                metadata_content += f"URL: {attachment.url}\n"
                metadata_content += f"Tool: {reader.tool}\n"
                
                # Add specific metadata based on the tool used.
                if reader.tool == "A1111/Forge":
                    metadata_content += f"Prompt:\n```{reader.positive}```\n"
                    if reader.negative:
                        metadata_content += f"Negative Prompt:\n```{reader.negative}```\n"
                    metadata_content += f"Settings:\n```Steps: {reader.parameter['steps']}, Sampler: {reader.parameter['sampler']}, "
                    metadata_content += f"CFG scale: {reader.parameter['cfg']}, Seed: {reader.parameter['seed']}, "
                    metadata_content += f"Size: {reader.parameter['size']}, Model: {reader.parameter['model']}```\n\n"
                else:
                    metadata_content += f"Prompt:\n```{reader.positive}```\n"
                    if reader.negative:
                        metadata_content += f"Negative Prompt:\n```{reader.negative}```\n"
                    metadata_content += f"Settings:\n```{reader.setting}```\n"
                    metadata_content += f"Parameters:\n```{reader.parameter}```\n\n"
                
                # Immediately send this image's metadata as a separate message.
                await user.send(metadata_content)

            except Exception as e:
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                print(f"[{current_time}][{message.guild.name}] Error processing image: {e}")
            finally:
                # Clean up the temporary image file.
                if os.path.exists('temp_image'):
                    os.remove('temp_image')

async def get_image_info(message):
    image_info = f"**Original Message**: {message.jump_url}\n\n"
    image_count = len(message.attachments)
    for index, attachment in enumerate(message.attachments, start=1):
        if attachment.content_type.startswith('image/'):
            image_info += f"**Image {index}/{image_count}**:\n"
            image_info += f"URL: {attachment.url}\n\n"
    return image_info

with open('bot_token.txt', 'r') as f:
    bot_token = f.read().strip()

bot.run(bot_token)