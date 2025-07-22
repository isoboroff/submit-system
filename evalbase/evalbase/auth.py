from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from .models import UserProfile
from .settings import DEBUG

# a None response could mean:
# 1. no such user, could be a new signup
# 2. no such profile for a real user
# 3. profile unique_id doesn't match the unique_id

class EmailBackend(ModelBackend):
    def authenticate(self, request, email=None, verified=False, unique_id=None):
        if not verified:
            return None
        
        UserModel = get_user_model()
        try:
            user = UserModel.objects.get(email=email)
        except UserModel.DoesNotExist:
            return None
        except UserModel.MultipleObjectsReturned:
            user = UserModel.objects.filter(email=email).first()
        
        try:
            profile = UserProfile.objects.get(user=user)
            if profile.unique_id == '':
                profile.unique_id = unique_id
                profile.save()
            elif not DEBUG and profile.unique_id != unique_id:
                return None
        except UserProfile.DoesNotExist:
            # This is ok, the login cycle will redirect them to make their profile
            pass
        
        # The user has already been authenticated by login.gov, so the email is legit
        return user
