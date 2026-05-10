from contextlib import contextmanager
from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from talk2type.config import DB_PATH

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(f"sqlite:///{DB_PATH}")
        SQLModel.metadata.create_all(_engine)
    return _engine


@contextmanager
def get_session() -> Generator[Session, None, None]:
    with Session(get_engine()) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
