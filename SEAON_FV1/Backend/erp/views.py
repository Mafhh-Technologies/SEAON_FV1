# API VIEWS: browser requests arrive here, permissions are checked, and services/models are called.
import hashlib,secrets,jwt
from datetime import timedelta
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
from rest_framework import viewsets
from rest_framework.decorators import action,api_view,permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .models import *
from .serializers import *
from .authentication import access_token
from .permissions import RolePermission, user_can
from .services import create_product,adjust_stock,receive_stock,consume_fifo,stock_health,complete_production,order_availability,consume_order_stock,create_order_workflow
from .notifications import notify_vendor_for_order
from django.db import transaction
from rest_framework.exceptions import ValidationError

def record_audit(request, action, module, description):
    AuditLog.objects.create(user=request.user, action=action, module=module, description=description)

def user_data(user): return UserSerializer(user).data

@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    """Authenticate by email/password and issue access/refresh JWTs."""
    email=str(request.data.get("email","")).strip()
    password=str(request.data.get("password",""))
    user=User.objects.filter(email__iexact=email).first()
    if not user or not user.is_active or not authenticate(username=user.username,password=password):
        return Response({"detail":"Invalid email or password."},status=401)

    try:
        refresh=jwt.encode(
            {"sub":str(user.pk),"type":"refresh","exp":timezone.now()+timedelta(days=14)},
            settings.SECRET_KEY,
            algorithm="HS256",
        )
        RefreshToken.objects.create(
            user=user,
            token_hash=hashlib.sha256(refresh.encode()).hexdigest(),
            expires_at=timezone.now()+timedelta(days=14),
        )
        return Response({
            "access":access_token(user),
            "refresh":refresh,
            "user":user_data(user),
        })
    except Exception as exc:
        # Keep API failures JSON so the browser never renders Django's
        # full debug HTML inside the login error box.
        return Response({"detail":f"Login service error: {exc}"},status=500)

@api_view(["POST"])
@permission_classes([AllowAny])
def refresh(request):
    """Issue a fresh short-lived access token from a valid refresh token."""
    raw=request.data.get("refresh","")
    try:
        d=jwt.decode(raw,settings.SECRET_KEY,algorithms=["HS256"])
        if d.get("type")!="refresh": raise ValueError()
        h=hashlib.sha256(raw.encode()).hexdigest()
        rt=RefreshToken.objects.get(token_hash=h,revoked=False,expires_at__gt=timezone.now())
        return Response({"access":access_token(rt.user)})
    except Exception: return Response({"detail":"Invalid or expired refresh token."},status=401)

@api_view(["POST"])
def logout(request):
    """Revoke outstanding refresh tokens for the signed-in user."""
    RefreshToken.objects.filter(user=request.user,revoked=False).update(revoked=True)
    return Response({"ok":True})

@api_view(["GET"])
def me(request): return Response(user_data(request.user))

class ProductViewSet(viewsets.ModelViewSet):
    queryset=Product.objects.all().order_by("name"); serializer_class=ProductSerializer
    def get_permissions(self):
        self.required_permission="products.read" if self.action in ("list","retrieve") else "products.write"; return [RolePermission()]
    def create(self,request,*a,**k):
        data=request.data.copy()
        for key in ("minimum_stock","quantity","thickness"):
            if key in data and data[key]=="": data[key]=0
        try:
            product=create_product(dict(data))
        except Exception as exc:
            return Response({"detail":str(exc)},status=400)
        record_audit(request,"product.created","Products",f"Created {product.name}")
        return Response(ProductSerializer(product).data,status=201)

    def update(self,request,*a,**k):
        response=super().update(request,*a,**k)
        record_audit(request,"product.updated","Inventory",f"Updated product #{k.get('pk')}")
        return response

    def destroy(self,request,*a,**k):
        product=self.get_object()
        if product.orders.exists() or product.production_orders.exists() or product.bom_items.exists() or product.used_in_boms.exists():
            return Response({"detail":"This product is linked to orders, production, or a BOM and cannot be deleted."},status=400)
        name=product.name
        response=super().destroy(request,*a,**k)
        record_audit(request,"product.deleted","Inventory",f"Deleted product {name}")
        return response

class InventoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset=Inventory.objects.select_related("product").order_by("product__name"); serializer_class=InventorySerializer
    required_permission="inventory.view"
    @action(detail=False,methods=["get"])
    def low_stock(self,request):
        rows=[x for x in self.get_queryset() if x.quantity<=x.product.minimum_stock]
        return Response(self.get_serializer(rows,many=True).data)
    @action(detail=False,methods=["patch"],url_path=r"(?P<product_id>[^/.]+)/stock")
    def stock(self,request,product_id=None):
        self.required_permission="inventory.write"
        try:
            inv=adjust_stock(product_id,float(request.data.get("delta",0)),str(request.data.get("note","")))
            record_audit(request,"stock.adjusted","Inventory",f"Adjusted {inv.product.name} by {request.data.get('delta',0)}")
            return Response(InventorySerializer(inv).data)
        except Exception as e: return Response({"detail":str(e)},status=400)

class OrderViewSet(viewsets.ModelViewSet):
    queryset=Order.objects.select_related("product").order_by("-created_at"); serializer_class=OrderSerializer
    def get_permissions(self):
        self.required_permission="orders.view" if self.action in ("list","retrieve","availability") else "orders.write"; return [RolePermission()]

    @action(detail=False,methods=["get"])
    def availability(self,request):
        try:
            product=Product.objects.get(pk=request.query_params.get("product"))
            quantity=Decimal(str(request.query_params.get("quantity", "0")))
            order_type=request.query_params.get("order_type", "manufactured")
            return Response(order_availability(product,quantity,order_type))
        except Product.DoesNotExist:
            return Response({"detail":"Select a valid product."},status=400)
        except Exception as exc:
            return Response({"detail":str(exc)},status=400)

    @transaction.atomic
    def perform_create(self,serializer):
        data=self.request.data
        order_type=str(data.get("order_type", "manufactured"))
        if order_type not in ("manufactured", "readymade"):
            raise ValidationError({"detail":"Order type must be manufactured or readymade."})
        order=serializer.save(order_number=f"ORD-{secrets.token_hex(5).upper()}", status="new-order")
        try:
            availability=create_order_workflow(order)
        except ValidationError:
            raise
        except Exception as exc:
            raise ValidationError({"detail":str(exc)})
        self._notification_results=notify_vendor_for_order(order)
        self._created_order=order
        summary=", ".join(f"{channel}={result['status']}" for channel,result in self._notification_results.items())
        record_audit(self.request,"order.created","Orders",f"Created {order.order_number}; status={order.status}; vendor notifications: {summary}")

    def create(self,request,*args,**kwargs):
        # Preflight outside the atomic create transaction so a blocked order
        # still leaves a persistent in-app notification.
        try:
            product=Product.objects.get(pk=request.data.get("product"))
            quantity=Decimal(str(request.data.get("quantity", "0")))
            order_type=str(request.data.get("order_type", "manufactured"))
            check=order_availability(product,quantity,order_type)
            if not check["available"]:
                Notification.objects.create(title="Order blocked: insufficient stock",message=f"{request.data.get('customer_name','Customer')}: {product.name} x {quantity}. {check['message']}",kind="warning")
                return Response({"detail":check["message"],"availability":check},status=400)
        except Product.DoesNotExist:
            return Response({"detail":"Select a valid product."},status=400)
        except Exception as exc:
            return Response({"detail":str(exc)},status=400)
        response=super().create(request,*args,**kwargs)
        if hasattr(self,"_notification_results"):
            response.data["notifications"]=self._notification_results
        if hasattr(self,"_created_order"):
            response.data["status"]=self._created_order.status
            response.data["production_created"]=self._created_order.order_type=="manufactured"
        return response

    @action(detail=True,methods=["patch"])
    @transaction.atomic
    def transition(self,request,pk=None):
        order=self.get_object()
        new_status=str(request.data.get("status", ""))
        transitions={"new-order":{"packed"},"in-production":set(),"packed":{"dispatched"},"dispatched":set()}
        if new_status not in {"new-order","in-production","packed","dispatched"}:
            return Response({"detail":"Status must be New Order, In Production, Packed, or Dispatched."},status=400)
        if new_status != order.status and new_status not in transitions.get(order.status,set()):
            return Response({"detail":"Invalid order status transition. Complete production before packing, and pack before dispatch."},status=400)
        if new_status=="dispatched" and order.status!="dispatched":
            if order.order_type=="manufactured":
                try: consume_order_stock(order.product,order.quantity,f"Dispatch {order.order_number}")
                except Exception as exc: return Response({"detail":str(exc)},status=400)
            WarehouseTransaction.objects.create(product=order.product,transaction_type="dispatch",quantity=order.quantity,reference=order.order_number,notes="Order dispatched")
        order.status=new_status
        order.save(update_fields=["status"])
        Notification.objects.create(title="Order status updated",message=f"{order.order_number} status changed to {new_status.replace('-', ' ')}.",kind="order")
        record_audit(request,"order.status_changed","Orders",f"{order.order_number} -> {new_status}")
        return Response(self.get_serializer(order).data)

    @action(detail=True,methods=["patch"])
    def complete(self,request,pk=None):
        order=self.get_object()
        if order.order_type=="manufactured":
            job=order.production_jobs.order_by("-started_at").first()
            if job:
                try: complete_production(job)
                except Exception as exc: return Response({"detail":str(exc)},status=400)
                order.refresh_from_db()
            else:
                order.status="packed"; order.save(update_fields=["status"])
        else:
            order.status="packed"; order.save(update_fields=["status"])
        return Response(self.get_serializer(order).data)

