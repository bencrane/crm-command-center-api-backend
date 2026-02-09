import uuid
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import decrypt_token, encrypt_token
from app.core.salesforce import refresh_access_token
from app.dependencies.database import get_db
from app.dependencies.org import get_verified_org
from app.models.organization import Organization
from app.models.salesforce_connection import SalesforceConnection


@dataclass
class DecryptedSalesforceConnection:
    """Holds decrypted tokens + connection metadata, never serialized to a response."""

    id: uuid.UUID
    org_id: uuid.UUID
    access_token: str  # plaintext
    refresh_token: str  # plaintext
    instance_url: str
    salesforce_org_id: str | None


async def get_salesforce_connection(
    org: Organization = Depends(get_verified_org),
    db: AsyncSession = Depends(get_db),
) -> DecryptedSalesforceConnection:
    """
    Resolve the Salesforce connection for the current org.
    Returns decrypted tokens ready for API calls.
    404 if no connection exists.
    """
    result = await db.execute(
        select(SalesforceConnection).where(SalesforceConnection.org_id == org.id)
    )
    conn = result.scalar_one_or_none()

    if conn is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Salesforce connection found for this organization. Use POST /auth/salesforce/connect first.",
        )

    try:
        access_token = decrypt_token(conn.access_token)
        refresh_token = decrypt_token(conn.refresh_token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to decrypt stored Salesforce tokens. Encryption key may have changed.",
        )

    return DecryptedSalesforceConnection(
        id=conn.id,
        org_id=conn.org_id,
        access_token=access_token,
        refresh_token=refresh_token,
        instance_url=conn.instance_url,
        salesforce_org_id=conn.salesforce_org_id,
    )


async def refresh_and_update_token(
    sf_conn: DecryptedSalesforceConnection,
    db: AsyncSession,
) -> DecryptedSalesforceConnection:
    """
    Refresh the access token using the stored refresh token.
    Updates the DB row and returns a new DecryptedSalesforceConnection with the fresh token.
    """
    try:
        token_data = await refresh_access_token(sf_conn.refresh_token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to refresh Salesforce token: {e}. User may need to re-authorize.",
        )

    new_access_token = token_data.get("access_token")
    if not new_access_token:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Salesforce returned no access token on refresh.",
        )

    # Update DB
    result = await db.execute(
        select(SalesforceConnection).where(SalesforceConnection.id == sf_conn.id)
    )
    conn = result.scalar_one()
    conn.access_token = encrypt_token(new_access_token)
    conn.instance_url = token_data.get("instance_url", sf_conn.instance_url)
    await db.flush()

    return DecryptedSalesforceConnection(
        id=sf_conn.id,
        org_id=sf_conn.org_id,
        access_token=new_access_token,
        refresh_token=sf_conn.refresh_token,
        instance_url=conn.instance_url,
        salesforce_org_id=sf_conn.salesforce_org_id,
    )
