import io
import re
from datetime import datetime
from functools import wraps
from pathlib import Path
from socket import AF_INET, SHUT_RD, SOCK_STREAM, gethostbyname, socket, timeout
from time import time
from typing import Any, Awaitable, Callable, List, Optional, ParamSpec, TypeVar, Union, cast

from discord import (
    Attachment,
    CheckFailure,
    Colour,
    Embed,
    File,
    Forbidden,
    Guild,
    Interaction,
    Member,
    Message,
    PartialEmoji,
    Permissions,
    Role,
    User,
    VoiceChannel, )
from discord.abc import Messageable, Snowflake
from discord.ext.commands import Context, Converter, GuildChannelConverter, check, Cooldown, CooldownMapping
from discord.ext.commands.bot import Bot
from discord.ext.commands.errors import CommandError

from PyDrocsid.bot_mode import BotMode
from PyDrocsid.config import Config
from PyDrocsid.emojis import name_to_emoji
from PyDrocsid.environment import OWNER_IDS, SUDOERS
from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import t
from PyDrocsid.types import GuildMessageable

t = t.g
ZERO_WIDTH_WHITESPACE = "​"


def get_owners(bot: Bot) -> list[User]:
    owners = []
    for owner_id in OWNER_IDS:
        if owner := bot.get_user(owner_id):
            owners.append(owner)
    return owners


@check
def is_sudoer_deco(ctx: Context):
    if not is_sudoer(ctx):
        raise CheckFailure(t.not_in_sudoers_file(ctx.author.mention))
    return True


def is_sudoer(ctx: Context | User | Member) -> bool:
    user_id = ctx.author.id if isinstance(ctx, Context) else ctx.id
    if isinstance(ctx, Context) and ctx.guild and ctx.guild.owner_id == user_id:
        return True

    if user_id not in SUDOERS:
        return False
    return True


T = TypeVar("T")
P = ParamSpec("P")


