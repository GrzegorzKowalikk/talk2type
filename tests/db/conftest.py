import pytest
from sqlmodel import SQLModel, Session, create_engine

from talk2type.db.model import Transcription  # noqa: F401 — registers metadata


@pytest.fixture
def engine():
    e = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(e)
    yield e
    SQLModel.metadata.drop_all(e)


@pytest.fixture
def session(engine):
    with Session(engine) as s:
        yield s
