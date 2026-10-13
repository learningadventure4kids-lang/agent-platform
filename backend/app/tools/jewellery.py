from __future__ import annotations

from typing import Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.services import customer_service, lead_service, product_service
from app.tools.common import ToolContext
from app.utils.validation import is_valid_email, is_valid_phone


class SearchJewelleryArgs(BaseModel):
    query: str = Field(description="What the visitor is looking for, e.g. 'wedding necklace'")


class ProductDetailsArgs(BaseModel):
    product_id: str = Field(description="The product id from a previous search result")


class CreateJewelleryLeadArgs(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    product_interest: Optional[str] = Field(default=None, description="Product name or id they liked")
    budget: Optional[str] = Field(default=None, description="Their stated budget, if any")
    occasion: Optional[str] = Field(default=None, description="e.g. wedding, anniversary, gift")
    confirmed: bool = Field(description="True only after the visitor explicitly confirmed")


def build_jewellery_tools(ctx: ToolContext) -> dict[str, StructuredTool]:
    db = ctx.db

    def search_jewellery_fn(query: str) -> str:
        results = product_service.search_products(query)
        ctx.record("search_jewellery", f"{len(results)} results for '{query}'")
        if not results:
            return "No matching products found."
        lines = [
            f"{p['id']}: {p['name']} - ${p['price']:.0f} - {p['description']}" for p in results
        ]
        return "\n".join(lines)

    def get_product_details_fn(product_id: str) -> str:
        product = product_service.get_product(product_id)
        if not product:
            return f"No product found with id {product_id}."
        return (
            f"{product['name']} ({product['category']}): {product['description']} "
            f"Price: ${product['price']:.0f} {product['currency']}. "
            f"Good for: {', '.join(product['occasion'])}."
        )

    def create_jewellery_lead_fn(
        confirmed: bool,
        name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        product_interest: Optional[str] = None,
        budget: Optional[str] = None,
        occasion: Optional[str] = None,
    ) -> str:
        if not confirmed:
            ctx.record("create_jewellery_lead", "not created: confirmed=false", success=False)
            return "Lead not created: confirmation was not affirmative."
        if email and not is_valid_email(email):
            ctx.record("create_jewellery_lead", "not created: invalid email format", success=False)
            return "That email address doesn't look valid."
        if phone and not is_valid_phone(phone):
            ctx.record("create_jewellery_lead", "not created: invalid phone format", success=False)
            return "That phone number doesn't look valid."
        if not (email or phone):
            ctx.record("create_jewellery_lead", "not created: no email or phone provided", success=False)
            return "Cannot create the lead yet -- no email or phone has been provided."

        ctx.customer = customer_service.get_or_create_customer(
            db,
            name=name,
            email=email,
            phone=phone,
            existing_customer_id=ctx.customer.id if ctx.customer else None,
        )
        lead = lead_service.create_lead(
            db,
            agent_id=ctx.agent.id,
            session_id=ctx.session.session_id,
            customer=ctx.customer,
            name=name,
            email=email,
            phone=phone,
            source="kaur-jewellery-widget",
            metadata={
                "product_interest": product_interest,
                "budget": budget,
                "occasion": occasion,
            },
        )
        ctx.leads_created.append(lead)
        ctx.record("create_jewellery_lead", f"lead #{lead.id} created")
        return f"Lead #{lead.id} created successfully with status '{lead.status}'."

    return {
        "search_jewellery": StructuredTool.from_function(
            func=search_jewellery_fn,
            name="search_jewellery",
            description="Search the jewellery catalog by free-text query (occasion, type, style).",
            args_schema=SearchJewelleryArgs,
        ),
        "get_product_details": StructuredTool.from_function(
            func=get_product_details_fn,
            name="get_product_details",
            description="Get full details for a specific product id returned by search_jewellery.",
            args_schema=ProductDetailsArgs,
        ),
        "create_jewellery_lead": StructuredTool.from_function(
            func=create_jewellery_lead_fn,
            name="create_jewellery_lead",
            description=(
                "Create a jewellery consultation lead. Only call after the visitor has "
                "explicitly confirmed a summary of their name, contact info, product "
                "interest, budget, and occasion."
            ),
            args_schema=CreateJewelleryLeadArgs,
        ),
    }
