from talk2type.core.cancellation import CancellationToken


def test_new_token_not_cancelled():
    assert CancellationToken().cancelled is False


def test_cancel_sets_flag():
    t = CancellationToken()
    t.cancel()
    assert t.cancelled is True


def test_cancel_is_idempotent():
    t = CancellationToken()
    t.cancel()
    t.cancel()
    assert t.cancelled is True