class ProductionViewSet(viewsets.ModelViewSet):
    queryset=ProductionOrder.objects.select_related("product").order_by("-started_at"); serializer_class=ProductionSerializer
    def get_permissions(self):
        self.required_permission="production.view" if self.action in ("list","retrieve") else "production.write"; return [RolePermission()]
    def perform_create(self,serializer):
        job=serializer.save(production_number=f"PROD-{secrets.token_hex(5).upper()}")
        record_audit(self.request,"production.created","Production",f"Created {job.production_number}")
    @action(detail=True,methods=["post"])
    def complete(self,request,pk=None):
        try:
            p, allocations=complete_production(self.get_object())
        except Exception as e:
            return Response({"detail":str(e)},status=400)
        record_audit(request,"production.completed","Production",f"Completed {p.production_number}")
        return Response({"production":self.get_serializer(p).data,"fifo_allocations":allocations})

class BOMViewSet(viewsets.ModelViewSet):
    queryset=BOMItem.objects.select_related("product","component_product").order_by("product__name"); serializer_class=BOMSerializer
    def perform_create(self,serializer):
        item=serializer.save()
        record_audit(self.request,"bom.created","BOM",f"Added {item.component_product.name} to {item.product.name}")
    def perform_destroy(self,instance):
        record_audit(self.request,"bom.deleted","BOM",f"Removed {instance.component_product.name} from {instance.product.name}")
        instance.delete()
    def get_permissions(self):
        self.required_permission="bom.read" if self.action in ("list","retrieve") else "bom.write"; return [RolePermission()]

@api_view(["GET","PATCH"])
def notifications(request):
    if request.method=="GET":
        rows=Notification.objects.all()[:200]
        return Response(NotificationSerializer(rows,many=True).data)
    action_name=request.data.get("action")
    if action_name=="read_all": Notification.objects.filter(is_read=False).update(is_read=True)
    elif action_name=="clear_all": Notification.objects.all().delete()
    elif request.data.get("id"): Notification.objects.filter(pk=request.data.get("id")).update(is_read=True)
    return Response({"ok":True})

@api_view(["GET","PATCH"])
def branding(request):
    """Read or update the single shared company/logo branding record."""
    if request.method=="PATCH" and not user_can(request.user,"settings.branding") and getattr(getattr(request.user,"profile",None),"role","") not in ("super-admin","admin"):
        return Response({"detail":"Only an administrator can change branding."},status=403)
    obj=BrandSettings.current()
    if request.method=="PATCH":
        for key in ("company_name","tagline","logo_text","logo_color","logo_style"):
            if key in request.data: setattr(obj,key,str(request.data[key]).strip())
        if not obj.logo_text: obj.logo_text="S"
        if not __import__("re").fullmatch(r"#[0-9A-Fa-f]{6}",obj.logo_color):
            return Response({"detail":"Logo color must be a hex color such as #2563eb."},status=400)
        if obj.logo_style not in ("rounded","circle","square"): return Response({"detail":"Invalid logo style."},status=400)
        obj.save()
        record_audit(request,"branding.updated","Administration",f"Updated logo and company identity for {obj.company_name}")
    return Response(BrandSettingsSerializer(obj).data)

@api_view(["GET"])
def health(request): return Response({"ok":True,"service":"SEAON ERP","database":"sqlite"})


@api_view(["GET"])
def dashboard(request):
    """One small endpoint used by the dashboard cards and charts."""
    from django.db.models import Sum
    orders=Order.objects.all()
    production=ProductionOrder.objects.all()
    inventory=Inventory.objects.select_related("product")
    low=[x for x in inventory if x.quantity <= x.product.minimum_stock]
    return Response({
        "orders_total":orders.count(),
        "orders_pending":orders.filter(status__in=["pending","created","approved","new-order","in-production"]).count(),
        "orders_completed":orders.filter(status="completed").count(),
        "production_active":production.filter(status="in-progress").count(),
        "inventory_items":inventory.count(),
        "low_stock":len(low),
        "stock_units":sum((x.quantity for x in inventory), Decimal("0")),
        "returns_open":ReturnRecord.objects.exclude(status="closed").count(),
        "warehouse_queue":WarehouseTransaction.objects.filter(transaction_type__in=["pick","pack","dispatch"]).count(),
        "fifo_batches":InventoryBatch.objects.filter(remaining_quantity__gt=0).count(),
        "stock_health":stock_health(),
        "recent_orders":Order.objects.select_related("product").order_by("-created_at")[:8].values(
            "id","order_number","customer_name","status","quantity","product__name","created_at"),
    })

