import uuid
from datetime import datetime

from pydantic import BaseModel


class SalesforceConnectRequest(BaseModel):
    """Request body for initiating OAuth (currently empty — org_id comes from header)."""
    pass


class SalesforceConnectResponse(BaseModel):
    """Response with the authorization URL to redirect the user to."""
    authorization_url: str
    message: str = "Redirect the user to this URL to authorize Salesforce access"


class SalesforceConnectionResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    instance_url: str
    salesforce_org_id: str | None
    token_expires_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SalesforceTestResponse(BaseModel):
    connected: bool
    instance_url: str
    api_version: str
    org_name: str | None
    org_type: str | None
    salesforce_org_id: str | None
    tested_at: str
