from rest_framework.permissions import BasePermission, SAFE_METHODS


class AdminReadOnlyOrUserWrite(BasePermission):

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

       
        if user.is_staff:
            return request.method in SAFE_METHODS

       
        return True

class CategoryPermission(BasePermission):

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):

        # Admin can read/update/delete all categories
        if request.user.is_staff:
            return True

        # Normal users can READ global categories
        if request.method in SAFE_METHODS:
            return obj.owner.is_staff or obj.owner == request.user

        # Normal users can modify only their own categories
        return obj.owner == request.user