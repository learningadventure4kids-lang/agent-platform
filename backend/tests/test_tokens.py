from app.security.tokens import generate_token, hash_token, tokens_match


def test_generate_token_is_unique_and_prefixed():
    t1, t2 = generate_token(), generate_token()
    assert t1 != t2
    assert t1.startswith("pub_")


def test_hash_token_is_deterministic():
    token = generate_token()
    assert hash_token(token) == hash_token(token)


def test_hash_token_differs_per_token():
    assert hash_token(generate_token()) != hash_token(generate_token())


def test_tokens_match():
    token = generate_token()
    stored_hash = hash_token(token)
    assert tokens_match(token, stored_hash)
    assert not tokens_match("pub_wrong-token", stored_hash)
