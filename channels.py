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
    async with channel_lock:
        # Get the current list of channel configurations
        current_channels = _get_channels()

        # dont add it if we already have it
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

        # Add the new channel
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

        with open(CHANNEL_FILE, 'w') as channels:
            yaml.dump(current_channels, channels)

        return True


async def leave_channel(server_id, channel_id):
    async with channel_lock:
        # Get the list of channel configurations
        original_channels = _get_channels()

        new_channels = [
            channel for channel in original_channels if
            channel['channel'] != channel_id and channel['server'] == server_id
        ]
        with open(CHANNEL_FILE, 'w') as channels:
            yaml.dump(new_channels, channels)

        # Return true if the channel was found and removed
        return len(new_channels) != len(original_channels)


async def get_channels():
    async with channel_lock:
        # return the current channel configuraitons
        return _get_channels()
