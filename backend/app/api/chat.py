"""The one chat endpoint every tenant's widget calls. Which business it's
talking to is entirely determined by `agent_token` -- there is no
per-tenant route or code branch here."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session as DBSession

from app.agents.graph import run_turn
from app.agents.registry import get_allowed_tool_keys
from app.agents.resolver import resolve_agent
from app.api.deps import client_ip
from app.database.connection import get_db
from app.models.agent import Agent
from app.schemas import AgentPublicInfo, ChatRequest, ChatResponse
from app.security.rate_limit import check_rate_limit
from app.services import session_service

logger = logging.getLogger("agent_platform.chat")

router = APIRouter(prefix="/api/chat", tags=["chat"])

FRIENDLY_FALLBACK = (
    "I'm having a temporary problem connecting right now. Your conversation has been "
    "saved, so nothing is lost -- please try again in a moment."
)

# Phrases that suggest the assistant is telling the visitor their details
# were saved / a lead was created / someone will follow up. If the final
# response contains one of these AND no lead-creation tool actually
# succeeded this turn, that's exactly the "agent claims success but no
# lead in the dashboard" bug -- logged as a warning so it's greppable in
# `docker compose logs backend` instead of being invisible. This is a
# detection aid, not a fix for model unfaithfulness: the underlying cause
# is almost always that the LLM never called (or was never given) the
# lead-creation tool, or called it and got a failure it didn't relay to
# the visitor -- see the tool-level logs (app/tools/common.py::ToolContext.record)
# for which of those it was in a specific session.
_SUCCESS_CLAIM_PHRASES = (
    "saved your", "noted that down", "noted your", "logged your", "recorded your",
    "someone will", "team will", "astrologer will", "reach out", "follow up",
    "get in touch", "in touch with you", "submitted your", "created your",
)


def _looks_like_ungrounded_success_claim(response_text: str, ctx) -> bool:
    text = response_text.lower()
    if not any(phrase in text for phrase in _SUCCESS_CLAIM_PHRASES):
        return False
    if ctx.leads_created:
        return False  # a lead genuinely was created this turn -- not ungrounded
    return True


def run_chat_turn(
    db: DBSession, agent: Agent, request: Request, session_id: str | None, message: str,
) -> ChatResponse:
    """The actual turn: resolve/create the session, run the LangGraph
    agent, persist messages, and fall back gracefully on error. Shared by
    every caller that has already authenticated and resolved an `Agent` --
    the public `/api/chat` endpoint (via `agent_token`) and the self-serve
    builder's ownership-authenticated preview endpoint alike -- so a
    preview is the real pipeline, not a simulation of it."""
    session, _ = session_service.get_or_create_session(db, agent.id, session_id)

    allowed, rate_limit_message = check_rate_limit(
        agent.agent_key, session.session_id, client_ip(request)
    )
    if not allowed:
        raise HTTPException(status_code=429, detail=rate_limit_message)

    customer = None
    if session.customer_id:
        from app.models.customer import Customer

        customer = db.query(Customer).filter(Customer.id == session.customer_id).first()

    history = session_service.get_messages(db, session.session_id)
    session_service.save_message(db, session.session_id, "user", message)
    db.commit()

    agent_public = AgentPublicInfo(
        name=agent.name,
        brand=agent.brand_name,
        welcome_message=agent.welcome_message,
        suggestions=agent.suggestions,
        theme=agent.theme,
    )

    try:
        allowed_tool_keys = get_allowed_tool_keys(db, agent.id)
        result = run_turn(
            db=db,
            agent=agent,
            session=session,
            customer=customer,
            allowed_tool_keys=allowed_tool_keys,
            history=history,
            user_message=message,
        )
        ctx = result.ctx

        if ctx.customer and session.customer_id != ctx.customer.id:
            session.customer_id = ctx.customer.id

        session.conversation_status = "qualified" if ctx.leads_created else "collecting_information"
        session_service.touch_session(db, session)
        assistant_msg = session_service.save_message(
            db, session.session_id, "assistant", result.assistant_text
        )
        db.commit()

        logger.info(
            "chat turn completed agent=%s session=%s tools_called=%s lead_created=%s",
            agent.agent_key, session.session_id,
            [r["tool"] for r in ctx.tool_results], bool(ctx.leads_created),
        )
        if _looks_like_ungrounded_success_claim(result.assistant_text, ctx):
            logger.warning(
                "possible ungrounded success claim: agent=%s session=%s tools_called=%s "
                "-- assistant response sounds like it confirmed saving/following up on the "
                "visitor's details, but no lead-creation tool succeeded this turn. This "
                "usually means the model either never called the lead tool (check whether "
                "it's granted to this agent, and whether the configured provider/model "
                "reliably supports tool calling) or called it and got a failure result it "
                "didn't relay to the visitor (see the tool_results log line above for why).",
                agent.agent_key, session.session_id, [r["tool"] for r in ctx.tool_results],
            )

        return ChatResponse(
            session_id=session.session_id,
            agent=agent_public,
            response=result.assistant_text,
            message_id=assistant_msg.id,
            lead_created=bool(ctx.leads_created),
        )

    except HTTPException:
        raise
    except Exception:
        logger.exception("Chat turn failed for agent=%s session=%s", agent.agent_key, session.session_id)
        db.rollback()
        assistant_msg = session_service.save_message(db, session.session_id, "assistant", FRIENDLY_FALLBACK)
        db.commit()
        return ChatResponse(
            session_id=session.session_id,
            agent=agent_public,
            response=FRIENDLY_FALLBACK,
            message_id=assistant_msg.id,
            lead_created=False,
        )


@router.post("", response_model=ChatResponse)
def chat(req: ChatRequest, request: Request, db: DBSession = Depends(get_db)):
    agent = resolve_agent(db, req.agent_token, request)
    return run_chat_turn(db, agent, request, req.session_id, req.message)
