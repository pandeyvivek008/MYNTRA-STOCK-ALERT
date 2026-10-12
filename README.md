# Myntra Stock Watch

A live size-level inventory monitor for fashion catalogues. It tracks SKU/size stock, calculates urgency from reorder thresholds, creates actionable alerts, and pushes changes to every open dashboard through WebSockets.

## Included

- Responsive UI for phone, tablet and desktop
- Size-run view (S to XXL), low/critical/out-of-stock states
- Live WebSocket notification bell and alert stream
- Search, filter, acknowledgement and resolved-alert workflow
- CSV inventory import endpoint for ERP/WMS/Myntra feed integrations
- Secure Myntra-order connector endpoint which atomically reduces stock for each SKU, colour and size
- Idempotent order processing: a repeated marketplace order cannot reduce stock twice
- Optional Meta WhatsApp Cloud API template notification for critical / out-of-stock alerts
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
- `POST /api/integrations/myntra/orders` – authenticated normalized order feed; stock is reduced per `sku`, `color`, and `size`
- `WS /ws/alerts?token=...` – live `stock_changed` and `alert_created` events

### Order connector payload

Myntra must provide official Seller API credentials and its exact order schema. Connect their webhook/polling adapter to this normalized, idempotent endpoint rather than exposing your dashboard login:

```json
{
  "order_id": "MYNTRA-ORDER-92831",
  "items": [{"sku": "MTR-KRT-1056", "color": "Indigo", "size": "M", "quantity": 1}]
}
```

Send `X-Integration-Secret` with the value of `INTEGRATION_WEBHOOK_SECRET`. The server decreases the matching variant stock, creates an alert at the reorder threshold, pushes the live dashboard update, and sends a WhatsApp template alert when Meta credentials are present.

For WhatsApp configure `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_ALERT_TO`, and an approved `stock_alert` template containing six body variables: product name, SKU, size, colour, remaining units, severity.

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
