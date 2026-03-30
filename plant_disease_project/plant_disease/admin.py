# Register your models here.
from django.contrib import admin
from .models import UserProfile, ScanHistory
 
 
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display  = ('user', 'phone_number', 'created_at')
    search_fields = ('user__username', 'user__email')
 
 
@admin.register(ScanHistory)
class ScanHistoryAdmin(admin.ModelAdmin):
    list_display    = ('user', 'disease_name', 'confidence_percent', 'status', 'created_at')
    list_filter     = ('status',)
    search_fields   = ('user__username', 'disease_name')
    readonly_fields = ('raw_result',)