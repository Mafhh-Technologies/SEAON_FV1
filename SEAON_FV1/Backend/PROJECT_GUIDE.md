# SEAON Project Guide

If you are not a programmer, remember these three things:

1. `app.py` starts everything.
2. `public/` is the website users see.
3. `erp/` contains the business rules and database API.

## File responsibilities

- `app.py` — one-click startup.
- `manage.py` — standard Django maintenance commands.
- `config/settings.py` — Django configuration and SQLite.
- `config/urls.py` — connects browser URLs and API URLs.
- `erp/models.py` — database tables.
- `erp/serializers.py` — converts database records to/from API JSON.
- `erp/views.py` — API endpoints.
- `erp/services.py` — business logic such as FIFO.
- `erp/permissions.py` — role/permission checks.
- `erp/admin_api.py` — friendly admin-panel API.
- `erp/management/commands/seed_seaon.py` — creates demo administrator, roles and base data.
- `erp/management/commands/import_sample_data.py` — imports supplied Excel files.
- `public/login.html` — login page.
- `public/index.html` — main ERP shell.
- `public/admin.html` — Super Admin panel.
- `public/JS/api.js` — all browser-to-server requests.
- `public/JS/auth.js` — login/session handling.
- `public/JS/app.js` — all ERP screens and button actions.
- `public/JS/admin.js` — admin-panel screens and actions.
- `public/CSS/style.css` — complete application styling.

## Data flow

Button → `app.js` → `api.js` → Django URL → Django view/service → SQLite model.

Keep this flow when adding features. It prevents the frontend and backend from becoming disconnected.


## Recent repair notes (2026-10-15)

- `erp.views` imports `user_can` explicitly. This helper is used by warehouse, returns, FIFO, reports, and branding endpoints; without the import those screens can fail with a Python `NameError`.
- `public/JS/api.js` is the shared authenticated HTTP client. It is exposed as `window.API` (preferred) and compatibility aliases `window.Api` / `window.api`; it parses API errors into readable messages.
- Return cases track a returned quantity and `return_stock_added`. When a case transitions to `received`, the returned quantity is added to inventory once, and stock/warehouse ledgers are updated.
- Warehouse inward movements update inventory and FIFO batches. Pick/putaway/pack/dispatch are movement-ledger events so the order workflow does not deduct the same quantity twice. Use the FIFO Consume action for a deliberate additional stock consumption.
- Branding is stored in the `BrandSettings` singleton. After saving, the main ERP and admin shell read the same settings from `/api/branding/`.
- New database migration: `0007_return_quantity_tracking.py`. `python app.py` runs migrations during startup; manual alternative: `python manage.py migrate`.

### Quick developer checks

```powershell
python -m compileall app.py manage.py config erp
node --check public/JS/api.js
node --check public/JS/app.js
node --check public/JS/admin.js
python manage.py check
```
