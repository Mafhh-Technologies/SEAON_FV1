# FRIENDLY ADMIN API: endpoints used by public/admin.html. Django's technical /admin is separate.
import json
from django.contrib.auth.models import User
from django.db.models import Count
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .models import AuditLog, PermissionRule, RoleDefinition, StockRecord, UserProfile
from .permissions import user_can

def admin_required(request, code="users.manage"):
    return request.user.is_authenticated and user_can(request.user, code)

def audit(request, action, module, description):
    AuditLog.objects.create(user=request.user, action=action, module=module, description=description)

@api_view(["GET"])
def summary(request):
    if not admin_required(request): return Response({"detail":"Permission denied."}, status=403)
    return Response({
        "users": User.objects.count(),
        "active_users": User.objects.filter(is_active=True).count(),
        "roles": RoleDefinition.objects.count(),
        "stock_rows": StockRecord.objects.count(),
        "audit_events": AuditLog.objects.count(),
    })

@api_view(["GET","POST"])
def users(request):
    if not admin_required(request): return Response({"detail":"Permission denied."}, status=403)
    if request.method == "GET":
        rows=[]
        for u in User.objects.select_related("profile").order_by("username"):
            rows.append({"id":u.id,"email":u.email,"username":u.username,
                         "full_name":getattr(u.profile,"full_name","") if hasattr(u,"profile") else "",
                         "role":getattr(u.profile,"role","viewer") if hasattr(u,"profile") else "viewer",
                         "is_active":u.is_active,"is_staff":u.is_staff})
        return Response(rows)
    data=request.data
    email=str(data.get("email","")).strip().lower()
    password=str(data.get("password",""))
    if not email or not password: return Response({"detail":"Email and password are required."},status=400)
    if User.objects.filter(username=email).exists(): return Response({"detail":"User already exists."},status=400)
    u=User.objects.create_user(username=email,email=email,password=password)
    u.is_staff=bool(data.get("is_staff",False)); u.save()
    UserProfile.objects.create(user=u,role=str(data.get("role","viewer")),full_name=str(data.get("full_name","")))
    audit(request,"user.created","Administration",f"Created user {email}")
    return Response({"id":u.id,"email":u.email,"role":u.profile.role},status=201)

@api_view(["PATCH","DELETE"])
def user_detail(request, pk):
    if not admin_required(request): return Response({"detail":"Permission denied."}, status=403)
    try: u=User.objects.select_related("profile").get(pk=pk)
    except User.DoesNotExist: return Response({"detail":"User not found."},status=404)
    if request.method=="DELETE":
        if u == request.user: return Response({"detail":"You cannot deactivate yourself."},status=400)
        u.is_active=False; u.save(update_fields=["is_active"])
        audit(request,"user.deactivated","Administration",f"Deactivated {u.email}")
        return Response({"ok":True})
    data=request.data
    if "role" in data: u.profile.role=str(data["role"])
    if "full_name" in data: u.profile.full_name=str(data["full_name"])
    if "is_active" in data: u.is_active=bool(data["is_active"])
    if "password" in data and data["password"]: u.set_password(str(data["password"]))
    u.profile.save(); u.save()
    audit(request,"user.updated","Administration",f"Updated {u.email}")
    return Response({"ok":True})

@api_view(["GET","POST"])
def roles(request):
    if not admin_required(request,"roles.manage"): return Response({"detail":"Permission denied."},status=403)
    if request.method=="GET":
        return Response([{"id":r.id,"name":r.name,"description":r.description,
                          "permissions":json.loads(r.permissions_json or "[]"),"is_system":r.is_system}
                         for r in RoleDefinition.objects.order_by("name")])
    name=str(request.data.get("name","")).strip()
    if not name:return Response({"detail":"Role name is required."},status=400)
    perms=request.data.get("permissions",[])
    r=RoleDefinition.objects.create(name=name,description=str(request.data.get("description","")),
                                    permissions_json=json.dumps(perms),is_system=False)
    for rule in PermissionRule.objects.filter(role=name): rule.delete()
    # Copy the known permission labels into this new role.
    for code in perms:
        source=PermissionRule.objects.filter(code=code).first()
        PermissionRule.objects.update_or_create(role=name,code=code,defaults={
            "label":source.label if source else code,"module":source.module if source else "Custom","enabled":True})
    audit(request,"role.created","Administration",f"Created role {name}")
    return Response({"id":r.id,"name":r.name},status=201)

@api_view(["PATCH"])
def role_detail(request, pk):
    if not admin_required(request,"roles.manage"): return Response({"detail":"Permission denied."},status=403)
    try:r=RoleDefinition.objects.get(pk=pk)
    except RoleDefinition.DoesNotExist:return Response({"detail":"Role not found."},status=404)
    if r.is_system and r.name=="super-admin": return Response({"detail":"Super Admin cannot be restricted."},status=400)
    perms=request.data.get("permissions",json.loads(r.permissions_json or "[]"))
    r.description=str(request.data.get("description",r.description)); r.permissions_json=json.dumps(perms); r.save()
    PermissionRule.objects.filter(role=r.name).update(enabled=False)
    for code in perms:
        PermissionRule.objects.filter(role=r.name,code=code).update(enabled=True)
    audit(request,"role.updated","Administration",f"Updated role {r.name}")
    return Response({"ok":True})

@api_view(["GET"])
def permissions(request):
    if not admin_required(request,"roles.manage"): return Response({"detail":"Permission denied."},status=403)
    return Response([{"code":p.code,"label":p.label,"module":p.module} for p in
                     PermissionRule.objects.filter(role="admin").order_by("module","label")])

@api_view(["GET"])
def audit_logs(request):
    if not admin_required(request,"audit.view"): return Response({"detail":"Permission denied."},status=403)
    rows=[]
    for x in AuditLog.objects.select_related("user").order_by("-created_at")[:500]:
        rows.append({"id":x.id,"user":x.user.email if x.user else "System","action":x.action,
                     "module":x.module,"description":x.description,"created_at":x.created_at})
    return Response(rows)

@api_view(["GET"])
def stock_rows(request):
    if not admin_required(request,"inventory.view"): return Response({"detail":"Permission denied."},status=403)
    qs=StockRecord.objects.all()
    category=request.GET.get("category")
    q=request.GET.get("q")
    if category: qs=qs.filter(category__icontains=category)
    if q: qs=qs.filter(item_name__icontains=q)
    return Response([{
        "id":x.id,"category":x.category,"item_name":x.item_name,"size":x.size,"color":x.color,
        "thickness":x.thickness,"width":x.width,"length":x.length,"minimum_stock":x.minimum_stock,
        "unit":x.unit,"available_stock":x.available_stock,"required_stock":x.required_stock,
        "source_file":x.source_file,"source_sheet":x.source_sheet,"source_row":x.source_row,"stock_date":x.stock_date,
        "remark":x.remark
    } for x in qs[:2000]])

@api_view(["POST"])
def reimport(request):
    if not admin_required(request,"inventory.import"): return Response({"detail":"Permission denied."},status=403)
    from django.core.management import call_command
    call_command("import_sample_data")
    audit(request,"stock.imported","Inventory","Re-imported all supplied Excel stock sheets.")
    return Response({"ok":True})
