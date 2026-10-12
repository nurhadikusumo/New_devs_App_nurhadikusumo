from fastapi import APIRouter, Depends, HTTPException, Query
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any
from app.services.cache import get_revenue_summary
from app.core.auth import authenticate_request as get_current_user
from app.core.database_pool import db_pool
from sqlalchemy import text

router = APIRouter()

@router.get("/dashboard/properties")
async def get_dashboard_properties(current_user: dict = Depends(get_current_user)):
    tenant_id = getattr(current_user, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=403, detail="Tenant access required")
    if not db_pool.session_factory:
        await db_pool.initialize()
    async with db_pool.get_session() as session:
        result = await session.execute(
            text("SELECT id, name FROM properties WHERE tenant_id = :tenant_id ORDER BY name"),
            {"tenant_id": tenant_id},
        )
        return [dict(row._mapping) for row in result]

@router.get("/dashboard/summary")
async def get_dashboard_summary(
    property_id: str,
    month: int = Query(3, ge=1, le=12),
    year: int = Query(2024, ge=1, le=9998),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    
    tenant_id = getattr(current_user, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=403, detail="Tenant access required")
    
    revenue_data = await get_revenue_summary(property_id, tenant_id, month, year)
    
    total_revenue = Decimal(revenue_data['total']).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    return {
        "property_id": revenue_data['property_id'],
        "total_revenue": str(total_revenue),
        "currency": revenue_data['currency'],
        "reservations_count": revenue_data['count'],
        "month": month,
        "year": year
    }
