from django.db import models
from django.conf import settings

class StoreSettings(models.Model):
    name = models.CharField(max_length=255, default="Stroy Material Dukoni")
    address = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    receipt_header = models.TextField(blank=True, null=True)
    receipt_footer = models.TextField(blank=True, null=True, default="Rahmat xaridingiz uchun!")

    def __str__(self):
        return self.name

class Employee(models.Model):
    ROLE_CHOICES = [
        ('super_admin', 'Super Admin'),
        ('branch_admin', 'Dukon Admini'),
        ('seller', 'Sotuvchi'),
        ('warehouse_keeper', 'Omborchi'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='employee_profile')
    position = models.CharField(max_length=100)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='seller')
    phone = models.CharField(max_length=20, blank=True, null=True)
    pin = models.CharField(max_length=10, unique=True, null=True, blank=True, help_text="POS login PIN")
    salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.position} ({self.get_role_display()})"

class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('sale', 'Savdo'),
        ('product_add', 'Mahsulot qo\'shildi'),
        ('product_edit', 'Mahsulot o\'zgartirildi'),
        ('price_change', 'Narx o\'zgartirildi'),
        ('stock_move', 'Ombor harakati'),
        ('debt_payment', 'Qarz to\'lovi'),
        ('setting_change', 'Sozlama o\'zgartirildi'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action_type = models.CharField(max_length=20, choices=ACTION_CHOICES)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(null=True, blank=True) # For storing old/new values

    def __str__(self):
        return f"{self.timestamp} - {self.user} - {self.action_type}"
