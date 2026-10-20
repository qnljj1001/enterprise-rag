"""数据库连接与会话工厂。"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    pass


class Database:
    def __init__(self, url: str) -> None:
        connect_args: dict[str, object] = {}
        poolclass = None
        if url.startswith("sqlite"):
            connect_args["check_same_thread"] = False
            if ":memory:" in url:
                poolclass = StaticPool
        self.engine = create_engine(
            url,
            future=True,
            pool_pre_ping=not url.startswith("sqlite"),
            connect_args=connect_args,
            poolclass=poolclass,
        )
        self.SessionLocal = sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
            class_=Session,
        )

    def create_all(self) -> None:
        # 确保模型已注册到 Base.metadata
        from . import models  # noqa: F401

        Base.metadata.create_all(self.engine)

    def drop_all(self) -> None:
        from . import models  # noqa: F401

        Base.metadata.drop_all(self.engine)

    @contextmanager
    def session(self) -> Iterator[Session]:
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()

    def dispose(self) -> None:
        self.engine.dispose()
