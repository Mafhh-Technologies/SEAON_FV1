import jwt
from datetime import timedelta
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
SECRET=settings.SECRET_KEY
def access_token(user):
    return jwt.encode({"sub":str(user.pk),"type":"access","exp":timezone.now()+timedelta(hours=8)},SECRET,algorithm="HS256")
class JWTAuthentication(BaseAuthentication):
    def authenticate(self,request):
        header=request.headers.get("Authorization","")
        if not header.startswith("Bearer "): return None
        try:
            data=jwt.decode(header[7:].strip(),SECRET,algorithms=["HS256"])
            if data.get("type")!="access": raise AuthenticationFailed("Invalid token")
            user=User.objects.get(pk=int(data["sub"]))
            if not user.is_active: raise AuthenticationFailed("User disabled")
            return user,header[7:].strip()
        except (jwt.PyJWTError,User.DoesNotExist,KeyError):
            raise AuthenticationFailed("Invalid or expired token")
