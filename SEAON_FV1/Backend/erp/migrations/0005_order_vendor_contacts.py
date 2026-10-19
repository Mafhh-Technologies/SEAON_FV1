from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("erp", "0004_order_type")]

    operations = [
        migrations.AddField(
            model_name="order",
            name="vendor_email",
            field=models.EmailField(blank=True, max_length=254),
        ),
        migrations.AddField(
            model_name="order",
            name="vendor_whatsapp",
            field=models.CharField(blank=True, help_text="Vendor WhatsApp number in international format, e.g. +919876543210", max_length=30),
        ),
    ]
