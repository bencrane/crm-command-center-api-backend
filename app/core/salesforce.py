import hashlib
import hmac
import secrets
from datetime import datetime, timezone
from urllib.parse import urlencode

import httpx

from app.core.config import settings

# Salesforce OAuth endpoints
SF_AUTH_BASE = "https://login.salesforce.com"
SF_AUTHORIZE_URL = f"{SF_AUTH_BASE}/services/oauth2/authorize"
SF_TOKEN_URL = f"{SF_AUTH_BASE}/services/oauth2/token"
SF_REVOKE_URL = f"{SF_AUTH_BASE}/services/oauth2/revoke"

# Scopes we request
SF_SCOPES = "api refresh_token"


def generate_oauth_state(org_id: str) -> str:
    """
    Generate a signed state parameter for the OAuth flow.
    Format: {random_nonce}:{org_id}:{signature}
    """
    nonce = secrets.token_urlsafe(32)
    payload = f"{nonce}:{org_id}"
    signature = hmac.new(
        settings.app_secret.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()[:16]
    return f"{payload}:{signature}"


def verify_oauth_state(state: str) -> str | None:
    """
    Verify the signed state and extract org_id.
    Returns org_id if valid, None if tampered.
    """
    parts = state.split(":")
    if len(parts) != 3:
        return None

    nonce, org_id, signature = parts
    payload = f"{nonce}:{org_id}"
    expected = hmac.new(
        settings.app_secret.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()[:16]

    if not hmac.compare_digest(signature, expected):
        return None

    return org_id


def build_authorization_url(org_id: str) -> str:
    """Build the Salesforce OAuth authorization URL."""
    state = generate_oauth_state(org_id)
    params = {
        "response_type": "code",
        "client_id": settings.salesforce_client_id,
        "redirect_uri": settings.salesforce_redirect_uri,
        "scope": SF_SCOPES,
        "state": state,
        "prompt": "login consent",
    }
    return f"{SF_AUTHORIZE_URL}?{urlencode(params)}"


async def exchange_code_for_tokens(code: str) -> dict:
    """
    Exchange an authorization code for access + refresh tokens.
    Returns the raw Salesforce token response dict.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            SF_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": settings.salesforce_client_id,
                "client_secret": settings.salesforce_client_secret,
                "redirect_uri": settings.salesforce_redirect_uri,
            },
        )
        response.raise_for_status()
        return response.json()


async def refresh_access_token(refresh_token: str) -> dict:
    """
    Use a refresh token to get a new access token.
    Returns the raw Salesforce token response dict.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            SF_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": settings.salesforce_client_id,
                "client_secret": settings.salesforce_client_secret,
            },
        )
        response.raise_for_status()
        return response.json()


async def test_salesforce_connection(instance_url: str, access_token: str) -> dict:
    """
    Call the Salesforce versions endpoint to verify the connection is alive.
    Returns org info on success.
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        # Get available API versions
        response = await client.get(
            f"{instance_url}/services/data/",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        versions = response.json()
        latest = versions[-1] if versions else {}

        # Get org info using the latest API version
        if latest.get("url"):
            org_response = await client.get(
                f"{instance_url}{latest['url']}/query",
                params={"q": "SELECT Id, Name, OrganizationType FROM Organization LIMIT 1"},
                headers={"Authorization": f"Bearer {access_token}"},
            )
            org_response.raise_for_status()
            org_data = org_response.json()
            records = org_data.get("records", [])
            org_info = records[0] if records else {}
        else:
            org_info = {}

        return {
            "connected": True,
            "instance_url": instance_url,
            "api_version": latest.get("version", "unknown"),
            "org_name": org_info.get("Name"),
            "org_type": org_info.get("OrganizationType"),
            "salesforce_org_id": org_info.get("Id"),
            "tested_at": datetime.now(timezone.utc).isoformat(),
        }
