from pathlib import Path
from django.contrib import admin
from django.http import FileResponse, JsonResponse
from django.urls import include, path
from django.conf import settings
PUBLIC=Path(settings.BASE_DIR)/"public"
TYPES={".html":"text/html",".css":"text/css",".js":"application/javascript",".svg":"image/svg+xml",
 ".png":"image/png",".jpg":"image/jpeg",".jpeg":"image/jpeg",".ico":"image/x-icon"}
def frontend(request,path=""):
    target=PUBLIC/(path or "login.html")
    if not target.exists() or not target.is_file(): target=PUBLIC/"login.html"
    return FileResponse(open(target,"rb"),content_type=TYPES.get(target.suffix.lower(),"application/octet-stream"))
def health(request): return JsonResponse({"ok":True,"service":"SEAON ERP","database":"sqlite"})
urlpatterns=[
 path("admin/",admin.site.urls),path("api/",include("erp.urls")),path("health/",health),
 path("app/",frontend),path("app/<path:path>",frontend),path("",frontend)]
