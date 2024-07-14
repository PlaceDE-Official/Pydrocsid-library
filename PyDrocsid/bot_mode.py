from datetime import datetime
from pathlib import Path

from discord import Game, Status, CustomActivity
from discord.ext.commands import Bot, Context

from PyDrocsid.config import Config
from PyDrocsid.database import db_wrapper
from PyDrocsid.logger import get_logger
from PyDrocsid.settings import SettingsModel
from PyDrocsid.translations import t
from PyDrocsid.types import BotMode


logger = get_logger(__name__)

t = t.g


# TODO ntfy endpoint


def mode_args(ctx: Context):
    now = datetime.utcnow()
    return ctx.author.mention, ctx.author.name, ctx.author.id, now.strftime("%d.%m.%Y, %H:%M:%S"), now.timestamp()


def get_mode_change_message(ctx: Context):
    args = mode_args(ctx)
    if Config.BOT_MODE == BotMode.NORMAL:
        return t.bot_modes.normal(*args)
    elif Config.BOT_MODE == BotMode.MAINTENANCE:
        return t.bot_modes.maintenance(*args)
    elif Config.BOT_MODE == BotMode.STOPPED:
        return t.bot_modes.stopped(*args)
    elif Config.BOT_MODE == BotMode.KILLED:
        return t.bot_modes.killed(*args)


def check_deactivation():
    Config.BOT_MODE = BotMode.NORMAL

    found = []
    for path_string in ["health", Config.VOLUME_PATH]:
        path = Path(path_string)
        if path.is_dir():
            path = path.joinpath("data")
        if not path.exists():
            continue
        with open(path, "r") as f:
            data = f.read().splitlines()
            for mode in BotMode:
                if any(mode.value in line for line in data):
                    found.append(path.absolute())
                    if mode < Config.BOT_MODE:
                        Config.BOT_MODE = mode

    if Config.BOT_MODE in [BotMode.STOPPED, BotMode.KILLED]:
        from PyDrocsid.environment import TOKEN

        disabled_bot = Bot()

        @disabled_bot.event
        async def on_ready():
            await disabled_bot.change_presence(
                status=Status.idle,
                activity=CustomActivity(name=Config.BOT_MODE.bot_activity)
            )

        logger.warning(
            f"\nBot deactivated, clear contents of files {' and '.join(map(str, found))}"
            f" and restart to continue!\n"
            f"Do NOT delete the files itself!\n"
            f"It will break the volume or the healthcheck!!\n"
            f"Sleeping!"
        )
        disabled_bot.run(TOKEN)


@db_wrapper
async def write_status(text, bot_mode):
    await SettingsModel.set(str, "bot_mode", bot_mode.value, True)
    for path_string in ["health", Config.VOLUME_PATH]:
        try:
            path = Path(path_string)
            if not path.parent.exists():
                continue
            if path.is_dir():
                path = path.joinpath("data")
            with open(path, "w+") as f:
                f.write("Bot mode: " + Config.BOT_MODE.value + "\n")
                f.write(text)
        except PermissionError:
            logger.error(f"Permission denied for {path_string} or contents")
            logger.error("If the volume is not writable, killing the bot might not work properly in docker!")
