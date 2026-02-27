from django.db import models
from customers.models import Customer
from products.models import Product
from django.conf import settings
import random

class Sale(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Naqd'),
        ('card', 'Karta'),
        ('transfer', 'O\'tkazma'),
        ('debt', 'Qarz'),
        ('mixed', 'Aralash'),
        ('truck_sale', 'Mashina sotuvi'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Kutilmoqda'),
        ('completed', 'Yakunlandi'),
        ('cancelled', 'Bekor qilindi'),
    ]

    receipt_id = models.CharField(max_length=50, unique=True, null=True) # E.g., SALE-2025-001
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name='purchases')
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='cash')
    
    # Debt sale specific
    is_debt_sale = models.BooleanField(default=False)
    debt_signature_required = models.BooleanField(default=False)
    
    # Transaction tracking
    keyboard_shortcut_used = models.CharField(max_length=10, blank=True, null=True, 
                                             help_text="F8, F9, etc.")
    scanner_used = models.BooleanField(default=False)
    
    # Staff involvement
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='sales_created')
    cashier = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='sales_confirmed')
    
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.created_at:
            from django.utils import timezone
            self.created_at = timezone.now()
        
        # Auto-set debt sale flag
        if self.payment_method == 'debt':
            self.is_debt_sale = True
            self.debt_signature_required = True
            
        is_new = self.id is None
        if is_new:
            # First save to get the ID
            super().save(*args, **kwargs)
            # Then set receipt_id to the ID
            self.receipt_id = str(self.id)
            type(self).objects.filter(pk=self.pk).update(receipt_id=self.receipt_id)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return f"Sale {self.id} - {self.total_amount}"

class SaleItem(models.Model):
    UNIT_TYPE_CHOICES = [
        ('base', 'Base Unit'),
        ('sell', 'Sell Unit'),
    ]
    
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    
    # Quantity and unit tracking
    quantity = models.DecimalField(max_digits=15, decimal_places=2)
    unit_type = models.CharField(max_length=10, choices=UNIT_TYPE_CHOICES, default='sell')
    unit_ratio_at_sale = models.DecimalField(max_digits=10, decimal_places=3, default=1,
                                             help_text="Conversion ratio at time of sale")
    base_unit_quantity = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                             help_text="Auto-calculated quantity in base unit")
    
    # Price tracking
    price = models.DecimalField(max_digits=15, decimal_places=2) # Price at the moment of sale
    cost_price_at_sale = models.DecimalField(max_digits=15, decimal_places=2, default=0) # For accurate profit audit
    total = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Package tracking
    from_opened_package = models.BooleanField(default=False,
                                              help_text="Ochilgan qop/rulondan sotilganmi")

    def save(self, *args, **kwargs):
        # Auto-calculate base unit quantity
        if self.unit_type == 'sell':
            self.base_unit_quantity = self.quantity * self.unit_ratio_at_sale
        else:
            self.base_unit_quantity = self.quantity
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} x {self.quantity} {self.unit_type}"

