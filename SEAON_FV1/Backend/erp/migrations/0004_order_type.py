from django.db import migrations, models
class Migration(migrations.Migration):
    dependencies=[("erp","0003_operations")]
    operations=[migrations.AddField(model_name="order",name="order_type",field=models.CharField(default="manufactured",max_length=20))]
