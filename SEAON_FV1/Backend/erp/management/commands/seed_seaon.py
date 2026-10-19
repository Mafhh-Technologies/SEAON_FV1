from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from erp.models import *

DEFAULT_ROLES = {
    "super-admin": "Everything in the system",
    "admin": "Day-to-day administration",
    "sales": "Orders, customers and dispatch",
    "production": "Production and work orders",
    "warehouse": "Inventory, warehouse and dispatch",
    "inventory": "Stock, FIFO and inventory reports",
    "accounts": "Management and financial reports",
    "customer-support": "Orders, returns and customer updates",
}

PERMISSIONS = [
    ("products.read","View Products","Products"),("products.write","Manage Products","Products"),
    ("bom.read","View BOM","BOM"),("bom.write","Manage BOM","BOM"),
    ("orders.view","View Orders","Orders"),("orders.create","Create Orders","Orders"),
    ("orders.approve","Approve Orders","Orders"),("orders.dispatch","Dispatch Orders","Orders"),
    ("production.view","View Production","Production"),("production.start","Start Production","Production"),
    ("production.complete","Complete Production","Production"),("inventory.view","View Inventory","Inventory"),
    ("inventory.adjust","Adjust Inventory","Inventory"),("inventory.import","Import Stock","Inventory"),
    ("inventory.fifo","View FIFO","Inventory"),("warehouse.receive","Receive Stock","Warehouse"),
    ("warehouse.pick","Pick Stock","Warehouse"),("warehouse.pack","Pack Stock","Warehouse"),
    ("warehouse.dispatch","Dispatch Stock","Warehouse"),("returns.view","View Returns","Returns"),
    ("returns.manage","Manage Returns","Returns"),("reports.view","View Reports","Reports"),
    ("users.manage","Manage Users","Administration"),("roles.manage","Manage Roles","Administration"),
    ("audit.view","View Audit Logs","Administration"),
]

class Command(BaseCommand):
    help="Create the default SEAON administrator, roles and demo data."

    def handle(self,*args,**kwargs):
        user,_=User.objects.get_or_create(username="admin@seaon.com",defaults={"email":"admin@seaon.com"})
        user.email="admin@seaon.com"; user.set_password("Admin@123"); user.is_staff=True; user.is_superuser=True; user.save()
        profile,_=UserProfile.objects.get_or_create(user=user)
        profile.role="super-admin"; profile.full_name="SEAON Administrator"; profile.save()

        for name,description in DEFAULT_ROLES.items():
            role,_=RoleDefinition.objects.get_or_create(name=name)
            role.description=description
            role.is_system=True
            allowed=[code for code,label,module in PERMISSIONS if name=="super-admin"]
            if name=="admin":
                allowed=[x[0] for x in PERMISSIONS]
            elif name=="sales":
                allowed=[x[0] for x in PERMISSIONS if x[0].startswith(("orders.","returns.","reports."))]
            elif name=="production":
                allowed=[x[0] for x in PERMISSIONS if x[0].startswith("production.") or x[0] in ("inventory.view","inventory.fifo","reports.view")]
            elif name=="warehouse":
                allowed=[x[0] for x in PERMISSIONS if x[0].startswith("warehouse.") or x[0].startswith("inventory.")]
            elif name=="inventory":
                allowed=[x[0] for x in PERMISSIONS if x[0].startswith("inventory.") or x[0]=="reports.view"]
            elif name=="accounts":
                allowed=["reports.view"]
            elif name=="customer-support":
                allowed=[x[0] for x in PERMISSIONS if x[0].startswith(("orders.","returns."))]
            role.permissions_json=__import__("json").dumps(allowed)
            role.save()

            for code,label,module in PERMISSIONS:
                PermissionRule.objects.update_or_create(
                    role=name,code=code,
                    defaults={"label":label,"module":module,"enabled":code in allowed},
                )

        seed=[
            ("Raw Material X","RM-001","raw-material","kg",50,500),
            ("Raw Material Y","RM-002","raw-material","kg",30,120),
            ("Component A","CMP-001","component","pcs",20,250),
            ("Component B","CMP-002","component","pcs",50,45),
            ("Widget A","WID-A","finished","pcs",20,80),
            ("Widget B","WID-B","finished","pcs",20,60),
            ("Widget C","WID-C","finished","pcs",15,30),
        ]
        ps={}
        for n,sku,t,u,m,q in seed:
            x,_=Product.objects.update_or_create(
                sku=sku,defaults={"name":n,"product_type":t,"unit":u,"minimum_stock":m,"location":"Main Store"})
            Inventory.objects.update_or_create(product=x,defaults={"quantity":q})
            InventoryBatch.objects.update_or_create(
                batch_code=f"OPEN-{sku}",
                defaults={"product":x,"received_date":__import__("datetime").date.today(),
                          "quantity":q,"remaining_quantity":q,"vendor":"Opening Stock","unit_cost":0})
            ps[sku]=x
        for a,b,q,u in [
            ("WID-A","RM-001",2,"kg"),("WID-A","CMP-001",4,"pcs"),
            ("WID-B","RM-002",3,"kg"),("WID-B","CMP-002",2,"pcs"),
            ("WID-C","RM-001",1,"kg"),("WID-C","CMP-001",6,"pcs")]:
            BOMItem.objects.update_or_create(
                product=ps[a],component_product=ps[b],
                defaults={"quantity_per_unit":q,"unit":u})
        self.stdout.write(self.style.SUCCESS("SEAON demo account, roles and base data are ready."))
