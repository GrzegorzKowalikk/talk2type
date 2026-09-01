import sys
from contextlib import contextmanager
from unittest.mock import patch

import pytest
from sqlmodel import SQLModel, Session, create_engine

from talk2type.config import WHISPER_HOTWORDS
from talk2type.db.model import Hotword  # noqa: F401 -- registers metadata


@pytest.fixture(scope="session")
def qt_app():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


def _in_memory_engine():
    e = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(e)
    return e


@pytest.fixture
def dict_page(qt_app):
    from talk2type.ui.pages.dictionary import DictionaryPage

    e = _in_memory_engine()

    @contextmanager
    def _sess():
        with Session(e) as s:
            yield s

    with patch("talk2type.ui.pages.dictionary.get_session", side_effect=_sess):
        w = DictionaryPage()
        w.show()
        yield w
    w.close()


# --- List hotwords from DB ---


def test_refresh_loads_hotwords_from_db(qt_app):
    from talk2type.ui.pages.dictionary import DictionaryPage

    e = _in_memory_engine()
    with Session(e) as s:
        s.add(Hotword(word="Claude"))
        s.add(Hotword(word="Anthropic"))
        s.commit()

    @contextmanager
    def _sess():
        with Session(e) as s:
            yield s

    with patch("talk2type.ui.pages.dictionary.get_session", side_effect=_sess):
        w = DictionaryPage()
        w.refresh_data()

    assert w.word_list.count() == 2
    texts = [w.word_list.item(i).data(256) for i in range(w.word_list.count())]
    assert "Claude" in texts
    assert "Anthropic" in texts
    w.close()


# --- Add hotword via UI ---


def test_add_word_via_input(dict_page):
    # dict_page starts with the config-seeded hotwords
    dict_page.input.setText("NewWord")
    dict_page.add_word()

    assert dict_page.word_list.count() == len(WHISPER_HOTWORDS) + 1
    texts = [dict_page.word_list.item(i).data(256) for i in range(dict_page.word_list.count())]
    assert "NewWord" in texts
    assert dict_page.input.text() == ""  # cleared after add


def test_add_word_ignores_empty(dict_page):
    dict_page.input.setText("  ")
    dict_page.add_word()

    # still just the seeded items
    assert dict_page.word_list.count() == len(WHISPER_HOTWORDS)


def test_add_word_ignores_duplicate(dict_page):
    dict_page.input.setText("Claude")
    dict_page.add_word()
    assert dict_page.word_list.count() == len(WHISPER_HOTWORDS)  # Claude already seeded

    dict_page.input.setText("Claude")
    dict_page.add_word()
    assert dict_page.word_list.count() == len(WHISPER_HOTWORDS)  # no duplicate


# --- Remove hotword via UI ---


def test_remove_word(dict_page):
    # dict_page starts with the config-seeded hotwords
    dict_page.input.setText("TestWord")
    dict_page.add_word()
    assert dict_page.word_list.count() == len(WHISPER_HOTWORDS) + 1

    # Find the id of the newly added "TestWord"
    for i in range(dict_page.word_list.count()):
        if dict_page.word_list.item(i).data(256) == "TestWord":
            word_id = dict_page.word_list.item(i).data(257)
            break

    dict_page.remove_word(word_id)
    assert dict_page.word_list.count() == len(WHISPER_HOTWORDS)


# --- Seed from config on first launch ---


def test_seed_from_config_when_db_empty(qt_app):
    from talk2type.ui.pages.dictionary import DictionaryPage

    e = _in_memory_engine()

    @contextmanager
    def _sess():
        with Session(e) as s:
            yield s

    with patch("talk2type.ui.pages.dictionary.get_session", side_effect=_sess):
        w = DictionaryPage()

    # After construction, config hotwords should be seeded
    assert w.word_list.count() == len(WHISPER_HOTWORDS)
    texts = [w.word_list.item(i).data(256) for i in range(w.word_list.count())]
    assert "Claude" in texts
    assert "Claude Code" in texts
    assert "Anthropic" in texts
    w.close()


def test_no_seed_when_db_not_empty(qt_app):
    from talk2type.ui.pages.dictionary import DictionaryPage

    e = _in_memory_engine()
    with Session(e) as s:
        s.add(Hotword(word="Existing"))
        s.commit()

    @contextmanager
    def _sess():
        with Session(e) as s:
            yield s

    with patch("talk2type.ui.pages.dictionary.get_session", side_effect=_sess):
        w = DictionaryPage()

    assert w.word_list.count() == 1
    assert w.word_list.item(0).data(256) == "Existing"
    w.close()


# --- hotwords_changed signal ---


def test_add_word_emits_hotwords_changed(dict_page):
    seen = []
    dict_page.hotwords_changed.connect(lambda: seen.append(1))
    dict_page.input.setText("Kubernetes")
    dict_page.add_word()
    assert seen == [1]


def test_duplicate_add_does_not_emit(dict_page):
    seen = []
    dict_page.hotwords_changed.connect(lambda: seen.append(1))
    dict_page.input.setText("Claude")  # already seeded
    dict_page.add_word()
    assert seen == []


def test_empty_input_does_not_emit(dict_page):
    seen = []
    dict_page.hotwords_changed.connect(lambda: seen.append(1))
    dict_page.input.setText("   ")
    dict_page.add_word()
    assert seen == []


def test_remove_word_emits_hotwords_changed(dict_page):
    dict_page.input.setText("Tmp")
    dict_page.add_word()
    item = dict_page.word_list.item(0)
    seen = []
    dict_page.hotwords_changed.connect(lambda: seen.append(1))
    dict_page.remove_word(item.data(257))  # 257 = _ID_DATA
    assert seen == [1]
