# Myntra Stock Watch

A live size-level inventory monitor for fashion catalogues. It tracks SKU/size stock, calculates urgency from reorder thresholds, creates actionable alerts, and pushes changes to every open dashboard through WebSockets.

## Included

- Responsive UI for phone, tablet and desktop
- Size-run view (S to XXL), low/critical/out-of-stock states
- Live WebSocket notification bell and alert stream
- Search, filter, acknowledgement and resolved-alert workflow
- CSV inventory import endpoint for ERP/WMS/Myntra feed integrations
- REST API designed for scheduled feed syncs; no scraping is included
- SQLite locally and Railway PostgreSQL in production

## Local start

```powershell
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Or, after making `.env`, simply run `./run-local.ps1` in the VS Code terminal.

Open `http://127.0.0.1:8000`. Default demo login comes from `.env`: `admin@example.com` / `change-me-before-production`.

## API quick reference

- `POST /api/auth/login` – receive access token
- `GET /api/dashboard` – KPI and recent alerts
- `GET /api/products?query=&status=` – SKU grid
- `GET /api/products/{id}` – product and all sizes
- `PATCH /api/alerts/{id}` – `acknowledged` or `resolved`
- `POST /api/imports/inventory` – CSV multipart upload; columns: `sku,name,category,size,quantity,reorder_point`
- `WS /ws/alerts?token=...` – live `stock_changed` and `alert_created` events

## Railway deployment

1. Create a GitHub repo, then use the commands below.
2. In Railway: **New Project → Deploy from GitHub**, choose the repo, then add a **PostgreSQL** service.
3. In the app service Variables, set `DATABASE_URL` to Railway's PostgreSQL connection URL (normally reference `${{Postgres.DATABASE_URL}}`), plus a strong `JWT_SECRET`, `ADMIN_EMAIL` and `ADMIN_PASSWORD`.
4. Railway detects `railway.toml` and Dockerfile. Deploy. Open the generated domain.

```powershell
git init
git add .
git commit -m "Initial Myntra Stock Watch"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/myntra-stock-watch.git
git push -u origin main
```

Never commit `.env`. Change the demo password and JWT secret before publishing.
