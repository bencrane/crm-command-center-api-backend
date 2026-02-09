import uuid

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.database import get_db
from app.models.organization import Organization


async def get_org_id(
    x_org_id: str = Header(..., description="Organization ID (UUID)"),
) -> uuid.UUID:
    """Extract and validate org_id from the X-Org-ID request header."""
    try:
        return uuid.UUID(x_org_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Org-ID header must be a valid UUID",
        )


async def get_verified_org(
    org_id: uuid.UUID = Depends(get_org_id),
    db: AsyncSession = Depends(get_db),
) -> Organization:
    """Resolve org_id to a real Organization row. 403 if it doesn't exist."""
    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization not found or access denied",
        )
    return org
