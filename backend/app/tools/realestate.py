from __future__ import annotations

from typing import Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.services import property_service
from app.tools.common import ToolContext


class SearchPropertiesArgs(BaseModel):
    location: Optional[str] = Field(default=None, description="City or area, e.g. 'Austin, TX'")
    max_price: Optional[float] = Field(default=None, description="Maximum budget, if given")


class PropertyDetailsArgs(BaseModel):
    property_id: str = Field(description="The property id from a previous search result")


def build_realestate_tools(ctx: ToolContext) -> dict[str, StructuredTool]:
    def search_properties_fn(location: Optional[str] = None, max_price: Optional[float] = None) -> str:
        results = property_service.search_properties(location=location, max_price=max_price)
        ctx.record("search_properties", f"{len(results)} results")
        if not results:
            return "No matching properties found."
        lines = [
            f"{p['id']}: {p['title']} - {p['location']} - ${p['price']:,} - {p['bedrooms']}bd"
            for p in results
        ]
        return "\n".join(lines)

    def get_property_details_fn(property_id: str) -> str:
        prop = property_service.get_property(property_id)
        if not prop:
            return f"No property found with id {property_id}."
        return (
            f"{prop['title']} in {prop['location']}: {prop['description']} "
            f"${prop['price']:,}, {prop['bedrooms']} bedroom(s), type: {prop['type']}."
        )

    return {
        "search_properties": StructuredTool.from_function(
            func=search_properties_fn,
            name="search_properties",
            description="Search property listings by location and/or maximum price.",
            args_schema=SearchPropertiesArgs,
        ),
        "get_property_details": StructuredTool.from_function(
            func=get_property_details_fn,
            name="get_property_details",
            description="Get full details for a specific property id returned by search_properties.",
            args_schema=PropertyDetailsArgs,
        ),
    }
