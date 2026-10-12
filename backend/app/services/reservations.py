from datetime import date
from decimal import Decimal
from typing import Dict, Any
from fastapi import HTTPException
from sqlalchemy import text
from app.core.database_pool import db_pool

async def calculate_total_revenue(property_id: str, tenant_id: str, month: int, year: int) -> Dict[str, Any]:
    """
    Aggregates revenue from database.
    """
    if not db_pool.session_factory:
        await db_pool.initialize()

    start_date = date(year, month, 1)
    end_date = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)

    async with db_pool.get_session() as session:
        result = await session.execute(text("""
            SELECT p.id AS property_id,
                   COALESCE(SUM(r.total_amount), 0) AS total_revenue,
                   COUNT(r.id) AS reservation_count,
                   COUNT(DISTINCT r.currency) AS currency_count,
                   MIN(r.currency) AS currency
            FROM properties AS p
            LEFT JOIN reservations AS r
              ON r.property_id = p.id AND r.tenant_id = p.tenant_id
             AND (r.check_in_date AT TIME ZONE p.timezone)::date >= :start_date
             AND (r.check_in_date AT TIME ZONE p.timezone)::date < :end_date
            WHERE p.id = :property_id AND p.tenant_id = :tenant_id
            GROUP BY p.id
        """), {"property_id": property_id, "tenant_id": tenant_id,
               "start_date": start_date, "end_date": end_date})
        row = result.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Property not found")
    if row.currency_count > 1:
        raise HTTPException(status_code=409, detail="Cannot combine revenue in different currencies")
    return {
        "property_id": property_id,
        "tenant_id": tenant_id,
        "total": str(Decimal(str(row.total_revenue))),
        "currency": row.currency or "USD",
        "count": row.reservation_count,
    }
