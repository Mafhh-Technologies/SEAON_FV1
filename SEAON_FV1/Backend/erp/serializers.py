# SERIALIZERS: convert Django database objects to JSON and validate incoming JSON.
from rest_framework import serializers
from .models import *
class UserSerializer(serializers.Serializer):
    id=serializers.IntegerField(source="pk")
    email=serializers.EmailField()
    username=serializers.CharField()
    role=serializers.SerializerMethodField()
    full_name=serializers.SerializerMethodField()
    permissions=serializers.SerializerMethodField()
    def get_role(self,o): return getattr(getattr(o,"profile",None),"role","viewer")
    def get_full_name(self,o): return getattr(getattr(o,"profile",None),"full_name","") or o.username
    def get_permissions(self,o):
        role=getattr(getattr(o,"profile",None),"role","viewer")
        if role=="super-admin": return ["*"]
        return list(PermissionRule.objects.filter(role=role,enabled=True).values_list("code",flat=True))
class ProductSerializer(serializers.ModelSerializer):
    quantity=serializers.SerializerMethodField()
    class Meta: model=Product; fields="__all__"
    def get_quantity(self,o): return getattr(getattr(o,"inventory",None),"quantity",0)
class InventorySerializer(serializers.ModelSerializer):
    product_name=serializers.CharField(source="product.name",read_only=True)
    sku=serializers.CharField(source="product.sku",read_only=True)
    minimum_stock=serializers.DecimalField(source="product.minimum_stock",max_digits=14,decimal_places=2,read_only=True)
    unit=serializers.CharField(source="product.unit",read_only=True)
    location=serializers.CharField(source="product.location",read_only=True)
    class Meta:
        model=Inventory
        fields=["id","product","product_name","sku","quantity","minimum_stock","unit","location","average_cost","updated_at"]
class OrderSerializer(serializers.ModelSerializer):
    # The UI submits multiple recipient addresses as an array; DRF validates each one.
    vendor_emails = serializers.ListField(
        child=serializers.EmailField(), required=False, allow_empty=True
    )
    product_name=serializers.CharField(source="product.name",read_only=True)
    unit=serializers.CharField(source="product.unit",read_only=True)

    def validate(self, attrs):
        """Normalize multiple recipients and preserve compatibility with vendor_email."""
        recipients = attrs.get("vendor_emails") or []
        legacy_recipient = attrs.get("vendor_email", "").strip()
        if legacy_recipient and legacy_recipient not in recipients:
            recipients.insert(0, legacy_recipient)
        # Remove duplicates without changing the order entered by the user.
        recipients = list(dict.fromkeys(email.strip().lower() for email in recipients if email.strip()))
        attrs["vendor_emails"] = recipients
        attrs["vendor_email"] = recipients[0] if recipients else ""
        return attrs

    class Meta:
        model=Order
        fields="__all__"
        read_only_fields=["order_number","created_at","status"]
class ProductionSerializer(serializers.ModelSerializer):
    product_name=serializers.CharField(source="product.name",read_only=True)
    class Meta: model=ProductionOrder; fields="__all__"; read_only_fields=["production_number","started_at","completed_at"]
class BOMSerializer(serializers.ModelSerializer):
    product_name=serializers.CharField(source="product.name",read_only=True)
    component_name=serializers.CharField(source="component_product.name",read_only=True)
    class Meta: model=BOMItem; fields="__all__"


class BatchSerializer(serializers.ModelSerializer):
    product_name=serializers.CharField(source="product.name",read_only=True)
    sku=serializers.CharField(source="product.sku",read_only=True)
    class Meta:
        model=InventoryBatch
        fields="__all__"

class WarehouseSerializer(serializers.ModelSerializer):
    product_name=serializers.CharField(source="product.name",read_only=True)
    class Meta:
        model=WarehouseTransaction
        fields="__all__"

class ReturnSerializer(serializers.ModelSerializer):
    order_number=serializers.CharField(source="order.order_number",read_only=True)
    customer_name=serializers.CharField(source="order.customer_name",read_only=True)
    product_name=serializers.CharField(source="order.product.name",read_only=True)
    class Meta:
        model=ReturnRecord
        fields="__all__"
        read_only_fields=["created_at","updated_at"]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "title", "message", "kind", "is_read", "created_at"]

class BrandSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrandSettings
        fields = ["company_name", "tagline", "logo_text", "logo_color", "logo_style"]
