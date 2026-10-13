from unittest.mock import MagicMock

from app.security.domains import is_origin_allowed


def _request_with(origin=None, referer=None):
    req = MagicMock()
    headers = {}
    if origin:
        headers["origin"] = origin
    if referer:
        headers["referer"] = referer
    req.headers = headers
    return req


def test_empty_allowlist_permits_anything():
    assert is_origin_allowed([], _request_with(origin="https://evil.example.com"))


def test_matching_origin_allowed():
    req = _request_with(origin="https://kaurjewellery.com")
    assert is_origin_allowed(["kaurjewellery.com"], req)


def test_www_variant_allowed():
    req = _request_with(origin="https://www.kaurjewellery.com")
    assert is_origin_allowed(["kaurjewellery.com"], req)


def test_non_matching_origin_rejected():
    req = _request_with(origin="https://evil.example.com")
    assert not is_origin_allowed(["kaurjewellery.com"], req)


def test_falls_back_to_referer():
    req = _request_with(referer="https://kaurjewellery.com/products")
    assert is_origin_allowed(["kaurjewellery.com"], req)


def test_no_origin_or_referer_is_allowed_through():
    # Non-browser requests (server-to-server, curl) aren't blocked here --
    # the token check is the real gate for those.
    req = _request_with()
    assert is_origin_allowed(["kaurjewellery.com"], req)
