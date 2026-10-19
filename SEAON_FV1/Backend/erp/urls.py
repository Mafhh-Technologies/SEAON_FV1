from django.urls import include,path
from rest_framework.routers import DefaultRouter
from .views import *
from .admin_api import summary as admin_summary, users as admin_users, user_detail as admin_user_detail, roles as admin_roles, role_detail as admin_role_detail, permissions as admin_permissions, audit_logs as admin_audit, stock_rows as admin_stock, reimport as admin_reimport
r=DefaultRouter()
r.register("products",ProductViewSet,basename="products")
r.register("inventory",InventoryViewSet,basename="inventory")
r.register("orders",OrderViewSet,basename="orders")
r.register("production",ProductionViewSet,basename="production")
r.register("bom",BOMViewSet,basename="bom")
urlpatterns=[
 path("admin/summary/",admin_summary),path("admin/users/",admin_users),path("admin/users/<int:pk>/",admin_user_detail),
 path("admin/roles/",admin_roles),path("admin/roles/<int:pk>/",admin_role_detail),path("admin/permissions/",admin_permissions),
 path("admin/audit/",admin_audit),path("admin/stock/",admin_stock),path("admin/reimport/",admin_reimport),
 path("auth/login/",login),path("auth/refresh/",refresh),path("auth/logout/",logout),path("auth/me/",me),
 path("health/",health),path("dashboard/",dashboard),path("notifications/",notifications),path("branding/",branding),path("inventory/batches/",batches),path("inventory/fifo/consume/",fifo_consume),path("warehouse/",warehouse),path("returns/",returns),path("returns/<int:pk>/",returns),path("reports/",reports),path("",include(r.urls))]
