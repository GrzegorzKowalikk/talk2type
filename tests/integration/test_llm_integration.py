import pytest

pytestmark = pytest.mark.integration


def test_real_cleanup_removes_fillers():
    from talk2type.services.cleanup import CleanupService

    result = CleanupService().cleanup("dzisiaj eeee byłem yyyy w sklepie", language="pl")
    assert "eeee" not in result
    assert "yyyy" not in result
    # Should still contain the meaningful words
    assert "sklepie" in result.lower() or "sklep" in result.lower()
