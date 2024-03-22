import re

from discord import Guild, HTTPException, Member, NotFound, PartialEmoji, User, ScheduledEvent
from discord.ext.commands import Bot
from discord.ext.commands.context import Context
from discord.ext.commands.converter import ColorConverter, Converter, PartialEmojiConverter, CONVERTER_MAPPING
from discord.ext.commands.errors import BadArgument

from PyDrocsid.emojis import emoji_to_name
from PyDrocsid.translations import t


t = t.g




class EmojiConverter(PartialEmojiConverter):
    """Emoji converter which also supports unicode emojis."""

    async def convert(self, ctx: Context[Bot], argument: str) -> PartialEmoji:
        try:
            return await super().convert(ctx, argument)
        except BadArgument:
            pass

        if argument not in emoji_to_name:
            raise BadArgument

        connection = ctx.bot._connection  # noqa
        return PartialEmoji.with_state(connection, animated=False, name=argument, id=None)


class Color(Converter[int]):
    """Color converter which also supports hex codes."""

    async def convert(self, ctx: Context[Bot], argument: str) -> int:
        try:
            return (await ColorConverter().convert(ctx, argument)).value
        except BadArgument:
            pass

        if not re.match(r"^[0-9a-fA-F]{6}$", argument):
            raise BadArgument(t.invalid_color)
        return int(argument, 16)


class UserMemberConverter(Converter[User | Member]):
    """Return a member or user object depending on whether the user is currently a guild member."""

    async def convert(self, ctx: Context[Bot], argument: str) -> User | Member:
        guild: Guild = ctx.bot.guilds[0]

        if not (match := re.match(r"^(<@!?)?([0-9]{15,20})(?(1)>)$", argument)):
            raise BadArgument(t.user_not_found)

        # find user/member by id
        user_id: int = int(match.group(2))
        if member := guild.get_member(user_id):
            return member
        try:
            return await ctx.bot.fetch_user(user_id)
        except (NotFound, HTTPException):
            raise BadArgument(t.user_not_found)


class ScheduledEventConverter(Converter[ScheduledEvent]):
    """Return a scheduled event."""

    async def convert(self, ctx: Context[Bot], argument: str) -> ScheduledEvent:
        guild: Guild = ctx.bot.guilds[0]

        for event in guild.scheduled_events:
            if event.name == argument:
                return event

        if not (match := re.match(r"^(<@!?)?([0-9]{15,20})(?(1)>)$", argument)):
            raise BadArgument(t.event_not_found)

        # find user/member by id
        event_id: int = int(match.group(2))
        if event := guild.get_scheduled_event(event_id):
            return event
        try:
            return await guild.fetch_scheduled_event(event_id)
        except (NotFound, HTTPException):
            raise BadArgument(t.event_not_found)


CONVERTER_MAPPING.update({ScheduledEvent: ScheduledEventConverter})
