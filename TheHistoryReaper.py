import os
import asyncio
import discord
from discord.ext import tasks
from dotenv import load_dotenv
import channels as channel_api
import datetime
import re
import traceback

# Number of seconds to wait after a change to configuration, before beginning to reap.  This is so users have
# time to catch errors in case they accidentally set the limit too low.
REAP_DELAY_SECONDS = 15

# How frequently to check for messages to be deleted (seconds)
DELETE_MESSAGE_BATCH_FREQUENCY = 3

# How many messages to delete at a time (keep this low, or
DELETE_MESSAGE_BATCH_LIMIT = 4


load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
client = discord.Client()


@tasks.loop(seconds=DELETE_MESSAGE_BATCH_FREQUENCY)
async def on_tick():
    if client.is_ready():
        channels = await channel_api.get_channels()
        if channels:
            for channel in channels:
                # If the channel disappeared, we should remove it from the config
                try:
                    channel_object = await client.fetch_channel(channel['channel'])
                except discord.errors.NotFound:
                    print(f"Channel went away, removing it {channel['channel']} on server {channel['server']}")
                    await channel_api.leave_channel(channel['server'], channel['channel'])
                    continue

                current_time = datetime.datetime.now().timestamp()
                start_reaping_at = datetime.datetime.fromtimestamp(channel['config']['updated']) + \
                                   datetime.timedelta(seconds=REAP_DELAY_SECONDS)
                if current_time > start_reaping_at.timestamp():
                    now = datetime.datetime.utcnow()
                    before_date = now - datetime.timedelta(days=channel['config']['max_days'])

                    to_reap = await channel_object.history(
                        limit=DELETE_MESSAGE_BATCH_LIMIT,
                        before=before_date
                    ).flatten()

                    print(f'Reaping {len(to_reap)} messages from {channel_object.name}')

                    for message in to_reap:
                        try:
                            await message.delete()
                        except Exception:
                            print(f"Unable to delete message {message.id}")
                            traceback.print_exc()
                else:
                    print(f"Skipping channel {channel_object.name} because the config was "
                          f"updated less than {REAP_DELAY_SECONDS} seconds ago")


async def on_join(message):
    join_channel = message.content.split(" ", 2)
    if len(join_channel) == 2 and re.match(r"^[0-9]{1,4}$", join_channel[1]):
        max_days = int(join_channel[1])
        if await channel_api.join_channel(
                message.guild.id,
                message.channel.id,
                max_days
        ):
            await message.channel.send(f'I will proudly start reaping {message.channel.name} '
                                       f'in {REAP_DELAY_SECONDS} seconds sir!')
            await message.channel.send(
                f'Messages older than {max_days} day{"s" if max_days != 1 else ""} will be removed'
            )
        else:
            await message.channel.send(f'Already reaping this channel sir!')
    else:
        await message.channel.send(f"I didn't understand that sir!")
        await message.channel.send(f'Example: .reap 120')


async def on_leave(message):
    leave_channel = message.content.split(" ")
    if len(leave_channel) == 1:
        if await channel_api.leave_channel(message.guild.id, message.channel.id):
            await message.channel.send(f'No longer reaping {message.channel.name} sir!')
        else:
            await message.channel.send(f"I wasn't reaping this channel sir!")
    else:
        await message.channel.send(f"I didn't understand that sir!")
        await message.channel.send(f"Example: .unreap")


@client.event
async def on_message(message):
    if client.user.id != message.author.id:
        # only allow administrators to issue commands
        permissions = message.author.permissions_in(message.channel)
        if permissions.administrator:
            command = message.content.split(" ")
            if len(command) >= 2 and command[0] == '.reap':
                await on_join(message)
            elif len(command) >= 1 and command[0] == '.unreap':
                await on_leave(message)


@client.event
async def on_ready():
    for guild in client.guilds:
        print(f'{client.user} has connected to Discord {guild.name}!')

# Begin the cleanup background task
on_tick.start()

# Begin the long running client loop
client.run(TOKEN)
