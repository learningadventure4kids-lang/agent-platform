from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.schemas import AdminLoginRequest, AdminLoginResponse

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/login", response_model=AdminLoginResponse)
def login(payload: AdminLoginRequest):
    settings = get_settings()
    if payload.username != settings.ADMIN_USERNAME or payload.password != settings.ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return AdminLoginResponse(admin_key=settings.ADMIN_SECRET_KEY)