@api_view(["GET","POST"])
def batches(request):
    """List FIFO batches or receive stock into a new dated batch."""
    if request.method=="GET":
        if not user_can(request.user,"inventory.fifo"): return Response({"detail":"Permission denied."},status=403)
        return Response(BatchSerializer(InventoryBatch.objects.select_related("product").all()[:1000],many=True).data)
    if not user_can(request.user,"inventory.adjust"): return Response({"detail":"Permission denied."},status=403)
    data=request.data
    try:
        product=Product.objects.get(pk=data.get("product"))
        batch=receive_stock(product,data.get("quantity"),data.get("vendor",""),data.get("batch_code",""),data.get("unit_cost",0),data.get("received_date") or None,data.get("expiry_date") or None,data.get("reference",""))
        record_audit(request,"stock.received","Inventory",f"Received {batch.quantity} {product.unit} of {product.name}")
        return Response(BatchSerializer(batch).data,status=201)
    except Exception as e: return Response({"detail":str(e)},status=400)

@api_view(["POST"])
def fifo_consume(request):
    """Consume a requested quantity from the oldest eligible stock batches."""
    if not user_can(request.user,"inventory.fifo"): return Response({"detail":"Permission denied."},status=403)
    try:
        product=Product.objects.get(pk=request.data.get("product"))
        allocations=consume_fifo(product,request.data.get("quantity"),request.data.get("reference",""))
        record_audit(request,"fifo.consumed","Inventory",f"FIFO consumed {request.data.get('quantity')} {product.unit} of {product.name}")
        return Response({"ok":True,"allocations":allocations})
    except Exception as e: return Response({"detail":str(e)},status=400)

@api_view(["GET", "POST"])
def warehouse(request):
    """List warehouse movements or record a validated stock movement.

    Inward movements increase stock. Pick, putaway, pack and dispatch are
    recorded as workflow events here: order acceptance already consumes stock,
    so a second deduction during picking would incorrectly double-decrement it.
    Returns are restocked by the return-case transition to "received".
    """
    if request.method == "GET":
        if not user_can(request.user, "inventory.view"):
            return Response({"detail": "Permission denied."}, status=403)
        rows = WarehouseTransaction.objects.select_related("product").order_by("-created_at")[:1000]
        return Response(WarehouseSerializer(rows, many=True).data)

    if not user_can(request.user, "warehouse.receive"):
        return Response({"detail": "Permission denied."}, status=403)

    try:
        product = Product.objects.get(pk=request.data.get("product"))
        quantity = Decimal(str(request.data.get("quantity", "0")))
        movement_type = str(request.data.get("transaction_type", "inward"))
        allowed_types = {choice[0] for choice in WarehouseTransaction.TYPES}
        if movement_type not in allowed_types:
            return Response({"detail": "Choose a valid warehouse movement type."}, status=400)
        if quantity <= 0:
            return Response({"detail": "Quantity must be greater than zero."}, status=400)

        reference = str(request.data.get("reference", "")).strip()
        notes = str(request.data.get("notes", "")).strip()

        # Keep stock balances, FIFO batches and the movement ledger in sync.
        with transaction.atomic():
            if movement_type in ("inward", "return-receive"):
                receive_stock(product, quantity, reference=reference)
                # receive_stock writes the inward ledger row. Add a second row
                # only when the event is specifically a returned item.
                if movement_type == "return-receive":
                    WarehouseTransaction.objects.filter(
                        product=product, transaction_type="inward", quantity=quantity,
                        reference=reference
                    ).order_by("-created_at").first().delete()
                    WarehouseTransaction.objects.create(
                        product=product, transaction_type=movement_type,
                        quantity=quantity, reference=reference, notes=notes
                    )
            else:
                # Workflow movements are recorded without another stock change.
                # Stock is consumed when an order is accepted or through the
                # dedicated FIFO consumption action, not again during packing.
                WarehouseTransaction.objects.create(
                    product=product, transaction_type=movement_type,
                    quantity=quantity, reference=reference, notes=notes
                )

            record_audit(request, f"warehouse.{movement_type}", "Warehouse",
                         f"{movement_type.title()} {quantity} {product.unit} of {product.name}")

        return Response({"ok": True, "movement_type": movement_type}, status=201)
    except Product.DoesNotExist:
        return Response({"detail": "Select a valid product."}, status=400)
    except Exception as exc:
        return Response({"detail": str(exc)}, status=400)

