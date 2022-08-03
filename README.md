# TheHistoryReaper
A discord bot that is capable of deleting all messages older than a configured number of days.  Unlike other implementations, this bot is capable of deleting messages older than 14 days.

## Behavior
This bot will periodically request batches of messages older than the configured date.  It will then delete those messages one-by-one.  When initially configuring a channel with a lot of messages that should be deleted, the bot may take several days to catch-up.

## Bot Permissions
In order for this bot to work, you will need to grant it the following permissions:

- Read Messages / View Channels
- Send Messages
- Manage Messages
- Manage Threads
- Read Message History

## Installation
1. Setup a new application in discord developer portal.
2. Add a bot to your application.
3. Configure the bot to have "Message Content Intent"
4. On the 'bot' page, select 'Reset Token' and then copy the new token
5. Paste the bot token in the .env file
6. Open "OAuth2 -> URL Generator" and select the 'bot' scope
7. Select all the required permissions
8. Copy the URL and paste it into your browser
9. Allow the bot to join your server (you must have Manage Server permissions)
10. Ensure 'channels.yaml' and 'log.txt' are writiable (chmod 666)
11. Install python dependencies
    - pip install discord
    - pip install python-dotenv
    - pip install pyyaml
12. Run TheHistoryReaper.py
13. When you're satisfied the bot is working properly, edit .env to turn off DEBUG_MODE, then restart TheHistoryReaper.py

## Usage
You can enable and disable history deletion in any channel by using the bot's commands.  If you make a change to a channels configuration, it will freeze the deletion process for a period of time, to allow you to fix any mistakes before messages begin getting deleted.

### Get the list of commands
.reap_help

### Get the current channels configuration
.reap_info

### Enable history deletion in the current channel or change the number of days (requires administrative permissions)
.reap <after_this_number_of_days>

### Disable history deletion in the current channel (requires administrative permission)
.unreap


