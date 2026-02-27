from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from .models import Employee, StoreSettings, AuditLog


class EmployeeInline(admin.StackedInline):
    model = Employee
    can_delete = False
    verbose_name_plural = 'Xodim ma\'lumotlari'
    fields = ('role', 'position', 'phone', 'pin', 'salary')
    extra = 0


class CustomUserAdmin(UserAdmin):
    """User + Employee birga ko'rsatish"""
    inlines = (EmployeeInline,)
    list_display = ('username', 'first_name', 'last_name', 'email', 'get_role', 'get_pin', 'is_active')
    list_filter = ('is_active', 'employee_profile__role')
    search_fields = ('username', 'first_name', 'last_name', 'employee_profile__pin')

    def get_role(self, obj):
        try:
            return obj.employee_profile.get_role_display()
        except Exception:
            return '-'
    get_role.short_description = 'Lavozim'

    def get_pin(self, obj):
        try:
            return obj.employee_profile.pin or '-'
        except Exception:
            return '-'
    get_pin.short_description = 'PIN'


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'position', 'pin', 'phone', 'salary', 'created_at')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__first_name', 'pin', 'phone')
    list_editable = ('pin',)  # PIN ni to'g'ridan-to'g'ri ro'yxatdan tahrirlash
    readonly_fields = ('created_at', 'updated_at')
    fields = ('user', 'role', 'position', 'pin', 'phone', 'salary', 'created_at', 'updated_at')

    fieldsets = (
        ('Asosiy', {
            'fields': ('user', 'role', 'position')
        }),
        ('POS Login', {
            'fields': ('pin',),
            'description': '4-10 ta raqamdan iborat PIN. POS tizimiga kirish uchun ishlatiladi.'
        }),
        ('Qo\'shimcha', {
            'fields': ('phone', 'salary')
        }),
        ('Sana', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(StoreSettings)
class StoreSettingsAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'phone')
    fields = ('name', 'address', 'phone', 'receipt_header', 'receipt_footer')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'user', 'description', 'created_at')
    list_filter = ('action',)
    search_fields = ('user__username', 'description')
    readonly_fields = ('action', 'user', 'description', 'created_at')
    ordering = ('-created_at',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# User admin ni o'rniga bizniki
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

admin.site.site_header = "STROY CRM Admin"
admin.site.site_title = "STROY CRM"
admin.site.index_title = "Boshqaruv Paneli"
