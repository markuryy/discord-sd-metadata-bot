import os
import asyncio
import discord
from discord.ext import commands
from sd_prompt_reader.image_data_reader import ImageDataReader
from datetime import datetime, timedelta

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.reactions = True

bot = commands.Bot(command_prefix='!', intents=intents)
bound_channel = None
reaction_cooldown = {}  # Dictionary to store user reaction cooldowns

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    print('Bot is ready. Press Ctrl+C to stop.')

@bot.command(name='bind')
@commands.has_permissions(administrator=True)
async def bind_channel(ctx):
    global bound_channel
    bound_channel = ctx.channel
    await ctx.send(f'Channel {ctx.channel.mention} is now bound for image analysis.')

@bot.command(name='unbind')
@commands.has_permissions(administrator=True)
async def unbind_channel(ctx):
    global bound_channel
    if bound_channel == ctx.channel:
        bound_channel = None
        await ctx.send(f'Channel {ctx.channel.mention} is no longer bound for image analysis.')
    else:
        await ctx.send(f'This channel is not currently bound.')

@bot.event
async def on_message(message):
    if message.channel == bound_channel:
        has_metadata = False
        for attachment in message.attachments:
            if attachment.content_type.startswith('image/'):
                try:
                    image_data = await attachment.read()
                    with open('temp_image', 'wb') as f:
                        f.write(image_data)
                    reader = ImageDataReader('temp_image')
                    if reader.tool:
                        has_metadata = True
                except Exception as e:
                    print(f"Error processing image: {e}")
                finally:
                    if os.path.exists('temp_image'):
                        os.remove('temp_image')
        if has_metadata:
            await message.add_reaction('🔍')
    await bot.process_commands(message)

@bot.event
async def on_reaction_add(reaction, user):
    if user != bot.user and str(reaction.emoji) == '🔍':
        message = reaction.message
        if user.id in reaction_cooldown and reaction_cooldown[user.id] > datetime.utcnow():
            print(f"User {user} is on cooldown. Skipping reaction.")
            return
        metadata = f"**Original Message**: {message.jump_url}\n\n"
        image_count = len(message.attachments)
        for index, attachment in enumerate(message.attachments, start=1):
            if attachment.content_type.startswith('image/'):
                try:
                    image_data = await attachment.read()
                    with open('temp_image', 'wb') as f:
                        f.write(image_data)
                    reader = ImageDataReader('temp_image')
                    metadata += f"**Image {index}/{image_count}**:\n"
                    metadata += f"URL: {attachment.url}\n"
                    metadata += f"Tool: {reader.tool}\n"
                    if reader.tool == "A1111 webUI":
                        metadata += f"Prompt:\n```{reader.positive}```\n"
                        if reader.negative:
                            metadata += f"Negative Prompt:\n```{reader.negative}```\n"
                        metadata += f"Settings:\n```Steps: {reader.parameter['steps']}, Sampler: {reader.parameter['sampler']}, "
                        metadata += f"CFG scale: {reader.parameter['cfg']}, Seed: {reader.parameter['seed']}, "
                        metadata += f"Size: {reader.parameter['size']}, Model: {reader.parameter['model']}```\n\n"
                    else:
                        metadata += f"Prompt:\n```{reader.positive}```\n"
                        if reader.negative:
                            metadata += f"Negative Prompt:\n```{reader.negative}```\n"
                        metadata += f"Settings:\n```{reader.setting}```\n"
                        metadata += f"Parameters:\n```{reader.parameter}```\n\n"
                except Exception as e:
                    print(f"Error processing image: {e}")
                finally:
                    if os.path.exists('temp_image'):
                        os.remove('temp_image')
        if metadata:
            try:
                await user.send(metadata)
                reaction_cooldown[user.id] = datetime.utcnow() + timedelta(minutes=5)  # 5-minute cooldown
            except discord.Forbidden:
                print(f"Failed to send DM to user {user}. DMs may be disabled.")

# bot.run('YOUR_BOT_TOKEN')