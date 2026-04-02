from django.contrib import admin
from .models import PasswordResetToken, ScanHistory


@admin.register(ScanHistory)
class ScanHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'disease_name', 'confidence_percent', 'status', 'created_at']
    search_fields = ['user__username', 'user__email', 'disease_name']
    list_filter = ['status', 'created_at']
    readonly_fields = ['user', 'image', 'disease_name', 'confidence', 'status', 'created_at', 'raw_result']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'token', 'created_at', 'expires_at', 'is_valid']
    search_fields = ['user__username', 'user__email', 'token']
    list_filter = ['created_at', 'expires_at']
    readonly_fields = ['user', 'token', 'created_at', 'expires_at']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
