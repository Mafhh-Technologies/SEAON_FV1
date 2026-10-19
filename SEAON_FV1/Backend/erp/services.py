# BUSINESS SERVICES: stock changes and other operations live here so views stay simple.
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from .models import Inventory,StockMovement,Product
@transaction.atomic
def create_product(data):
    """Create a product and its one-to-one inventory balance in one transaction."""
    qty=data.pop("quantity",0)
    product=Product.objects.create(**data)
    Inventory.objects.create(product=product,quantity=qty)
    if qty: StockMovement.objects.create(product=product,quantity_change=qty,quantity_after=qty,movement_type="opening")
    return product
@transaction.atomic
def adjust_stock(product_id,delta,note=""):
    """Apply a manual stock delta and record the resulting balance in the ledger."""
    inv=Inventory.objects.select_for_update().get(product_id=product_id)
    new=inv.quantity+delta
    if new<0: raise ValueError("Stock cannot become negative")
    inv.quantity=new; inv.save()
    StockMovement.objects.create(product=inv.product,quantity_change=delta,quantity_after=new,note=note)
    return inv


from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

@transaction.atomic
def receive_stock(product, quantity, vendor="", batch_code="", unit_cost=0, received_date=None, expiry_date=None, reference=""):
    """Receive stock into a new batch and update the live inventory balance."""
    quantity=Decimal(str(quantity))
    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero.")
    received_date=received_date or timezone.localdate()
    batch_code=batch_code or f"BATCH-{timezone.now():%Y%m%d%H%M%S}-{product.id}"
    batch=InventoryBatch.objects.create(
        product=product,batch_code=batch_code,received_date=received_date,
        vendor=vendor,expiry_date=expiry_date,quantity=quantity,
        remaining_quantity=quantity,unit_cost=Decimal(str(unit_cost or 0)))
    inv=Inventory.objects.select_for_update().get(product=product)
    inv.quantity += quantity
    inv.save(update_fields=["quantity","updated_at"])
    StockMovement.objects.create(product=product,quantity_change=quantity,quantity_after=inv.quantity,movement_type="inward",note=reference)
    WarehouseTransaction.objects.create(product=product,transaction_type="inward",quantity=quantity,reference=reference,notes=f"Batch {batch.batch_code}")
    return batch

@transaction.atomic
def consume_fifo(product, quantity, reference=""):
    """Consume the oldest available stock batches first and return the batch allocations."""
    quantity=Decimal(str(quantity))
    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero.")
    inv=Inventory.objects.select_for_update().get(product=product)
    if inv.quantity < quantity:
        raise ValueError(f"Insufficient stock. Available: {inv.quantity}")
    remaining=quantity
    allocations=[]
    batches=InventoryBatch.objects.select_for_update().filter(
        product=product,remaining_quantity__gt=0).order_by("received_date","id")
    for batch in batches:
        if remaining <= 0: break
        used=min(batch.remaining_quantity,remaining)
        batch.remaining_quantity-=used
        batch.save(update_fields=["remaining_quantity"])
        allocations.append({"batch":batch.batch_code,"quantity":str(used),"received_date":str(batch.received_date)})
        remaining-=used
    if remaining>0:
        raise ValueError("FIFO batch records do not contain enough stock.")
    inv.quantity-=quantity
    inv.save(update_fields=["quantity","updated_at"])
    StockMovement.objects.create(product=product,quantity_change=-quantity,quantity_after=inv.quantity,movement_type="fifo-consumption",note=reference)
    WarehouseTransaction.objects.create(product=product,transaction_type="pick",quantity=quantity,reference=reference,notes="FIFO consumption")
    return allocations

def stock_health():
    from .models import Product,Inventory,InventoryBatch
    rows=Inventory.objects.select_related("product")
    low=[x for x in rows if x.quantity <= x.product.minimum_stock]
    dead=[x for x in rows if x.quantity > 0 and not x.product.movements.filter(created_at__gte=timezone.now()-timedelta(days=90)).exists()]
    expiring=InventoryBatch.objects.filter(remaining_quantity__gt=0,expiry_date__isnull=False,expiry_date__lte=timezone.localdate()+timedelta(days=30)).count()
    return {"low_stock":len(low),"dead_stock":len(dead),"near_expiry":expiring}


@transaction.atomic
def complete_production(job):
    """Complete production, consume BOM components by FIFO, then add finished stock."""
    if job.status == "completed":
        return job, []
    allocations=[]
    if not job.materials_reserved:
        for item in job.product.bom_items.select_related("component_product").all():
            required=Decimal(str(job.quantity))*Decimal(str(item.quantity_per_unit))
            allocations.append({
                "component": item.component_product.name,
                "quantity": str(required),
                "batches": consume_order_stock(item.component_product, required, f"Production {job.production_number}")
            })
    job.status="completed"
    job.produced_quantity=job.quantity
    job.completed_at=timezone.now()
    job.save()
    receive_stock(job.product,job.quantity,vendor="Production",batch_code=f"PROD-{job.production_number}",
                  reference=job.production_number)
    if job.order_id:
        job.order.status = "packed"
        job.order.save(update_fields=["status"])
        Notification.objects.create(title="Production completed", message=f"{job.order.order_number} is produced and ready to pack/dispatch.", kind="success")
    return job, allocations


