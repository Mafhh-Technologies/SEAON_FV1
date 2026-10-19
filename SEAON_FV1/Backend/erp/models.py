# DATABASE MODELS: every class below becomes a SQLite table. Keep business data here.
from django.contrib.auth.models import User
from django.db import models

class UserProfile(models.Model):
    user=models.OneToOneField(User,on_delete=models.CASCADE,related_name="profile")
    role=models.CharField(max_length=30,default="viewer")
    full_name=models.CharField(max_length=160,blank=True)

class Product(models.Model):
    name=models.CharField(max_length=160)
    sku=models.CharField(max_length=80,unique=True)
    product_type=models.CharField(max_length=30)
    unit=models.CharField(max_length=20,default="pcs")
    minimum_stock=models.DecimalField(max_digits=14,decimal_places=2,default=0)
    location=models.CharField(max_length=120,blank=True)
    thickness=models.DecimalField(max_digits=10,decimal_places=2,null=True,blank=True)
    size=models.CharField(max_length=80,blank=True)
    color=models.CharField(max_length=80,blank=True)
    is_active=models.BooleanField(default=True)
    created_at=models.DateTimeField(auto_now_add=True)

class Inventory(models.Model):
    product=models.OneToOneField(Product,on_delete=models.CASCADE,related_name="inventory")
    quantity=models.DecimalField(max_digits=14,decimal_places=2,default=0)
    average_cost=models.DecimalField(max_digits=14,decimal_places=2,default=0)
    updated_at=models.DateTimeField(auto_now=True)

class StockMovement(models.Model):
    product=models.ForeignKey(Product,on_delete=models.CASCADE,related_name="movements")
    quantity_change=models.DecimalField(max_digits=14,decimal_places=2)
    quantity_after=models.DecimalField(max_digits=14,decimal_places=2)
    movement_type=models.CharField(max_length=40,default="adjustment")
    note=models.CharField(max_length=255,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)

class Order(models.Model):
    order_number=models.CharField(max_length=50,unique=True)
    order_type=models.CharField(max_length=20,default="manufactured")
    customer_name=models.CharField(max_length=160)
    customer_email=models.EmailField(blank=True)
    vendor_email=models.EmailField(blank=True)  # Legacy primary recipient; retained for older records.
    sender_email=models.EmailField(blank=True, help_text="Reply-to email supplied by the person creating the order")
    vendor_emails=models.JSONField(default=list, blank=True, help_text="Multiple vendor recipient email addresses")
    vendor_whatsapp=models.CharField(max_length=30,blank=True,help_text="Vendor WhatsApp number in international format, e.g. +919876543210")
    product=models.ForeignKey(Product,on_delete=models.PROTECT,related_name="orders")
    quantity=models.DecimalField(max_digits=14,decimal_places=2)
    status=models.CharField(max_length=20,default="pending")
    notes=models.TextField(blank=True)
    created_at=models.DateTimeField(auto_now_add=True)

class ProductionOrder(models.Model):
    production_number=models.CharField(max_length=50,unique=True)
    product=models.ForeignKey(Product,on_delete=models.PROTECT,related_name="production_orders")
    customer_name=models.CharField(max_length=160,blank=True)
    quantity=models.DecimalField(max_digits=14,decimal_places=2)
    produced_quantity=models.DecimalField(max_digits=14,decimal_places=2,default=0)
    status=models.CharField(max_length=20,default="in-progress")
    assigned_to=models.CharField(max_length=160,blank=True)
    started_at=models.DateTimeField(auto_now_add=True)
    completed_at=models.DateTimeField(null=True,blank=True)
    order=models.ForeignKey("Order",null=True,blank=True,on_delete=models.SET_NULL,related_name="production_jobs")
    materials_reserved=models.BooleanField(default=False)

class BOMItem(models.Model):
    product=models.ForeignKey(Product,on_delete=models.CASCADE,related_name="bom_items")
    component_product=models.ForeignKey(Product,on_delete=models.PROTECT,related_name="used_in_boms")
    quantity_per_unit=models.DecimalField(max_digits=14,decimal_places=4)
    unit=models.CharField(max_length=20,default="pcs")
    class Meta:
        constraints=[models.UniqueConstraint(fields=["product","component_product"],name="unique_bom_component")]

class RefreshToken(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE,related_name="refresh_tokens")
    token_hash=models.CharField(max_length=64,unique=True)
    expires_at=models.DateTimeField()
    revoked=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)