def interaction_wrapper(f: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
    """Decorator which wraps an async interaction callback function."""

    @wraps(f)
    async def inner(*args: P.args, **kwargs: P.kwargs) -> T:
        interaction: Interaction = args[-1]
        if message := await check_maintenance(interaction.user):
            await interaction.response.send_message(message, ephemeral=True)
            return False
        return await f(*args, **kwargs)

    return inner


async def check_maintenance(user: Member | User | None):
    """
    if True, user is not allowed to do things, because auf maintenance.
    return value is message text to be sent to user
    """
    if Config.BOT_MODE == BotMode.NORMAL:
        return False
    if user is None and Config.BOT_MODE == BotMode.MAINTENANCE:
        return t.maintenance_text
    if Config.BOT_MODE == BotMode.MAINTENANCE:
        from cogs.library.administration.sudo.permissions import SudoPermission

        if not (await SudoPermission.bypass_maintenance.check_permissions(user) or is_sudoer(user)):
            return t.maintenance_text
        return False
    return "Bot deactivated!"


def write_healthcheck():
    with open(Path("health"), "r") as f:
        data = f.readlines()
    if data and data[0].strip().isnumeric():
        data[0] = str(int(datetime.now().timestamp())) + "\n"
    else:
        data = [str(int(datetime.now().timestamp())) + "\n"] + data
    with open(Path("health"), "w+") as f:
        f.writelines(data)


# TODO remove
async def is_teamler(member: Member) -> bool:
    """Return whether a given member is a team member."""

    return await Config.TEAMLER_LEVEL.check_permissions(member)


async def check_wastebasket(
        message: Message, member: Member, emoji: PartialEmoji, footer: str, permission: BasePermission
) -> int | None:
    """
    Check if a user has reacted with :wastebasket: on an embed originally sent by the bot and if the user
    is allowed to delete or collapse this embed.

    :param message: the message the user has reacted on
    :param member: the user who added the reaction
    :param emoji: the emoji the user reacted with
    :param footer: the embed footer to search for
    :param permission: the permission required for deletion
    :return: the id of the user who originally requested this embed if the reacting user is allowed
             to delete this embed, otherwise None
    """

    if emoji.name != name_to_emoji["wastebasket"] or member.bot:
        return None

    # search all embeds for given footer
    for embed in message.embeds:
        if not embed.author:
            continue
        if embed.footer and not embed.footer.text:
            continue

        # pattern = re.escape(footer).replace("\\ ", " ").replace("\\{\\}", "{}").format(".*? (#\d{4})|(#\d)", r"\((\d+)\)")
        pattern = r"\(Author ID: (\d+)\)"
        if (match := re.search(pattern, cast(str, embed.footer.text))) is None:
            continue

        author_id = int(match.group(1))  # id of user who originally requested this embed

        if author_id == member.id or await permission.check_permissions(member):
            # user is authorized to delete this embed
            return author_id

        # user is not authorized -> remove reaction
        try:
            await message.remove_reaction(emoji, cast(Snowflake, member))
        except Forbidden:
            pass
        return None

    return None


def measure_latency() -> float | None:
    """Measure latency to discord.com."""

    host = gethostbyname("discord.com")
    s = socket(AF_INET, SOCK_STREAM)
    s.settimeout(5)

    now = time()

    try:
        s.connect((host, 443))
        s.shutdown(SHUT_RD)
    except (timeout, OSError):
        return None

    return time() - now


def calculate_edit_distance(a: str, b: str) -> int:
    """Calculate edit distance (Levenshtein distance) between two strings."""

    # dp[i][j] contains edit distance between a[:i] and b[:j]
    dp: list[list[int]] = [[max(i, j) for j in range(len(b) + 1)] for i in range(len(a) + 1)]
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            dp[i][j] = min(dp[i - 1][j - 1] + (a[i - 1] != b[j - 1]), dp[i - 1][j] + 1, dp[i][j - 1] + 1)
    return dp[len(a)][len(b)]


async def attachment_to_file(attachment: Attachment) -> File:
    """Convert an attachment to a file"""

    file = io.BytesIO()
    await attachment.save(file)
    return File(file, filename=attachment.filename, spoiler=attachment.is_spoiler())


async def read_normal_message(bot: Bot, channel: GuildMessageable, author: Member) -> tuple[str, list[File]]:
    """Read a message and return content and attachments."""

    def predicate(m: Message) -> bool:
        return m.author == author and m.channel == channel

    msg: Message = await bot.wait_for("message", check=predicate)
    return msg.content, [await attachment_to_file(attachment) for attachment in msg.attachments]


async def read_complete_message(message: Message) -> tuple[str, list[File], Embed | None]:
    """Extract content, attachments and embed from a given message."""

    embed: Embed | None
    for embed in message.embeds:
        if embed.type == "rich":
            break
    else:
        embed = None

    return message.content, [await attachment_to_file(attachment) for attachment in message.attachments], embed


async def send_editable_log(
        channel: Messageable,
        title: str,
        description: str,
        fields: list[tuple[str, str]],
        *,
        colour: int | None = None,
        inline: bool = False,
        force_resend: bool = False,
        force_new_embed: bool = False,
        force_new_field: bool = False,
        **kwargs: Any,
) -> Message:
    """
    Send a log embed into a given channel which can be updated later.

    :param channel: the channel into which the messages should be sent
    :param title: the embed title
    :param description: the embed description
    :param fields: the fields names and values
    :param colour: the embed color
    :param inline: inline parameter of embed field
    :param force_resend: whether to force a resend of the embed instead of editing it
    :param force_new_embed: whether to always send a new embed instead of extending the previous embed
    :param force_new_field: whether to always create a new field instead of editing the last field
    """

    messages: list[Message] = await channel.history(limit=1).flatten()
    edited = False
    if messages and messages[0].embeds and not force_new_embed:  # can extend last embed
        embed: Embed = messages[0].embeds[0]

        # if name or description don't match, a new embed must be created
        if (embed.title or "") == title and (embed.description or "") == description:

            for name, value in fields:
                if embed.fields and embed.fields[-1].name == name and not force_new_field:
                    # can edit last field
                    embed.set_field_at(index=-1, name=name, value=value, inline=inline)
                    edited = True
                elif len(embed.fields) < 25:
                    # can't edit last field -> create a new one
                    embed.add_field(name=name, value=value, inline=inline)
                    edited = True
                else:
                    # can't edit last field, can't create a new one -> create a new embed
                    force_new_embed = True
                    edited = True

                if colour is not None:
                    embed.colour = Colour(colour)

            # update embed
            if not force_new_embed:
                if force_resend:
                    await messages[0].delete()
                    return await channel.send(embed=embed, **kwargs)
                await messages[0].edit(embed=embed, **kwargs)
                return messages[0]
            elif edited:
                if force_resend:
                    await messages[0].delete()
                    await channel.send(embed=embed, **kwargs)
                await messages[0].edit(embed=embed, **kwargs)

    # create and send a new embed
    embed = Embed(title=title, description=description, colour=colour if colour is not None else 0x008080)
    for name, value in fields:
        embed.add_field(name=name, value=value, inline=inline)
    from PyDrocsid.embeds import send_long_embed
    return (await send_long_embed(channel, embed, repeat_title=True))[0]


def check_role_assignable(role: Role) -> None:
    """Check whether the bot could assign and unassign a given role."""

    guild: Guild = role.guild
    me: Member = guild.me

    if not me.guild_permissions.manage_roles:
        raise CommandError(t.role_assignment_error.no_permissions)
    if role > me.top_role:
        raise CommandError(t.role_assignment_error.higher(role, me.top_role))
    if role == me.top_role:
        raise CommandError(t.role_assignment_error.highest(role))
    if role.managed or role == guild.default_role:
        raise CommandError(t.role_assignment_error.managed_role(role))


def check_message_send_permissions(
        channel: GuildMessageable, check_send: bool = True, check_file: bool = False, check_embed: bool = False
) -> None:
    permissions: Permissions = channel.permissions_for(channel.guild.me)
    if not permissions.view_channel:
        raise CommandError(t.message_send_permission_error.cannot_view_channel(channel.mention))
    if check_send and not permissions.send_messages:
        raise CommandError(t.message_send_permission_error.could_not_send_message(channel.mention))
    if check_file and not permissions.attach_files:
        raise CommandError(t.message_send_permission_error.could_not_send_file(channel.mention))
    if check_embed and not permissions.embed_links:
        raise CommandError(t.message_send_permission_error.could_not_send_embed(channel.mention))


def escape_codeblock(string: str):
    prefix = ZERO_WIDTH_WHITESPACE if string.startswith("`") else ""
    return f"``{prefix}{string.replace('`', f'`{ZERO_WIDTH_WHITESPACE}')}``"


class RoleListConverter(Converter[Role]):
    """Return a list of role objects depending on whether the role is existing."""

    async def convert(self, ctx: Context[Bot], arg: str) -> List[Role]:
        guild: Guild = ctx.bot.guilds[0]
        out = []
        for argument in arg.split(" "):
            if not (match := re.match(r"^(<@&!?)?([0-9]{15,20})(?(1)>)$", argument)):
                raise CommandError(f"Role not found : {argument}")

            # find user/role by id
            role_id: int = int(match.group(2))
            if role := guild.get_role(role_id):
                out.append(role)
            else:
                raise CommandError(f"Role not found {role_id}.")
        return out


class DynamicVoiceConverter(Converter[Union[GuildMessageable, VoiceChannel]]):
    """Return a channel object depending on whether the channel is existing."""

    async def convert(self, ctx: Context[Bot], arg: str) -> Optional[Union[GuildMessageable, VoiceChannel]]:
        if match := re.match(r"^.*/channels/\d+/(\d+)$", arg):
            channel = ctx.guild.get_channel(int(match.group(1)))
        else:
            channel = await GuildChannelConverter().convert(ctx, arg)

        if not channel:
            raise CommandError(f"Channel not found: {arg}")
        if not isinstance(channel, GuildMessageable) and not isinstance(channel, VoiceChannel):
            raise CommandError(f"Channel is not a text or voice channel: {arg}")
        return channel
