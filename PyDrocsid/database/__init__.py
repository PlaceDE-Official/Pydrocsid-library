import os
import signal
from contextlib import asynccontextmanager
from functools import wraps
from typing import AsyncIterator, Awaitable, Callable, ParamSpec, TypeVar

from sqlalchemy.exc import OperationalError

from .database import Base, UTCDateTime, delete, exists, filter_by, get_database, select
from .. import logger


T = TypeVar("T")
P = ParamSpec("P")


@asynccontextmanager
async def db_context() -> AsyncIterator[None]:
    """Async context manager for database sessions."""
    do_exit = False

    db.create_session()
    try:
        yield
    except SystemExit:
        do_exit = True
        raise
    finally:
        if not do_exit:
            await db.commit()
            await db.close()


def db_wrapper(f: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
    """Decorator which wraps an async function in a database context."""

    @wraps(f)
    async def inner(*args: P.args, **kwargs: P.kwargs) -> T:
        async with db_context():
            try:
                return await f(*args, **kwargs)
            except OperationalError as e:
                if e.args and "1047," in e.args[0] or "1180," in e.args[0]:
                    logger.get_logger("database").warning("Database not usable anymore (1047 or 1180)")
                    os.kill(os.getpid(), signal.SIGTERM)
                    exit(1)

    return inner


# global database connection object
db = get_database()


__all__ = ["db_context", "db_wrapper", "select", "filter_by", "exists", "delete", "db", "Base", "UTCDateTime"]
