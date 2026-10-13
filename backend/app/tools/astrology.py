from __future__ import annotations

from typing import Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.models.consultation import Consultation
from app.services import customer_service, lead_service
from app.services.astrology_service import get_astrology_service
from app.tools.common import ToolContext
from app.utils.validation import (
    is_valid_birth_time,
    is_valid_email,
    is_valid_phone,
    normalize_birth_time,
    normalize_date_of_birth,
)


class CalculateBirthChartArgs(BaseModel):
    birth_date: str = Field(description="Date of birth, normalized to YYYY-MM-DD if possible")
    birth_time: Optional[str] = Field(default=None, description="Birth time, 24h HH:MM if known")
    birth_place: Optional[str] = Field(default=None, description="City/place of birth")


class CreateAstrologyConsultationArgs(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    birth_date: Optional[str] = None
    birth_time: Optional[str] = None
    birth_place: Optional[str] = None
    question: Optional[str] = Field(default=None, description="Their specific question")
    confirmed: bool = Field(description="True only after the visitor explicitly confirmed")


def build_astrology_tools(ctx: ToolContext) -> dict[str, StructuredTool]:
    db = ctx.db

    def calculate_birth_chart_fn(
        birth_date: str, birth_time: Optional[str] = None, birth_place: Optional[str] = None
    ) -> str:
        normalized_date = normalize_date_of_birth(birth_date) or birth_date
        service = get_astrology_service()
        try:
            normalized_time = normalize_birth_time(birth_time) if birth_time else None
            time_known = bool(normalized_time and is_valid_birth_time(normalized_time))
            result = service.calculate_chart(
                date_of_birth=normalized_date,
                birth_time=normalized_time,
                birth_place=birth_place,
                birth_country=None,
                birth_time_known=time_known,
            )
        except ValueError as exc:
            return f"Could not calculate the chart: {exc}"

        ctx.record("calculate_birth_chart", f"sun_sign={result['sun_sign']}")
        summary = f"Sun sign: {result['sun_sign']}."
        if result.get("moon_sign"):
            summary += f" (Demo) Moon sign: {result['moon_sign']}."
        if result.get("ascendant"):
            summary += f" (Demo) Ascendant: {result['ascendant']}."
        else:
            summary += " Ascendant unavailable without a known birth time."
        return summary + " " + result["disclaimer"]

    def create_astrology_consultation_fn(
        confirmed: bool,
        name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        birth_date: Optional[str] = None,
        birth_time: Optional[str] = None,
        birth_place: Optional[str] = None,
        question: Optional[str] = None,
    ) -> str:
        if not confirmed:
            ctx.record("create_astrology_consultation", "not created: confirmed=false", success=False)
            return "Consultation not created: confirmation was not affirmative."
        if email and not is_valid_email(email):
            ctx.record("create_astrology_consultation", "not created: invalid email format", success=False)
            return "That email address doesn't look valid."
        if phone and not is_valid_phone(phone):
            ctx.record("create_astrology_consultation", "not created: invalid phone format", success=False)
            return "That phone number doesn't look valid."
        if not (email or phone):
            ctx.record("create_astrology_consultation", "not created: no email or phone provided", success=False)
            return "Cannot create the consultation yet -- no email or phone has been provided."
        if not birth_date:
            ctx.record("create_astrology_consultation", "not created: missing date of birth", success=False)
            return "Cannot create the consultation yet -- date of birth is still missing."

        ctx.customer = customer_service.get_or_create_customer(
            db,
            name=name,
            email=email,
            phone=phone,
            existing_customer_id=ctx.customer.id if ctx.customer else None,
        )

        details = {
            "birth_date": normalize_date_of_birth(birth_date) or birth_date,
            "birth_time": birth_time,
            "birth_place": birth_place,
            "question": question,
        }
        consultation = Consultation(
            agent_id=ctx.agent.id,
            session_id=ctx.session.session_id,
            customer_id=ctx.customer.id,
            type="astrology",
            details=details,
            status="new",
        )
        db.add(consultation)
        db.flush()

        lead = lead_service.create_lead(
            db,
            agent_id=ctx.agent.id,
            session_id=ctx.session.session_id,
            customer=ctx.customer,
            name=name,
            email=email,
            phone=phone,
            source="astrology-widget",
            metadata={**details, "consultation_id": consultation.id},
        )
        ctx.leads_created.append(lead)
        ctx.record("create_astrology_consultation", f"consultation #{consultation.id}, lead #{lead.id}")
        return f"Consultation request #{consultation.id} created and a lead (#{lead.id}) has been logged for follow-up."

    return {
        "calculate_birth_chart": StructuredTool.from_function(
            func=calculate_birth_chart_fn,
            name="calculate_birth_chart",
            description=(
                "Calculate the visitor's astrology chart from their birth date/time/place. "
                "Never state sign or planet information without calling this tool first."
            ),
            args_schema=CalculateBirthChartArgs,
        ),
        "create_astrology_consultation": StructuredTool.from_function(
            func=create_astrology_consultation_fn,
            name="create_astrology_consultation",
            description=(
                "Create an astrology consultation request for human follow-up. Only call "
                "after the visitor has explicitly confirmed a summary of their details."
            ),
            args_schema=CreateAstrologyConsultationArgs,
        ),
    }
