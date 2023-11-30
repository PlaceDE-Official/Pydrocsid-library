from enum import Enum
from time import time
from typing import Any, Callable

from discord import User
from discord.ext.commands import Cooldown
from discord.ext.commands.cooldowns import C


class UserBucketType(Enum):
    user = 1
    member = 2

    def get_key(self, user: User) -> Any:
        if self is UserBucketType.user or self is UserBucketType.member:
            return user.id

    def __call__(self, user: User) -> Any:
        return self.get_key(user)


class UserCooldownMapping:
    def __init__(
            self,
            original: Cooldown | None,
            type: Callable[[User], Any],
    ) -> None:
        if not callable(type):
            raise TypeError("Cooldown type must be a BucketType or callable")

        self._cache: dict[Any, Cooldown] = {}
        self._cooldown: Cooldown | None = original
        self._type: Callable[[User], Any] = type

    def copy(self) -> "UserCooldownMapping":
        ret = UserCooldownMapping(self._cooldown, self._type)
        ret._cache = self._cache.copy()
        return ret

    @property
    def valid(self) -> bool:
        return self._cooldown is not None

    @property
    def type(self) -> Callable[[User], Any]:
        return self._type

    @classmethod
    def from_cooldown(cls, rate, per, type) -> C:
        return cls(Cooldown(rate, per), type)

    def _bucket_key(self, user: User) -> Any:
        return self._type(user)

    def _verify_cache_integrity(self, current: float | None = None) -> None:
        # we want to delete all cache objects that haven't been used
        # in a cooldown window. e.g. if we have a  command that has a
        # cooldown of 60s, and it has not been used in 60s then that key should be deleted
        current = current or time()
        dead_keys = [k for k, v in self._cache.items() if current > v._last + v.per]
        for k in dead_keys:
            del self._cache[k]

    def create_bucket(self, user: User) -> Cooldown:
        return self._cooldown.copy()  # type: ignore

    def get_bucket(self, user: User, current: float | None = None) -> Cooldown:
        self._verify_cache_integrity(current)
        key = self._bucket_key(user)
        if key not in self._cache:
            bucket = self.create_bucket(user)
            if bucket is not None:
                self._cache[key] = bucket
        else:
            bucket = self._cache[key]

        return bucket

    def update_rate_limit(
            self, user: User, current: float | None = None
    ) -> float | None:
        bucket = self.get_bucket(user, current)
        return bucket.update_rate_limit(current)
