from __future__ import annotations

from datetime import datetime
from typing import Union

from discord.utils import utcnow
from sqlalchemy import Boolean, Column, String

from PyDrocsid.database import Base, db, UTCDateTime, select


class ClusterNode(Base):
    __tablename__ = "cluster_node"

    node_name: Union[Column, str] = Column(String(64), primary_key=True, unique=True)
    timestamp: Union[Column, datetime] = Column(UTCDateTime)
    active: Union[Column, bool] = Column(Boolean)
    disabled: Union[Column, bool] = Column(Boolean)
    transferring: Union[Column, bool] = Column(Boolean)

    @staticmethod
    async def create(node_name: str, active: bool) -> ClusterNode:
        row = ClusterNode(
            node_name=node_name.lower(),
            active=active,
            timestamp=utcnow(),
            disabled=False,
            transferring=False,
        )
        await db.add(row)
        return row

    @staticmethod
    async def reset_temp_values(node_name: str) -> ClusterNode:
        if not (row := await db.get(ClusterNode, node_name=node_name.lower())):
            row = await ClusterNode.create(node_name, False)
        row.timestamp = utcnow()
        row.active = False
        row.transferring = False
        return row

    @staticmethod
    async def update_active(node_name: str, active: bool) -> ClusterNode:
        if not (row := await db.get(ClusterNode, node_name=node_name.lower())):
            row = await ClusterNode.create(node_name, active)
        row.timestamp = utcnow()
        row.active = active
        return row

    @staticmethod
    async def update_timestamp(node_name: str) -> ClusterNode:
        if not (row := await db.get(ClusterNode, node_name=node_name.lower())):
            row = await ClusterNode.create(node_name, False)
        row.timestamp = utcnow()
        return row

    @staticmethod
    async def get_all() -> list[ClusterNode]:
        return await db.all(select(ClusterNode))

    @staticmethod
    async def get(node_name: str) -> ClusterNode | None:
        return await db.get(ClusterNode, node_name=node_name.lower())
