"""Self-serve customer subscription plans and the limits that go with
each one. There is no payment processor wired up yet -- `User.plan` is
set to PLAN_FREE at signup and can only be changed today by a platform
operator (PATCH /api/admin/users/{id}/plan, app/api/admin_users.py).
Swapping in real billing later (Stripe webhook flipping `User.plan`) is a
single call to `set_user_plan`-style code; nothing else in this module
needs to change.

Limits here are enforced per-agent, not per-account: each agent has its
own knowledge base, and a customer with several agents shouldn't have to
split three documents across all of them. "PLUS" numbers are a reasonable
default starting point, not something the user specified -- change them
here, in one place, if the real pricing differs."""
from __future__ import annotations

PLAN_FREE = "free"
PLAN_PLUS = "plus"

VALID_PLANS = {PLAN_FREE, PLAN_PLUS}

PLAN_LIMITS: dict[str, dict[str, int]] = {
    PLAN_FREE: {
        "max_documents_per_agent": 3,
        "max_file_size_bytes": 5 * 1024 * 1024,  # 5 MB
    },
    PLAN_PLUS: {
        "max_documents_per_agent": 25,
        "max_file_size_bytes": 25 * 1024 * 1024,  # 25 MB
    },
}


def get_plan_limits(plan: str | None) -> dict[str, int]:
    """Unknown/missing plan values fail closed to the FREE tier's limits
    rather than raising, since the caller is always about to enforce a
    quota -- defaulting to the most permissive tier would be the wrong
    failure mode."""
    return PLAN_LIMITS.get(plan or PLAN_FREE, PLAN_LIMITS[PLAN_FREE])
