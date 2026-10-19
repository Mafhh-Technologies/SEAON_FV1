from rest_framework.permissions import BasePermission
from .models import PermissionRule

def user_can(user, code):
    if not user or not user.is_authenticated:
        return False
    role = getattr(getattr(user, "profile", None), "role", "viewer")
    if role == "super-admin":
        return True
    return PermissionRule.objects.filter(role=role, code=code, enabled=True).exists()

class RolePermission(BasePermission):
    def has_permission(self, request, view):
        required = getattr(view, "required_permission", None)
        return bool(request.user and request.user.is_authenticated and
                    (not required or user_can(request.user, required)))
