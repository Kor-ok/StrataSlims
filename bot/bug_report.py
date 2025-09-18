import discord

from config import get_bot_alerts_routes

_bot_alert_routes = get_bot_alerts_routes()
BOT_LOGS_CHANNEL_ID = _bot_alert_routes.get("BOT_LOGS_CHANNEL_ID", None)
BOT_LOGS_WEBHOOK = _bot_alert_routes.get("BOT_LOGS_WEBHOOK", None)

BUG_REPORT_EMOTE = '🐛'

STRATA_BOT_APP_ID = 1054345210693431366

async def on_bug_report_emote(self, payload: discord.RawReactionActionEvent):
        """
        If a user reacts with 🐛 :bug: to: 
            a post from the bot with App ID = STRATA_BOT_APP_ID
            or if the bot has used a webhook to post then author_id = STRATA_BOT_APP_ID
        then post a copy of that message to BOT_LOGS_CHANNEL_ID, BOT_LOGS_WEBHOOK
        """
        # Get the App ID of the message that was reacted to
        channel = self.get_channel(payload.channel_id)
        if not channel or not isinstance(channel, discord.TextChannel):
            return
        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            return
        app_id = message.application_id
        author_id = message.author.id
        jump_url = message.jump_url

        if (app_id == STRATA_BOT_APP_ID) or (author_id == STRATA_BOT_APP_ID):
            
            # Prepare the report message
            report_message = f"Bug report by <@{payload.user_id}>\n{jump_url}"
            
            print("Bug report detected:", report_message)
            
            # Send to BOT_LOGS_CHANNEL_ID
            if BOT_LOGS_CHANNEL_ID and BOT_LOGS_WEBHOOK:
                try:
                    log_channel = self.get_channel(BOT_LOGS_CHANNEL_ID)
                    if log_channel is None:
                        log_channel = await self.fetch_channel(BOT_LOGS_CHANNEL_ID)
                    if isinstance(log_channel, discord.TextChannel):
                        await log_channel.send(
                            content=report_message,
                            allowed_mentions=discord.AllowedMentions.none(),
                            mention_author=False,
                            silent=True
                        )
                except Exception as e:
                    print(f"Failed post to log channel: {e}")