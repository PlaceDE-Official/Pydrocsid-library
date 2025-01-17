from os import getenv


def get_bool(key: str, default: bool) -> bool:
    """Get a boolean from an environment variable."""

    return getenv(key, str(default)).lower() in ("true", "t", "yes", "y", "1")


TOKEN: str | None = getenv("TOKEN")  # bot token
LOG_LEVEL: str = getenv("LOG_LEVEL", "INFO")
PYCORD_LOG_LEVEL: str = getenv("PYCORD_LOG_LEVEL", "ERROR")

# database configuration
DB_DRIVER: str = getenv("DB_DRIVER", "mysql+aiomysql")
DB_HOST: str = getenv("DB_HOST", "localhost")
DB_PORT: int = int(getenv("DB_PORT", "3306"))
DB_DATABASE: str = getenv("DB_DATABASE", "bot")
DB_USERNAME: str = getenv("DB_USERNAME", "bot")
DB_PASSWORD: str = getenv("DB_PASSWORD", "bot")
POOL_RECYCLE: int = int(getenv("POOL_RECYCLE", 300))
POOL_SIZE: int = int(getenv("POOL_SIZE", 20))
MAX_OVERFLOW: int = int(getenv("MAX_OVERFLOW", 20))
SQL_SHOW_STATEMENTS: bool = get_bool("SQL_SHOW_STATEMENTS", False)

SENTRY_DSN: str | None = getenv("SENTRY_DSN")  # sentry data source name
SENTRY_ENVIRONMENT: str = getenv("SENTRY_ENVIRONMENT", "production")
GITHUB_TOKEN: str | None = getenv("GITHUB_TOKEN")  # github personal access token

OWNER_IDS: list[int] = [int(x) for x in map(lambda x: x.strip(), getenv("OWNER_IDS", "").split(",")) if x]
SUDOERS: list[int] = [int(x) for x in map(lambda x: x.strip(), getenv("SUDOERS", "").split(",")) if x]
ADVENT_PATH: str = getenv("ADVENT_PATH", "/tmp/advent")

DISABLED_COGS: set[str] = set(map(str.lower, getenv("DISABLED_COGS", "").split(",")))

# redis configuration
REDIS_HOST: str = getenv("REDIS_HOST", "localhost")
REDIS_PORT: int = int(getenv("REDIS_PORT", "6379"))
REDIS_DB: int = int(getenv("REDIS_DB", "0"))

CACHE_TTL: int = int(getenv("CACHE_TTL", 8 * 60 * 60))
RESPONSE_LINK_TTL: int = int(getenv("RESPONSE_LINK_TTL", 2 * 60 * 60))
PAGINATION_TTL: int = int(getenv("PAGINATION_TTL", 2 * 60 * 60))

# configuration for reply feature
REPLY: bool = get_bool("REPLY", True)
MENTION_AUTHOR: bool = get_bool("MENTION_AUTHOR", True)

DISABLE_PAGINATION: bool = get_bool("DISABLE_PAGINATION", False)
CLUSTER_NODE: str = getenv("CLUSTER_NODE", None)
CLUSTER_NODE_ORDER: list[str] = [x for x in map(lambda x: x.strip().lower(), getenv("CLUSTER_NODE_ORDER", "").split(",")) if x]
