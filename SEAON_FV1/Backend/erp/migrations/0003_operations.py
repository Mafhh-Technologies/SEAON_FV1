from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies=[("erp","0002_admin_and_import_data")]
    operations=[
        migrations.CreateModel(
            name="InventoryBatch",
            fields=[
                ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
                ("batch_code",models.CharField(max_length=80,unique=True)),
                ("received_date",models.DateField()),
                ("vendor",models.CharField(blank=True,max_length=160)),
                ("expiry_date",models.DateField(blank=True,null=True)),
                ("quantity",models.DecimalField(decimal_places=2,default=0,max_digits=14)),
                ("remaining_quantity",models.DecimalField(decimal_places=2,default=0,max_digits=14)),
                ("unit_cost",models.DecimalField(decimal_places=2,default=0,max_digits=14)),
                ("created_at",models.DateTimeField(auto_now_add=True)),
                ("product",models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name="batches",to="erp.product")),
            ],
            options={"ordering":["received_date","id"]},
        ),
        migrations.CreateModel(
            name="WarehouseTransaction",
            fields=[
                ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
                ("transaction_type",models.CharField(choices=[("inward","Inward"),("putaway","Putaway"),("pick","Pick"),("pack","Pack"),("dispatch","Dispatch"),("return-receive","Return Receive")],max_length=30)),
                ("quantity",models.DecimalField(decimal_places=2,max_digits=14)),
                ("reference",models.CharField(blank=True,max_length=100)),
                ("notes",models.CharField(blank=True,max_length=255)),
                ("created_at",models.DateTimeField(auto_now_add=True)),
                ("product",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name="warehouse_transactions",to="erp.product")),
            ],
        ),
        migrations.CreateModel(
            name="ReturnRecord",
            fields=[
                ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
                ("reason",models.TextField()),
                ("damage_notes",models.TextField(blank=True)),
                ("photos",models.TextField(blank=True)),
                ("status",models.CharField(choices=[("requested","Return Requested"),("received","Return Received"),("inspection","Under Inspection"),("repair","Repair / Rework"),("replacement","Replacement"),("redelivery","Ready for Redelivery"),("closed","Closed")],default="requested",max_length=30)),
                ("replacement_mode",models.CharField(choices=[("repair","Repair"),("replacement","Replacement"),("refund","Refund")],default="replacement",max_length=30)),
                ("redelivery_status",models.CharField(default="Not scheduled",max_length=40)),
                ("created_at",models.DateTimeField(auto_now_add=True)),
                ("updated_at",models.DateTimeField(auto_now=True)),
                ("order",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name="returns",to="erp.order")),
            ],
        ),
    ]
