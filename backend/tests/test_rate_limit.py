from app.security.rate_limit import SlidingWindowLimiter


def test_allows_up_to_limit():
    limiter = SlidingWindowLimiter()
    for _ in range(5):
        assert limiter.allow("key1", limit=5, window_seconds=60)
    assert not limiter.allow("key1", limit=5, window_seconds=60)


def test_different_keys_are_independent():
    limiter = SlidingWindowLimiter()
    for _ in range(3):
        limiter.allow("a", limit=3, window_seconds=60)
    assert not limiter.allow("a", limit=3, window_seconds=60)
    assert limiter.allow("b", limit=3, window_seconds=60)


def test_window_expiry_allows_again():
    limiter = SlidingWindowLimiter()
    assert limiter.allow("k", limit=1, window_seconds=0)
    # window_seconds=0 means the previous hit is immediately stale
    assert limiter.allow("k", limit=1, window_seconds=0)