class PermissionRule(models.Model):
    """Simple module/action permission used by the friendly admin panel."""
    role = models.CharField(max_length=60)
    code = models.CharField(max_length=100)
    label = models.CharField(max_length=160)
    module = models.CharField(max_length=60)
    enabled = models.BooleanField(default=True)

    class Meta:
        unique_together = ("role", "code")

class RoleDefinition(models.Model):
    """Human-friendly role definition. Permissions are stored as JSON text for SQLite simplicity."""
    name = models.CharField(max_length=60, unique=True)
    description = models.CharField(max_length=255, blank=True)
    permissions_json = models.TextField(default="[]")
    is_system = models.BooleanField(default=False)

class AuditLog(models.Model):
    """Records important admin/user actions."""
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=100)
    module = models.CharField(max_length=60, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class StockRecord(models.Model):
    """Faithful copy of a row imported from the supplied Excel stock sheets."""
    source_file = models.CharField(max_length=255)
    source_sheet = models.CharField(max_length=120)
    source_row = models.PositiveIntegerField()
    stock_date = models.DateField(null=True, blank=True)
    category = models.CharField(max_length=100, blank=True)
    item_name = models.CharField(max_length=255, blank=True)
    size = models.CharField(max_length=255, blank=True)
    color = models.CharField(max_length=120, blank=True)
    thickness = models.CharField(max_length=80, blank=True)
    width = models.CharField(max_length=80, blank=True)
    length = models.CharField(max_length=80, blank=True)
    jumbo_rolls = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    minimum_stock = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    unit = models.CharField(max_length=60, blank=True)
    available_stock = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    required_stock = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    remark = models.TextField(blank=True)
    raw_data = models.TextField(default="{}")
    imported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source_file", "source_sheet", "source_row"],
                name="unique_imported_stock_row",
            )
        ]
        ordering = ["category", "item_name", "source_file", "source_row"]


class InventoryBatch(models.Model):
    """A physical stock batch. FIFO always consumes the oldest remaining batch first."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="batches")
    batch_code = models.CharField(max_length=80, unique=True)
    received_date = models.DateField()
    vendor = models.CharField(max_length=160, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    quantity = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    remaining_quantity = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    unit_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["received_date", "id"]


class WarehouseTransaction(models.Model):
    """Simple warehouse movement ledger."""
    TYPES = [
        ("inward", "Inward"),
        ("putaway", "Putaway"),
        ("pick", "Pick"),
        ("pack", "Pack"),
        ("dispatch", "Dispatch"),
        ("return-receive", "Return Receive"),
    ]
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="warehouse_transactions")
    transaction_type = models.CharField(max_length=30, choices=TYPES)
    quantity = models.DecimalField(max_digits=14, decimal_places=2)
    reference = models.CharField(max_length=100, blank=True)
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class ReturnRecord(models.Model):
    """Returned-product workflow requested by the ERP requirements."""
    STATUS = [
        ("requested", "Return Requested"),
        ("received", "Return Received"),
        ("inspection", "Under Inspection"),
        ("repair", "Repair / Rework"),
        ("replacement", "Replacement"),
        ("redelivery", "Ready for Redelivery"),
        ("closed", "Closed"),
    ]
    MODE = [
        ("repair", "Repair"),
        ("replacement", "Replacement"),
        ("refund", "Refund"),
    ]
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="returns")
    reason = models.TextField()
    # Quantity physically returned; defaults to the full order quantity in the API.
    return_quantity = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    damage_notes = models.TextField(blank=True)
    photos = models.TextField(blank=True, help_text="Optional comma-separated photo paths/URLs.")
    status = models.CharField(max_length=30, choices=STATUS, default="requested")
    # Guards against adding the same returned quantity to inventory more than once.
    return_stock_added = models.BooleanField(default=False)
    replacement_mode = models.CharField(max_length=30, choices=MODE, default="replacement")
    redelivery_status = models.CharField(max_length=40, default="Not scheduled")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Notification(models.Model):
    """Persistent in-app notification for order and stock events."""
    title = models.CharField(max_length=180)
    message = models.TextField()
    kind = models.CharField(max_length=30, default="info")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class BrandSettings(models.Model):
    """Single configurable identity for the ERP's fixed logo component."""
    company_name = models.CharField(max_length=100, default="SEAON")
    tagline = models.CharField(max_length=160, default="Manufacturing & Stock")
    logo_text = models.CharField(max_length=5, default="S")
    logo_color = models.CharField(max_length=7, default="#2563eb")
    logo_style = models.CharField(max_length=20, default="rounded", choices=[("rounded", "Rounded square"), ("circle", "Circle"), ("square", "Square")])
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def current(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
