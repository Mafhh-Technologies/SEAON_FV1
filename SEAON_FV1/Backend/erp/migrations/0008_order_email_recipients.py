# Store the order creator's reply-to address and multiple vendor recipients.
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("erp", "0007_return_quantity_tracking")]

    operations = [
        migrations.AddField(
            model_name="order",
            name="sender_email",
            field=models.EmailField(blank=True, help_text="Reply-to email supplied by the person creating the order", max_length=254),
        ),
        migrations.AddField(
            model_name="order",
            name="vendor_emails",
            field=models.JSONField(blank=True, default=list, help_text="Multiple vendor recipient email addresses"),
        ),
    ]
