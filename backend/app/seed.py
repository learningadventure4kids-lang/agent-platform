"""Seeds the `tools` catalog from TOOL_REGISTRY and three sample agents
(Kaur Jewellery, Astrology, Real Estate) on first run, matching the spec's
sample-agent list. Each agent's freshly generated public token is written
to `backend/.seeded_tokens.txt` (gitignored) and logged, since after this
point only the token's hash is retrievable -- there is no "forgot my
token" recovery other than rotation.
"""
from __future__ import annotations

import logging
from pathlib import Path

from app.agents.registry import set_agent_tools
from app.config import get_settings
from app.database.connection import db_session
from app.models.agent import Agent
from app.models.ai_provider import AIProviderConfig
from app.models.tool import Tool
from app.security.tokens import generate_token, hash_token
from app.tools.registry import TOOL_REGISTRY

logger = logging.getLogger("agent_platform.seed")

KAUR_PROMPT = """You are Aria, a warm, knowledgeable luxury jewellery advisor for Kaur Jewellery.
Help visitors discover pieces that fit their occasion, style, and budget. Ask about
the occasion and who the piece is for before recommending. Use search_jewellery and
get_product_details rather than describing products from memory. Never pressure the
visitor to buy or to leave contact information."""

ASTROLOGY_PROMPT = """You are an astrology consultation assistant. Be conversational and
respectful, one question at a time. Treat astrology as a traditional belief/reflection
practice, not a scientifically proven fact -- say so if asked directly. Never invent
chart details yourself; always use calculate_birth_chart. Do not make definitive
medical, legal, or financial claims or diagnoses based on astrology."""

REALESTATE_PROMPT = """You are Maya, a helpful real estate assistant. Help visitors find
properties matching their location, budget, and needs using search_properties and
get_property_details. Ask about their timeline and must-haves naturally, not as a
checklist. Never claim a property is still available without checking search results
first."""

SAMPLE_AGENTS = [
    dict(
        agent_key="kaur-jewellery",
        tenant_id="kaur-jewellery",
        name="Aria",
        brand_name="Kaur Jewellery",
        description="Luxury jewellery advisor widget.",
        system_prompt=KAUR_PROMPT,
        welcome_message="Hello! I'm Aria, your personal jewellery advisor. What can I help you find today?",
        suggestions=["Wedding jewellery", "Gift ideas", "Engagement rings", "Everyday pieces"],
        lead_fields=["name", "email", "phone", "product_interest", "budget", "occasion"],
        theme={"accent": "#C9A227", "mode": "dark"},
        model="qwen3:8b",
        temperature=0.5,
        allowed_domains=[],
        tool_keys=["search_jewellery", "get_product_details", "create_jewellery_lead", "create_lead", "search_knowledge_base"],
    ),
    dict(
        agent_key="astrology",
        tenant_id="astrology",
        name="Aria",
        brand_name="Astrology Advisor",
        description="Astrology consultation widget.",
        system_prompt=ASTROLOGY_PROMPT,
        welcome_message="Hi! I'm here to help you explore your birth chart. What would you like to know?",
        suggestions=["Career", "Relationships", "Birth chart", "General reading"],
        lead_fields=["name", "email", "phone", "birth_date", "birth_time", "birth_place", "question"],
        theme={"accent": "#C08A3E", "mode": "dark"},
        model="qwen3:8b",
        temperature=0.4,
        allowed_domains=[],
        tool_keys=["calculate_birth_chart", "create_astrology_consultation", "create_lead", "search_knowledge_base"],
    ),
    dict(
        agent_key="real-estate",
        tenant_id="real-estate",
        name="Maya",
        brand_name="ABC Realty",
        description="Real estate search widget.",
        system_prompt=REALESTATE_PROMPT,
        welcome_message="Hi! I'm Maya. I can help you find the right property. Where are you looking?",
        suggestions=["Homes under $400k", "2-bedroom condos", "Austin listings", "Denver listings"],
        lead_fields=["name", "email", "phone", "location", "budget", "property_type", "timeline"],
        theme={"accent": "#4B7A6B", "mode": "dark"},
        model="qwen3:8b",
        temperature=0.4,
        allowed_domains=[],
        tool_keys=["search_properties", "get_property_details", "create_lead", "search_knowledge_base"],
    ),
]


def _seed_tools(db) -> None:
    for tool_key, meta in TOOL_REGISTRY.items():
        existing = db.query(Tool).filter(Tool.tool_key == tool_key).first()
        if existing:
            continue
        db.add(Tool(tool_key=tool_key, name=meta["name"], description=meta["description"], enabled=True))
    db.flush()


def _seed_default_provider(db) -> None:
    """Runs on EVERY startup (not just first-ever seed), so an existing
    installation upgrading to configurable providers automatically gets a
    default Ollama provider matching its previous hard-coded behavior --
    no admin action required, and every pre-existing agent (provider_id
    left NULL) keeps working exactly as before via the default-provider
    fallback in app/ai/resolution.py."""
    if db.query(AIProviderConfig).filter(AIProviderConfig.is_default.is_(True)).first():
        return
    settings = get_settings()
    default = AIProviderConfig(
        provider_type="ollama",
        display_name="Ollama",
        enabled=True,
        is_default=True,
        base_url=settings.OLLAMA_DEFAULT_BASE_URL,
        model_name=settings.CHAT_MODEL,
        temperature=0.4,
    )
    db.add(default)
    db.flush()
    logger.info("Seeded default AI provider: Ollama (%s)", settings.CHAT_MODEL)


def seed_demo_data() -> None:
    with db_session() as db:
        _seed_tools(db)
        _seed_default_provider(db)

        if db.query(Agent).count() > 0:
            return

        tokens: dict[str, str] = {}
        for data in SAMPLE_AGENTS:
            tool_keys = data.pop("tool_keys")
            token = generate_token()
            agent = Agent(public_token_hash=hash_token(token), **data)
            db.add(agent)
            db.flush()
            set_agent_tools(db, agent.id, tool_keys)
            tokens[data["agent_key"]] = token

        logger.info("Seeded %d sample agents.", len(SAMPLE_AGENTS))

        try:
            out_path = Path(__file__).resolve().parent.parent / ".seeded_tokens.txt"
            lines = [f"{key}: {token}" for key, token in tokens.items()]
            out_path.write_text(
                "Public agent tokens (generated once at seed time -- rotate via the "
                "admin API/dashboard if lost):\n\n" + "\n".join(lines) + "\n"
            )
            logger.info("Wrote seeded agent tokens to %s", out_path)
        except OSError:
            logger.warning("Could not write .seeded_tokens.txt; tokens were only logged.")
        for line in lines:
            logger.info("Seeded token -- %s", line)
