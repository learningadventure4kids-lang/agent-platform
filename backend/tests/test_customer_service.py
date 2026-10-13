from app.database.connection import db_session
from app.services import customer_service


def test_creates_new_customer():
    with db_session() as db:
        c = customer_service.get_or_create_customer(db, name="Alice", email="alice@example.com")
        assert c.id is not None


def test_matches_existing_by_email():
    with db_session() as db:
        first = customer_service.get_or_create_customer(db, name="Bob", email="bob@example.com")
        first_id = first.id
    with db_session() as db:
        second = customer_service.get_or_create_customer(db, email="bob@example.com", phone="+15551234567")
        assert second.id == first_id
        assert second.phone == "+15551234567"


def test_matches_existing_by_phone():
    with db_session() as db:
        first = customer_service.get_or_create_customer(db, name="Carol", phone="+15559998888")
        first_id = first.id
    with db_session() as db:
        second = customer_service.get_or_create_customer(db, phone="+15559998888")
        assert second.id == first_id


def test_does_not_overwrite_existing_name():
    with db_session() as db:
        first = customer_service.get_or_create_customer(db, name="Dave", email="dave@example.com")
        first_id = first.id
    with db_session() as db:
        second = customer_service.get_or_create_customer(db, name="Someone Else", email="dave@example.com")
        assert second.id == first_id
        assert second.name == "Dave"
