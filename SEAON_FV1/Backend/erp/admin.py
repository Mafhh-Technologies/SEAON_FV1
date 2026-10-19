# Django's built-in technical admin is also available at /admin/.
from django.contrib import admin
from .models import *

admin.site.register([
    UserProfile, Product, Inventory, StockMovement, Order, ProductionOrder,
    BOMItem, RefreshToken, PermissionRule, RoleDefinition, AuditLog,
    StockRecord, InventoryBatch, WarehouseTransaction, ReturnRecord,
])

from .models import Notification, BrandSettings
admin.site.register(Notification)
admin.site.register(BrandSettings)
