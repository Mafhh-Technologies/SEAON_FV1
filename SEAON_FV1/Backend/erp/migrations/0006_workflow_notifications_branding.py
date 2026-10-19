from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("erp", "0005_order_vendor_contacts")]

    operations = [
        migrations.AddField(
            model_name="productionorder",
            name="order",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="production_jobs", to="erp.order"),
        ),
        migrations.AddField(
            model_name="productionorder",
            name="materials_reserved",
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name="Notification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=180)),
                ("message", models.TextField()),
                ("kind", models.CharField(default="info", max_length=30)),
                ("is_read", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="BrandSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("company_name", models.CharField(default="SEAON", max_length=100)),
                ("tagline", models.CharField(default="Manufacturing & Stock", max_length=160)),
                ("logo_text", models.CharField(default="S", max_length=5)),
                ("logo_color", models.CharField(default="#2563eb", max_length=7)),
                ("logo_style", models.CharField(choices=[("rounded", "Rounded square"), ("circle", "Circle"), ("square", "Square")], default="rounded", max_length=20)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
