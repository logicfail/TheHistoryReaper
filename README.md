# TheHistoryReaper
A discord bot that is capable of deleting all messages older than a configured number of days.  Unlike other implementations, this bot is capable of deleting messages older than 14 days.

## Behavior
This bot will periodically request batches of messages older than the configured date.  It will then delete those messages one-by-one.  When initially configuring a channel with a lot of messages that should be deleted, the bot may take several days to catch-up.

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

