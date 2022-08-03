import os
import asyncio
import discord
from discord.ext import tasks
from dotenv import load_dotenv
import channels as channel_api
import datetime
import re
import traceback
import logging

load_dotenv()

# When enabled, the bot will only delete 1 message at a time, allowing you to validate that it is in fact
# deleting from the correct starting point.
DEBUG_MODE = os.getenv('DEBUG_MODE') == 'True'

# The oauth2 token for this bot
TOKEN = os.getenv('DISCORD_TOKEN')

# The log file (only logs actions, not the message content)
LOG_FILE = "log.txt"

# Number of seconds to wait after a change to configuration, before beginning to reap.  This is so users have
# time to catch errors in case they accidentally set the limit too low.
REAP_DELAY_SECONDS = 60

# How frequently to check for messages to be deleted (seconds)
DELETE_MESSAGE_BATCH_FREQUENCY = 60

# How many messages to delete at a time (keep this low, or
DELETE_MESSAGE_BATCH_LIMIT = 20


client = discord.Client()
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s [%(levelname)s]: %(message)s', )

async def show_menu(message):
    await message.channel.send(f'**.reap <max_days>** - *set the maximum number of days to retain messages in '
                               f'the current channel*\n'
                               f'**.unreap** - *stop managing messages in the current channel*\n'
                               f"**.reap_info** - *get the current channel's configuration*\n"
                               f"**.reap_help** - *show all commands*")


async def show_error(message):
    await message.channel.send(f"I didn't understand that command!\n"
                               f"*Example: .reap_help*\n"
                               f"*Example: .reap_info*\n"
                               f'*Example: .reap 120*\n'
                               f'*Example: .unreap*')


@tasks.loop(seconds=DELETE_MESSAGE_BATCH_FREQUENCY)
async def on_tick():
    """ Periodically loop over all the managed channels and request any messages older than the
    configured date (max DELETE_MESSAGE_BATCH_LIMIT).  Then one by one, delete the messages.  When
    this routine runs again, the next batch of messages older than the configured date will be deleted.
    This ensures that we don't flood the discord API with message delete requests or request huge batches
    of messages that would otherwise slow the bot down.
    """
    if client.is_ready():
        channels = await channel_api.get_channels()
        if channels:
            for channel in channels:
                # If the channel disappeared, we should remove it from the config
                try:
                    channel_object = await client.fetch_channel(channel['channel'])
                except discord.errors.NotFound:
                    logging.warning(f"Channel went away, removing it {channel['channel']} "
                                    f"on server {channel['server']}")
                    await channel_api.leave_channel(channel['server'], channel['channel'])
                    continue
                except Exception:
                    logging.exception(f"Unable to get channel {channel['channel']}")
                    continue

                # Don't reap channels who's configuration changed less than REAP_DELAY_SECONDS ago
                current_time = datetime.datetime.now().timestamp()
                start_reaping_at = datetime.datetime.fromtimestamp(channel['config']['updated']) + \
                                   datetime.timedelta(seconds=REAP_DELAY_SECONDS)
                if current_time > start_reaping_at.timestamp():
                    # Request a batch of messages older than the configured date
                    now = datetime.datetime.utcnow()
                    before_date = now - datetime.timedelta(days=channel['config']['max_days'])
                    try:
                        to_reap = await channel_object.history(
                            limit=DELETE_MESSAGE_BATCH_LIMIT,
                            before=before_date
                        ).flatten()
                    except Exception:
                        logging.exception(f"Unable to get history batch {channel_object.name}")
                        continue

                    # Loop over the individual messages and delete them one-by-one
                    if to_reap:
                        logging.info(f'Reaping {len(to_reap)} messages from {channel_object.id} ({channel_object.name})'
                              f'{" in DEBUG_MODE" if DEBUG_MODE else ""}')
                        for message in to_reap:
                            try:
                                await message.delete()
                                if DEBUG_MODE:
                                    # If we're in debug mode, only delete 1 message per channel at a time.
                                    break
                            except Exception:
                                logging.exception(f"Unable to delete message {message.id}")
                else:
                    logging.debug(f"Skipping channel {channel_object.name} because the config was "
                                  f"updated less than {REAP_DELAY_SECONDS} seconds ago")


async def on_join(message):
    """ Start managing  the current channel, or update its existing retention period """
    join_channel = message.content.split(" ", 2)
    if len(join_channel) == 2 and re.match(r"^[0-9]{1,4}$", join_channel[1]):
        max_days = int(join_channel[1])
        if await channel_api.join_channel(
                message.guild.id,
                message.channel.id,
                max_days
        ):
            logging.info(f"{message.author.name}#{message.author.discriminator} updated channel configuration "
                         f"{message.channel.id} ({message.channel.name})"
                         f" in server {message.guild.id} ({message.guild.name}) to {max_days}")
            await message.channel.send(f'I will proudly start reaping {message.channel.name} '
                                       f'for you in about {REAP_DELAY_SECONDS} seconds!\n'
                                       f'Messages older than {max_days} day{"s" if max_days != 1 else ""} '
                                       f'will be removed... It may take a while.')
    else:
        await show_error(message)


async def on_leave(message):
    """ Stop managing the current channel """
    leave_channel = message.content.split(" ")
    if len(leave_channel) == 1:
        if await channel_api.leave_channel(message.guild.id, message.channel.id):
            logging.info(f"{message.author.name}#{message.author.discriminator} removed channel configuration "
                         f"{message.channel.id} ({message.channel.name})"
                         f" in server {message.guild.id} ({message.guild.name})")
            await message.channel.send(f'No longer reaping {message.channel.name}!')
        else:
            await message.channel.send(f"I wasn't reaping this channel!")
    else:
        await show_error(message)


async def on_info(message):
    """ Get the configuration for the current channel """
    channels = [c for c in await channel_api.get_channels()
                if c['server'] == message.guild.id and c['channel'] == message.channel.id]
    if channels:
        info = f"This channel deletes all messages older than "\
                  f" {channels[0]['config']['max_days']} "\
                  f"day{'s' if channels[0]['config']['max_days'] != 1 else ''}!"
        if DEBUG_MODE:
            info += "\n" + f'*{"Operating in debug mode (1 message at a time)" if DEBUG_MODE else ""}*'
        await message.channel.send(info)
    else:
        await message.channel.send(f"I am not reaping this channel.")


@client.event
async def on_message(message):
    """ Handle a new message.  This will delegate to the proper command handler if the message is a command. """
    # Don't consider messages written by this bot
    if client.user.id != message.author.id:
        # only allow administrators to update channel configuration
        permissions = message.author.permissions_in(message.channel)
        command = message.content.split(" ")
        if permissions.administrator:
            # Only administrators can add/remove channels or update their config
            if len(command) >= 2 and command[0] == '.reap':
                await on_join(message)
            elif len(command) >= 1 and command[0] == '.unreap':
                await on_leave(message)

        # We can let anyone get the status
        if len(command) >= 1 and command[0] == ".reap_help":
            await show_menu(message)
        elif len(command) >= 1 and command[0] == ".reap_info":
            await on_info(message)


@client.event
async def on_ready():
    for guild in client.guilds:
        logging.info(f'{client.user} has connected to {guild.id} ({guild.name})!')

    # Set the status of the bot, so people know how to use it.
    game = discord.Game(".reap_help for info")
    await client.change_presence(status=discord.Status.online, activity=game)

# Begin the cleanup background task
on_tick.start()

# Begin the long running client loop
try:
    client.run(TOKEN)
except discord.errors.LoginFailure:
    logging.exception("OAuth2 token is not valid, please update it in .env")
