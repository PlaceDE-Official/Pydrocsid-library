from enum import Enum
from functools import total_ordering
from typing import TypeAlias

from discord import TextChannel, Thread, VoiceChannel

from PyDrocsid.translations import t


t = t.g

# TODO add threads https://docs.pycord.dev/en/stable/api/utils.html#discord.utils.get_or_fetch
# TODO add stage channels when library update
GuildMessageable: TypeAlias = TextChannel | VoiceChannel


@total_ordering
class BotMode(Enum):
    _order_: int

    NORMAL = "normal", t.bot_activity.normal, 10
    MAINTENANCE = "maintenance", t.bot_activity.maintenance, 2
    STOPPED = "stopped", t.bot_activity.deactivated, 1
    KILLED = "killed", t.bot_activity.deactivated, 0

    def __new__(cls, *args, **kwargs):
        obj = object.__new__(cls)
        obj._value_ = args[0]
        return obj

    # ignore the first param since it's already set by __new__
    def __init__(self, _: str, bot_activity: str = "", order: int = 100):
        self._bot_activity_ = bot_activity
        self._order_ = order

    def __str__(self):
        return self.value

    # this makes sure that the description is read-only
    @property
    def bot_activity(self):
        return self._bot_activity_

    def __le__(self, other):
        return self._order_ < other._order_
