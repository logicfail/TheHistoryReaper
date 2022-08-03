import asyncio
import yaml
import datetime

CHANNEL_FILE = "channels.yaml"

channel_lock = asyncio.Lock()


async def join_channel(server_id, channel_id, max_days=99999999):
    async with channel_lock:
        with open(CHANNEL_FILE) as channels:
            current_channels = yaml.load(channels, Loader=yaml.FullLoader)

        if current_channels is None:
            current_channels = []

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
        with open(CHANNEL_FILE) as channels:
            original_channels = yaml.load(channels, Loader=yaml.FullLoader)

        if original_channels is None:
            original_channels = []

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
        with open(CHANNEL_FILE) as channels:
            return yaml.load(channels, Loader=yaml.FullLoader)
