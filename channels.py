import asyncio
import yaml
import datetime

CHANNEL_FILE = "channels.yaml"

channel_lock = asyncio.Lock()


def _get_channels():
    """ Get the list of channel configurations (no concurrency protection)
    :return: The array of channel configurations
    """
    # Get the current list of channels
    with open(CHANNEL_FILE) as channels:
        original_channels = yaml.load(channels, Loader=yaml.FullLoader)

    if original_channels is None:
        original_channels = []

    return original_channels


async def join_channel(server_id, channel_id, max_days=99999999):
    """ Add or update a channel's configuration to the list of managed channels
    :param server_id: The numeric ID of the guild/server
    :param channel_id: The numeric ID of the channel
    :param max_days: The maximum number of days to retain messages
    """
    # Make sure we have exclusive access to the channel configuration file
    async with channel_lock:
        # Get the current list of channel configurations
        current_channels = _get_channels()

        # Update it if we already have the channel
        found = False
        for channel in current_channels:
            if channel['channel'] == channel_id and channel['server'] == server_id:
                channel['config'].update(
                    {
                        'max_days': max_days,
                        'updated': datetime.datetime.now().timestamp()
                    }
                )
                found = True

        # Add the channel if its not already in the file
        if not found:
            current_channels = current_channels + [
                {
                    'channel': channel_id,
                    'server': server_id,
                    'config': {
                        'max_days': max_days,
                        'updated': datetime.datetime.now().timestamp()
                    }
                }
            ]

        # Write the updated channel file
        with open(CHANNEL_FILE, 'w') as channels:
            yaml.dump(current_channels, channels)


async def leave_channel(server_id, channel_id):
    """ Remove a channel from the list of managed channels
    :param server_id: The numeric guild/server ID
    :param channel_id: The numeric channel ID
    :return: True if the channel was being monitored but was removed, False if it was not being monitored
                in the first place.
    """
    # Make sure we have exclusive access to the channel configuration file
    async with channel_lock:
        # Get the list of channel configurations
        original_channels = _get_channels()

        # Remove the one with the matching ID's
        new_channels = [
            channel for channel in original_channels if
            channel['channel'] != channel_id and channel['server'] == server_id
        ]

        # Write the new configuration
        with open(CHANNEL_FILE, 'w') as channels:
            yaml.dump(new_channels, channels)

        # Return true if the channel was found and removed
        return len(new_channels) != len(original_channels)


async def get_channels():
    # Make sure we have exclusive access to the channel configuration file
    async with channel_lock:
        # return the current channel configuraitons
        return _get_channels()
