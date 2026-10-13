"""Customer identity: matching a visitor to an existing customer record by
email/phone, or creating a new one. Customers are global (not scoped to an
agent) so the same person recognized on two different agent widgets is
still one customer record -- but note that Sessions, Leads, and
Consultations *are* agent-scoped, so no conversation content or lead data
ever crosses between tenants just because they share a customer row."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session as DBSession

from app.models.customer import Customer


def find_customer_by_contact(
    db: DBSession, email: Optional[str], phone: Optional[str]
) -> Optional[Customer]:
    if email:
        match = db.query(Customer).filter(Customer.email == email).first()
        if match:
            return match
    if phone:
        match = db.query(Customer).filter(Customer.phone == phone).first()
        if match:
            return match
    return None


def get_or_create_customer(
    db: DBSession,
    name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    existing_customer_id: Optional[int] = None,
) -> Customer:
    customer: Optional[Customer] = None

    if existing_customer_id:
        customer = db.query(Customer).filter(Customer.id == existing_customer_id).first()

    if customer is None:
        customer = find_customer_by_contact(db, email, phone)

    if customer is None:
        customer = Customer(name=name, email=email, phone=phone)
        db.add(customer)
        db.flush()
        return customer

    if name and not customer.name:
        customer.name = name
    if email and not customer.email:
        customer.email = email
    if phone and not customer.phone:
        customer.phone = phone
    db.flush()
    return customer
