# SEAON ERP — Simple Windows Application

SEAON is a Django + SQLite ERP for manufacturing, stock and warehouse operations.

## The only thing a normal user needs to know

### Windows
Double-click:

`run_seaon_windows.bat`

The script creates the environment, installs the packages and starts the whole application.

Then open:

`http://127.0.0.1:8000/app/login.html`

### Default administrator
Email: `admin@seaon.com`
Password: `Admin@123`

## How the application works

There is one backend process:

`Backend/app.py`

It automatically:

1. Runs Django migrations.
2. Creates the default administrator and roles.
3. Imports the supplied Excel stock sheets.
4. Creates FIFO opening batches.
5. Starts the Django server.

The browser frontend and Django API are served by the same server.

## Main screens

- Dashboard — KPIs and operational health
- Inventory — stock and adjustments
- Orders — manufactured/readymade orders
- Production — work orders
- BOM / Materials — material mapping
- Warehouse — inward, putaway, pick, pack and dispatch
- Returns — return/repair/replacement/redelivery workflow
- FIFO Batches — oldest stock first
- Reports — management summaries
- Alerts — low/dead/near-expiry stock
- Admin Panel — users, roles, permissions, imported stock and audit log

## Admin Panel

Open:

`http://127.0.0.1:8000/app/admin.html`

Only Super Admin/Admin accounts can enter it.

The Super Admin can:
- create users
- activate/deactivate users
- assign roles
- create custom roles
- choose permissions
- inspect imported spreadsheet data
- re-import Excel data
- review audit logs

## Supplied sample data

The Excel files are stored in:

`Backend/sample_data/`

They are imported into SQLite automatically when `app.py` starts.

The original spreadsheet row is retained in `StockRecord` with:
- source file
- sheet
- source row
- category
- item
- size
- colour
- thickness
- width
- length
- minimum stock
- available stock
- required stock
- remarks

Imported stock is also converted into products/inventory and opening FIFO batches so the software can be tested immediately.

## Database

SQLite file:

`Backend/seaon.db`

You do not need to create it manually.

## Developer commands

```powershell
cd Backend
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_seaon
python manage.py import_sample_data
python manage.py runserver
```

Normal operation should use `python app.py`.

## Important URLs

- ERP: `http://127.0.0.1:8000/app/login.html`
- Admin panel: `http://127.0.0.1:8000/app/admin.html`
- Django technical admin: `http://127.0.0.1:8000/admin/`
- API health: `http://127.0.0.1:8000/api/health/`

## Source of the business design

The supplied `SEAON - DASHBOARD Requirements.pdf` is included under `Backend/docs/`.
The implementation covers the requested Super Admin, role permissions, order flows, returns,
product types, BOM mapping, FIFO inventory, production, warehouse, alerts and role-aware dashboards.

For production deployment, change the development secret, DEBUG, allowed hosts, CORS settings
and demo credentials.


## Vendor email and WhatsApp order notifications

When a user creates an order, SEAON attempts to notify the vendor using the email address and/or WhatsApp number entered on the order form. An order is still saved if a provider is not configured or temporarily fails. The create-order response and success toast show each channel status (`sent`, `failed`, `not_configured`, or `skipped`). `sent` means the provider accepted the request, not necessarily that the vendor read the message.

### Configure notifications on Windows

1. Copy `Backend/.env.example` to `Backend/.env`.
2. Add valid SMTP credentials and/or WhatsApp Cloud API credentials. Do not share or commit `Backend/.env`.
3. Restart `python app.py`.

**Email:** For Gmail, use an app password (with 2-Step Verification enabled), not your regular account password. Some email providers require different SMTP host/port settings.

**WhatsApp:** Create/configure a WhatsApp Business Platform app, set `WHATSAPP_ACCESS_TOKEN` and `WHATSAPP_PHONE_NUMBER_ID`, and use a recipient number in international format (for example `+919876543210`). The recipient must be eligible to receive messages under Meta's policies. Outside the customer-service window, WhatsApp generally requires an approved message template rather than a free-form text message; this implementation sends a text message and reports API errors instead of pretending it was sent. For reliable production order alerts outside that window, configure an approved template and adapt the payload to that template.

Notifications are sent from the backend. Real credentials are required for real delivery; without them, order creation works and the UI will report `not_configured`.


## Order, inventory and BOM workflow update

- Manufactured orders check the selected product's BOM and live component inventory before saving. If any required component is short, the order is rejected and an in-app notification is recorded.
- When a manufactured order is accepted, the required BOM components are deducted atomically and a linked production job is created. The frontend redirects to Production. Materials are not deducted again when that job is completed.
- Readymade orders check and deduct finished-product inventory at order creation.
- Completing production adds finished goods to inventory and moves the linked order to Packed. Dispatching a manufactured order deducts the finished goods and records a warehouse dispatch.
- Orders can be filtered by New Order, In Production, Packed and Dispatched.
- BOM is initially collapsed to a product selector. Choosing a product shows only that product's material rows, with add/edit/delete actions.
- Inventory supports product create/edit/delete, stock adjustment and stock receipt. Products tied to orders, production, or BOM records cannot be deleted.
- Notifications are stored in SQLite and can be marked read or cleared. Provider email/WhatsApp notifications remain dependent on valid credentials in `Backend/.env`.
- Admin Panel → Logo & Branding lets an administrator configure company name, tagline, fixed logo text, color and shape.

Business rule note: this build deducts BOM components when the manufactured order is accepted, as requested, and marks them reserved/consumed so production completion does not deduct them twice. If your factory prefers material consumption only at production start, that timing should be changed before live production use.
