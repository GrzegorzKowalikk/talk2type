import pytest

pytestmark = pytest.mark.integration


def test_real_cleanup_removes_fillers():
    from talk2type.llm import cleanup_text

    result = cleanup_text("dzisiaj eeee byłem yyyy w sklepie", "pl")
    assert "eeee" not in result
    assert "yyyy" not in result
    # Should still contain the meaningful words
    assert "sklepie" in result.lower() or "sklep" in result.lower()
