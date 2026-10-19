# Add explicit returned quantity and a one-time restock guard to return cases.
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("erp", "0006_workflow_notifications_branding")]

    operations = [
        migrations.AddField(
            model_name="returnrecord",
            name="return_quantity",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14),
        ),
        migrations.AddField(
            model_name="returnrecord",
            name="return_stock_added",
            field=models.BooleanField(default=False),
        ),
    ]
