from typing import TypeAlias

from discord import TextChannel, Thread, VoiceChannel


GuildMessageable: TypeAlias = TextChannel | Thread | VoiceChannel
