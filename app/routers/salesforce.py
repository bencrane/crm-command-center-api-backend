from fastapi import APIRouter, Depends, HTTPException, status
from httpx import HTTPStatusError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.salesforce import test_salesforce_connection
from app.dependencies.database import get_db
from app.dependencies.salesforce import (
    DecryptedSalesforceConnection,
    get_salesforce_connection,
    refresh_and_update_token,
)
from app.schemas.salesforce import SalesforceTestResponse

router = APIRouter(prefix="/salesforce", tags=["salesforce"])


@router.get("/test", response_model=SalesforceTestResponse)
async def test_connection(
    sf_conn: DecryptedSalesforceConnection = Depends(get_salesforce_connection),
    db: AsyncSession = Depends(get_db),
):
    """
    Test the Salesforce connection for the current org.
    Automatically refreshes the access token if it has expired (401 from SF).
    Returns Salesforce org metadata on success.
    """
    try:
        result = await test_salesforce_connection(
            instance_url=sf_conn.instance_url,
            access_token=sf_conn.access_token,
        )
        return SalesforceTestResponse(**result)
    except HTTPStatusError as e:
        if e.response.status_code == 401:
            # Token expired — attempt refresh and retry
            sf_conn = await refresh_and_update_token(sf_conn, db)
            try:
                result = await test_salesforce_connection(
                    instance_url=sf_conn.instance_url,
                    access_token=sf_conn.access_token,
                )
                return SalesforceTestResponse(**result)
            except HTTPStatusError as retry_err:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Salesforce API error after token refresh: {retry_err.response.status_code} {retry_err.response.text}",
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Salesforce API error: {e.response.status_code} {e.response.text}",
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to connect to Salesforce: {e}",
        )
