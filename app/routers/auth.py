import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import encrypt_token
from app.core.salesforce import (
    build_authorization_url,
    exchange_code_for_tokens,
    verify_oauth_state,
)
from app.dependencies.database import get_db
from app.dependencies.org import get_verified_org
from app.models.organization import Organization
from app.models.salesforce_connection import SalesforceConnection
from app.schemas.salesforce import SalesforceConnectResponse

router = APIRouter(prefix="/auth/salesforce", tags=["salesforce-auth"])


@router.post(
    "/connect",
    response_model=SalesforceConnectResponse,
)
async def initiate_salesforce_connect(
    org: Organization = Depends(get_verified_org),
):
    """
    Generate a Salesforce OAuth authorization URL.
    The client should redirect the user to this URL.
    """
    authorization_url = build_authorization_url(str(org.id))
    return SalesforceConnectResponse(authorization_url=authorization_url)


@router.get("/callback")
async def salesforce_callback(
    code: str = Query(..., description="Authorization code from Salesforce"),
    state: str = Query(..., description="Signed state parameter"),
    db: AsyncSession = Depends(get_db),
):
    """
    Handle the OAuth callback from Salesforce.
    Exchanges the code for tokens and stores them encrypted in the DB.
    """
    # Verify state signature and extract org_id
    org_id_str = verify_oauth_state(state)
    if org_id_str is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or tampered state parameter",
        )

    try:
        org_id = uuid.UUID(org_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid org_id in state parameter",
        )

    # Verify org exists
    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Exchange code for tokens
    try:
        token_data = await exchange_code_for_tokens(code)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to exchange code with Salesforce: {e}",
        )

    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    instance_url = token_data.get("instance_url")
    sf_org_id = token_data.get("id", "").split("/")[-1] if token_data.get("id") else None

    if not access_token or not instance_url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Salesforce returned incomplete token data",
        )

    # Upsert: check for existing connection for this org
    existing_result = await db.execute(
        select(SalesforceConnection).where(SalesforceConnection.org_id == org_id)
    )
    existing = existing_result.scalar_one_or_none()

    if existing:
        # Update existing connection
        existing.access_token = encrypt_token(access_token)
        existing.refresh_token = encrypt_token(refresh_token) if refresh_token else existing.refresh_token
        existing.instance_url = instance_url
        existing.salesforce_org_id = sf_org_id
    else:
        # Create new connection
        connection = SalesforceConnection(
            org_id=org_id,
            access_token=encrypt_token(access_token),
            refresh_token=encrypt_token(refresh_token or ""),
            instance_url=instance_url,
            salesforce_org_id=sf_org_id,
        )
        db.add(connection)

    await db.flush()

    # In production, redirect to a frontend success page.
    # For now, return a simple JSON success indicator via redirect.
    return {
        "status": "connected",
        "org_id": str(org_id),
        "instance_url": instance_url,
        "message": "Salesforce connection established successfully",
    }