@api_view(["GET", "POST", "PATCH"])
def returns(request, pk=None):
    """List returns, create a return case, or advance/edit a return case."""
    if request.method == "GET":
        if not user_can(request.user, "returns.view"):
            return Response({"detail": "Permission denied."}, status=403)
        rows = ReturnRecord.objects.select_related("order", "order__product").order_by("-created_at")
        return Response(ReturnSerializer(rows, many=True).data)

    if not user_can(request.user, "returns.manage"):
        return Response({"detail": "Permission denied."}, status=403)

    if request.method == "POST":
        try:
            order = Order.objects.get(pk=request.data.get("order"))
            return_quantity = Decimal(str(request.data.get("return_quantity") or order.quantity))
            if return_quantity <= 0 or return_quantity > order.quantity:
                return Response({"detail": f"Return quantity must be between 0 and {order.quantity}."}, status=400)
            item = ReturnRecord.objects.create(
                order=order,
                return_quantity=return_quantity,
                reason=request.data.get("reason", ""),
                damage_notes=request.data.get("damage_notes", ""),
                photos=request.data.get("photos", ""),
                replacement_mode=request.data.get("replacement_mode", "replacement"),
            )
            Notification.objects.create(
                title="Return requested",
                message=f"Return #{item.id} was opened for {order.order_number} ({return_quantity} {order.product.unit}).",
                kind="warning",
            )
            record_audit(request, "return.created", "Returns", f"Created return for {order.order_number}")
            return Response(ReturnSerializer(item).data, status=201)
        except Order.DoesNotExist:
            return Response({"detail": "Select a valid order."}, status=400)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=400)

    try:
        item = ReturnRecord.objects.select_related("order", "order__product").get(pk=pk)
    except ReturnRecord.DoesNotExist:
        return Response({"detail": "Return not found."}, status=404)

    allowed_fields = ("status", "damage_notes", "replacement_mode", "redelivery_status")
    previous_status = item.status
    for key in allowed_fields:
        if key in request.data:
            setattr(item, key, request.data[key])

    valid_statuses = {choice[0] for choice in ReturnRecord.STATUS}
    if item.status not in valid_statuses:
        return Response({"detail": "Invalid return status."}, status=400)

    # Restock returned goods once, when the case is marked received. The flag
    # prevents repeated PATCH requests from adding the same quantity twice.
    with transaction.atomic():
        if item.status == "received" and not item.return_stock_added:
            inv, _ = Inventory.objects.select_for_update().get_or_create(
                product=item.order.product, defaults={"quantity": Decimal("0")}
            )
            inv.quantity += item.return_quantity
            inv.save(update_fields=["quantity", "updated_at"])
            StockMovement.objects.create(
                product=item.order.product,
                quantity_change=item.return_quantity,
                quantity_after=inv.quantity,
                movement_type="return-receive",
                note=f"Return #{item.id} / {item.order.order_number}",
            )
            WarehouseTransaction.objects.create(
                product=item.order.product,
                transaction_type="return-receive",
                quantity=item.return_quantity,
                reference=item.order.order_number,
                notes=f"Returned goods received for return #{item.id}",
            )
            item.return_stock_added = True
        item.save()

    if previous_status != item.status:
        Notification.objects.create(
            title="Return status updated",
            message=f"Return #{item.id} for {item.order.order_number} is now {item.get_status_display()}.",
            kind="info",
        )
    record_audit(request, "return.updated", "Returns", f"Updated return #{item.id} to {item.status}")
    return Response(ReturnSerializer(item).data)

@api_view(["GET"])
def reports(request):
    """Return aggregate stock, order, production and returns counts for reports."""
    if not user_can(request.user,"reports.view"): return Response({"detail":"Permission denied."},status=403)
    return Response({
        "stock":stock_health(),
        "orders_by_status":{status:Order.objects.filter(status=status).count() for status in ["new-order","in-production","packed","dispatched","pending","cancelled"]},
        "production_by_status":{status:ProductionOrder.objects.filter(status=status).count() for status in ["in-progress","completed","cancelled"]},
        "returns_by_status":{status:ReturnRecord.objects.filter(status=status).count() for status in ["requested","received","inspection","repair","replacement","redelivery","closed"]},
    })
