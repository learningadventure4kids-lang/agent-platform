"""Common tools available to every agent, plus the shared `ToolContext` that
all business-specific tool modules (jewellery.py, astrology.py,
realestate.py) build their tools around.

The LLM never touches the database directly -- every tool here validates
its own inputs and delegates to app/services/*. Tools are built fresh per
request via each module's `build_*_tools(ctx)` function, closing over the
current request's DB session, agent, and session/customer rows. This is
also what makes tool isolation between agents structural rather than
convention-based: a request for Agent A only ever constructs Agent A's
allowed tools, so there is nothing for the LLM to call into Agent B's
tools even if it tried (see app/agents/resolver.py::get_allowed_tools).
"""
from __future__ import annotations

import logging
from typing import Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from app.models.agent import Agent
from app.models.customer import Customer
from app.models.lead import Lead
from app.models.session import Session as SessionModel
from app.services import customer_service, lead_service
from app.utils.validation import is_valid_email, is_valid_phone

logger = logging.getLogger("agent_platform.tools")


class ToolContext:
    """Mutable, per-turn bag of everything a tool might need or produce.
    The graph reads `leads_created` / `tool_results` back out after the
    tool node runs so the final state reflects what actually happened --
    never what the LLM merely claims happened.

    Every call to `record()` is also written to the application log at
    INFO level (never the credential/PII-bearing tool *arguments*, only
    the tool name and a short outcome summary) -- this is what makes "the
    agent said a lead was created but nothing shows up in the dashboard"
    diagnosable: search `docker compose logs backend` for
    `agent=<agent_key> session=<session_id>` to see exactly which tools
    were invoked this turn and why each one succeeded or failed, including
    when a tool was never called at all (no matching log line for that
    session -- see the "ungrounded claim" check in app/api/chat.py, which
    catches exactly that case).
    """

    def __init__(
        self,
        db: DBSession,
        agent: Agent,
        session: SessionModel,
        customer: Optional[Customer],
    ):
        self.db = db
        self.agent = agent
        self.session = session
        self.customer = customer
        self.leads_created: list[Lead] = []
        self.tool_results: list[dict] = []
        self.pending_lead = False
        self.handoff_requested = False
        self.handoff_reason: Optional[str] = None

    def record(self, tool_name: str, result_summary: str, success: bool = True) -> None:
        self.tool_results.append({"tool": tool_name, "result": result_summary, "success": success})
        log_fn = logger.info if success else logger.warning
        log_fn(
            "tool=%s agent=%s session=%s success=%s result=%s",
            tool_name, self.agent.agent_key, self.session.session_id, success, result_summary,
        )


class CreateLeadArgs(BaseModel):
    name: Optional[str] = Field(default=None, description="Visitor's name, if known")
    email: Optional[str] = Field(default=None, description="Visitor's email, if given")
    phone: Optional[str] = Field(default=None, description="Visitor's phone, if given")
    confirmed: bool = Field(
        description="Must be true -- only call this after the visitor has explicitly "
        "confirmed a summary you showed them."
    )
    notes: Optional[str] = Field(default=None, description="Short free-text summary of what they need")


