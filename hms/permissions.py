from rest_framework import permissions

class IsDoctor(permissions.BasePermission):
    def has_permission(self, request, view):
        return hasattr(request.user, 'doctor')  # Check if the user is a doctor

class IsPatient(permissions.BasePermission):
    def has_permission(self, request, view):
        return hasattr(request.user, 'patient')  # Check if the user is a patient

class IsDoctorOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return hasattr(request.user, 'doctor')  # Check if the user is a doctor

class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user  # Check if the object belongs to the user
