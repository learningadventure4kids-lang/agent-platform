from app.services.lead_service import compute_lead_score


def test_score_zero_with_nothing():
    assert compute_lead_score(None, None, None, {}) == 0


def test_score_increases_with_name_and_contact():
    base = compute_lead_score(None, None, None, {})
    with_name = compute_lead_score("John", None, None, {})
    with_contact = compute_lead_score("John", "john@example.com", None, {})
    assert base < with_name < with_contact


def test_score_increases_with_metadata_fields():
    score1 = compute_lead_score("John", "j@example.com", None, {})
    score2 = compute_lead_score("John", "j@example.com", None, {"budget": "$500"})
    score3 = compute_lead_score(
        "John", "j@example.com", None, {"budget": "$500", "occasion": "wedding"}
    )
    assert score1 < score2 < score3


def test_score_capped_at_100():
    metadata = {f"field_{i}": "value" for i in range(20)}
    score = compute_lead_score("John", "j@example.com", "+15550001111", metadata)
    assert score == 100


def test_empty_metadata_values_dont_count():
    score_with_blanks = compute_lead_score("John", "j@example.com", None, {"a": "", "b": None, "c": []})
    score_without = compute_lead_score("John", "j@example.com", None, {})
    assert score_with_blanks == score_without