from .models import BOMItem, InventoryBatch, WarehouseTransaction, ProductionOrder, Notification, Order

def order_availability(product, quantity, order_type="manufactured"):
    """Return a live availability breakdown used by the order form and create endpoint."""
    quantity = Decimal(str(quantity))
    if quantity <= 0:
        raise ValueError("Order quantity must be greater than zero.")
    inv = Inventory.objects.filter(product=product).first()
    finished_available = inv.quantity if inv else Decimal("0")
    if order_type == "readymade":
        return {"available": finished_available >= quantity, "order_type": order_type,
                "finished_stock": str(finished_available), "required": str(quantity),
                "unit": product.unit, "materials": [],
                "message": "Finished stock is available." if finished_available >= quantity else f"Insufficient finished stock. Available: {finished_available} {product.unit}."}
    items = list(BOMItem.objects.select_related("component_product").filter(product=product))
    if not items:
        return {"available": False, "order_type": order_type, "finished_stock": str(finished_available),
                "required": str(quantity), "unit": product.unit, "materials": [],
                "message": "No BOM is configured for this product. Add its materials in BOM before creating a manufactured order."}
    materials = []
    enough = True
    for item in items:
        component_inventory = Inventory.objects.filter(product=item.component_product).first()
        available = component_inventory.quantity if component_inventory else Decimal("0")
        required = quantity * item.quantity_per_unit
        sufficient = available >= required
        enough = enough and sufficient
        materials.append({"product": item.component_product_id, "name": item.component_product.name,
                          "required": str(required), "available": str(available),
                          "unit": item.unit or item.component_product.unit, "sufficient": sufficient})
    return {"available": enough, "order_type": order_type, "finished_stock": str(finished_available),
            "required": str(quantity), "unit": product.unit, "materials": materials,
            "message": "All BOM materials are available." if enough else "Insufficient raw material. The order was not created."}

@transaction.atomic
def consume_order_stock(product, quantity, reference):
    """Consume inventory atomically; use FIFO batches when they cover the requested quantity."""
    quantity = Decimal(str(quantity))
    inv = Inventory.objects.select_for_update().get(product=product)
    if inv.quantity < quantity:
        raise ValueError(f"Insufficient stock for {product.name}. Available: {inv.quantity} {product.unit}.")
    batch_total = InventoryBatch.objects.select_for_update().filter(product=product, remaining_quantity__gt=0).aggregate(total=__import__('django.db.models', fromlist=['Sum']).Sum('remaining_quantity'))['total'] or Decimal('0')
    fifo_qty = min(quantity, batch_total)
    if fifo_qty > 0:
        consume_fifo(product, fifo_qty, reference)
    remaining = quantity - fifo_qty
    if remaining > 0:
        inv = Inventory.objects.select_for_update().get(product=product)
        if inv.quantity < remaining:
            raise ValueError(f"Insufficient stock for {product.name}.")
        inv.quantity -= remaining
        inv.save(update_fields=["quantity", "updated_at"])
        StockMovement.objects.create(product=product, quantity_change=-remaining, quantity_after=inv.quantity, movement_type="order-consumption", note=reference)
        WarehouseTransaction.objects.create(product=product, transaction_type="pick", quantity=remaining, reference=reference, notes="Order stock consumption (unbatched stock)")
    return Inventory.objects.get(product=product)

@transaction.atomic
def create_order_workflow(order):
    """Validate, reserve/consume stock, and send manufactured orders to production."""
    availability = order_availability(order.product, order.quantity, order.order_type)
    if not availability["available"]:
        Notification.objects.create(title="Order blocked: insufficient stock", message=f"{order.customer_name}: {order.product.name} x {order.quantity}. {availability['message']}", kind="warning")
        raise ValueError(availability["message"])
    if order.order_type == "readymade":
        consume_order_stock(order.product, order.quantity, f"Order {order.order_number}")
        order.status = "new-order"
        order.save(update_fields=["status"])
    else:
        for item in BOMItem.objects.select_related("component_product").filter(product=order.product):
            required = order.quantity * item.quantity_per_unit
            consume_order_stock(item.component_product, required, f"Order {order.order_number} BOM reservation")
        order.status = "in-production"
        order.save(update_fields=["status"])
        ProductionOrder.objects.create(
            production_number=f"PROD-{order.order_number}", product=order.product,
            customer_name=order.customer_name, quantity=order.quantity, status="in-progress",
            order=order, materials_reserved=True
        )
    Notification.objects.create(title="New order created", message=f"{order.order_number} — {order.product.name} x {order.quantity} for {order.customer_name}. Status: {order.status.replace('-', ' ')}.", kind="order")
    return availability
