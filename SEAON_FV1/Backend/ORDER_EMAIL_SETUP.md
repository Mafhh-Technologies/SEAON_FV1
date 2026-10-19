# SEAON order email notifications

## How order creators use it

1. Open **Orders → Create Order**.
2. Enter the creator's **Your sender / reply-to email**.
3. Enter one or more vendor addresses in **Vendor email addresses**, separated by commas, semicolons, or new lines.
4. Complete the product and quantity fields. The live stock/BOM check must pass.
5. Click **Create Order** once. SEAON saves the order and immediately attempts to email all listed vendors with the order number, customer, product, SKU, quantity, type, status, date, and notes. No separate notification panel is needed.

## Configure the mail account once (administrator/installer)

1. In `Backend`, copy `.env.example` to `.env`.
2. Set `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, and `DEFAULT_FROM_EMAIL`. For Gmail, use an App Password, not the normal account password.
3. Restart `python app.py`.
4. Test with a real recipient address. Check the Create Order toast for `Email: sent`, `failed`, or `not_configured`.

The sender address entered by the order creator is configured as **Reply-To**. The actual From address remains the authenticated `DEFAULT_FROM_EMAIL`, because SMTP providers generally do not allow an application to send as an arbitrary address.

If email settings are not configured, the order can still be saved and the response clearly reports `not_configured`; the app does not pretend that an email was delivered. `sent` means the SMTP server accepted the message, not that the recipient read it.
