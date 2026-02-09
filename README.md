# CRM Config API

Standalone FastAPI backend for Salesforce CRM configuration. Multi-tenant SaaS with OAuth-based Salesforce integration.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/orgs` | Create organization |
| `GET` | `/orgs/{org_id}` | Get organization |
| `POST` | `/auth/salesforce/connect` | Get Salesforce OAuth URL (requires `X-Org-ID` header) |
| `GET` | `/auth/salesforce/callback` | OAuth callback (Salesforce redirects here) |
| `GET` | `/salesforce/test` | Test Salesforce connection (requires `X-Org-ID` header) |

## Local Development

```bash
# Create venv
python3.13 -m venv .venv
source .venv/bin/activate

# Install deps
pip install -r requirements.txt

# Copy env template and fill in values
cp .env.example .env

# Run migrations
alembic upgrade head

# Start dev server
uvicorn app.main:app --reload
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | Supabase PostgreSQL connection (use `postgresql+asyncpg://` scheme) |
| `SALESFORCE_CLIENT_ID` | Yes | From Salesforce Connected App |
| `SALESFORCE_CLIENT_SECRET` | Yes | From Salesforce Connected App |
| `SALESFORCE_REDIRECT_URI` | Yes | OAuth callback URL (must match Connected App config) |
| `ENCRYPTION_KEY` | Yes | Fernet key for token encryption at rest |
| `APP_SECRET` | Yes | Secret for HMAC signing OAuth state |
| `CORS_ORIGINS` | No | JSON list of allowed origins (default: `["http://localhost:3000"]`) |
| `DEBUG` | No | Enable debug mode (default: `false`) |
| `PORT` | No | Server port — Railway sets this automatically (default: `8000`) |

## Deploy to Railway

1. Push to GitHub
2. Connect repo in Railway dashboard
3. Set environment variables in Railway service settings
4. Railway auto-detects `railway.json` and builds from Dockerfile
5. Migrations run automatically on deploy

## Architecture

- **FastAPI** + **uvicorn** (async, uvloop)
- **SQLAlchemy 2.0** async with **asyncpg** driver
- **Supabase PostgreSQL** for persistence
- **Alembic** for schema migrations
- **Fernet** symmetric encryption for Salesforce tokens at rest
- Multi-tenant via `org_id` scoping on all queries
- HMAC-signed OAuth state to prevent CSRF