class ValidateContactArgs(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None


class RequestHandoffArgs(BaseModel):
    reason: Optional[str] = Field(
        default=None, description="Short reason the visitor needs a human (optional)"
    )


def build_common_tools(ctx: ToolContext, source: str, extra_metadata_fn=None) -> dict[str, StructuredTool]:
    db = ctx.db

    def create_lead_fn(
        confirmed: bool,
        name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> str:
        if not confirmed:
            ctx.record("create_lead", "not created: confirmed=false", success=False)
            return "Lead not created: confirmation was not affirmative."
        if email and not is_valid_email(email):
            ctx.record("create_lead", f"not created: invalid email format ({email!r})", success=False)
            return "That email address doesn't look valid -- please ask the visitor to double-check it."
        if phone and not is_valid_phone(phone):
            ctx.record("create_lead", "not created: invalid phone format", success=False)
            return "That phone number doesn't look valid -- please ask the visitor to double-check it."
        if not (email or phone or (ctx.customer and (ctx.customer.email or ctx.customer.phone))):
            ctx.record("create_lead", "not created: no email or phone provided", success=False)
            return "Cannot create the lead yet -- no email or phone has been provided."

        if email or phone:
            ctx.customer = customer_service.get_or_create_customer(
                db,
                name=name,
                email=email,
                phone=phone,
                existing_customer_id=ctx.customer.id if ctx.customer else None,
            )

        metadata = {"notes": notes} if notes else {}
        if extra_metadata_fn:
            metadata.update(extra_metadata_fn())

        lead = lead_service.create_lead(
            db,
            agent_id=ctx.agent.id,
            session_id=ctx.session.session_id,
            customer=ctx.customer,
            name=name,
            email=email,
            phone=phone,
            source=source,
            metadata=metadata,
        )
        ctx.leads_created.append(lead)
        ctx.record("create_lead", f"lead #{lead.id} created")
        return f"Lead #{lead.id} created successfully with status '{lead.status}'."

    def get_known_info_fn() -> str:
        parts = []
        if ctx.customer:
            if ctx.customer.name:
                parts.append(f"name={ctx.customer.name}")
            if ctx.customer.email:
                parts.append(f"email={ctx.customer.email}")
            if ctx.customer.phone:
                parts.append(f"phone={ctx.customer.phone}")
        if ctx.leads_created:
            parts.append(f"lead_already_created=true (#{ctx.leads_created[-1].id})")
        return "; ".join(parts) if parts else "Nothing has been recorded about this visitor yet."

    def validate_contact_fn(email: Optional[str] = None, phone: Optional[str] = None) -> str:
        problems = []
        if email and not is_valid_email(email):
            problems.append("that email address doesn't look valid")
        if phone and not is_valid_phone(phone):
            problems.append("that phone number doesn't look valid")
        if problems:
            return "Invalid: " + "; ".join(problems) + "."
        if not email and not phone:
            return "No contact info given to validate."
        return "Contact info looks valid."

    def request_human_handoff_fn(reason: Optional[str] = None) -> str:
        ctx.handoff_requested = True
        ctx.handoff_reason = reason
        note = f"Human handoff requested. Reason: {reason}" if reason else "Human handoff requested."
        if ctx.leads_created:
            lead = ctx.leads_created[-1]
            lead.status = "contact_requested"
            lead.metadata_json = {**(lead.metadata_json or {}), "handoff_note": note}
            db.flush()
            ctx.record("request_human_handoff", f"flagged existing lead #{lead.id}: {note}")
        else:
            ctx.record("request_human_handoff", f"flagged (no lead yet): {note}")
        return (
            "Handoff has been flagged. If no lead/contact record exists yet for this "
            "visitor, you still need their email or phone before anyone can actually "
            "follow up -- ask for it if you haven't already. Tell the visitor something "
            "like: \"I can connect you with a team member.\" Do not describe how this "
            "was flagged internally."
        )

    return {
        "create_lead": StructuredTool.from_function(
            func=create_lead_fn,
            name="create_lead",
            description=(
                "Create a lead so the business's team can follow up. Only call this "
                "immediately after the visitor has explicitly confirmed a summary you "
                "showed them (e.g. said 'yes', 'that's correct', 'go ahead')."
            ),
            args_schema=CreateLeadArgs,
        ),
        "get_known_info": StructuredTool.from_function(
            func=get_known_info_fn,
            name="get_known_info",
            description="Check what's already known about this visitor before asking for it again.",
        ),
        "validate_contact_info": StructuredTool.from_function(
            func=validate_contact_fn,
            name="validate_contact_info",
            description="Validate an email and/or phone number's format before confirming it with the visitor.",
            args_schema=ValidateContactArgs,
        ),
        "request_human_handoff": StructuredTool.from_function(
            func=request_human_handoff_fn,
            name="request_human_handoff",
            description=(
                "Flag this conversation for a human team member to take over -- use when "
                "the visitor explicitly asks for a person, or the request is clearly outside "
                "what you can help with."
            ),
            args_schema=RequestHandoffArgs,
        ),
    }
