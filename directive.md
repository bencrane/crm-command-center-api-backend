```
Create a new FastAPI project for Salesforce CRM configuration tool:

**Project name:** salesforce-config-api (or crm-config-api if you want to leave room for others)

**Foundation to build:**

1. **FastAPI app structure:**
   - Standard FastAPI setup with uvicorn
   - Environment config with Pydantic Settings
   - Health check endpoint
   - CORS middleware
   - Error handling

2. **Database:**
   - Supabase PostgreSQL connection
   - Multi-tenant with org_id (reuse Service-Engine pattern)
   - Tables needed:
     - organizations (reuse Service-Engine orgs)
     - salesforce_connections (org_id, access_token, refresh_token, instance_url)
     - saved_configs (dashboards, workflows user has built)

3. **Salesforce OAuth:**
   - OAuth 2.0 flow endpoints
   - Token storage and refresh
   - Salesforce API client wrapper

4. **Deployment:**
   - Railway-ready (Dockerfile, railway.json)
   - Environment variables for Salesforce OAuth credentials

5. **Initial endpoints:**
   - POST /auth/salesforce/connect - initiate OAuth
   - GET /auth/salesforce/callback - handle OAuth redirect
   - GET /salesforce/test - test connection works

Build the foundation so I can then add actual Salesforce operations (dashboards, workflows) on top of working auth/connection layer.

Use the same patterns as Service-Engine (multi-tenant, Supabase, Railway deployment).
```