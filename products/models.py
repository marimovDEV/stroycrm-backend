from django.db import models
from django.conf import settings
from decimal import Decimal

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    
    def __str__(self):
        return self.name

class Product(models.Model):
    # Unit choices for construction materials
    BASE_UNIT_CHOICES = [
        ('kg', 'Kilogram'),
        ('m', 'Metr'),
        ('m2', 'Kvadrat metr'),
        ('m3', 'Kub metr'),
        ('l', 'Litr'),
        ('dona', 'Dona'),
    ]
    
    SELL_UNIT_CHOICES = [
        ('qop', 'Qop'),
        ('rulon', 'Rulon'),
        ('dona', 'Dona'),
        ('m', 'Metr'),
        ('m2', 'Kvadrat metr'),
        ('m3', 'Kub metr'),
        ('kg', 'Kilogram'),
        ('bank', 'Bank'),
        ('korobka', 'Korobka'),
    ]
    
    # Basic info
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    short_code = models.CharField(max_length=20, unique=True, null=True, blank=True)
    
    # Multi-unit system (now flexible strings)
    base_unit = models.CharField(max_length=20, default='dona')
    sell_unit = models.CharField(max_length=20, default='dona')
    unit_ratio = models.DecimalField(max_digits=10, decimal_places=3, default=1, 
                                     help_text="1 sell_unit = ? base_unit (masalan: 1 qop = 25 kg)")
    
    # Pricing (always per sell_unit)
    cost_price = models.DecimalField(max_digits=15, decimal_places=2)
    sale_price = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Stock (always in base_unit)
    stock = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    min_stock = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Opened package tracking
    is_package_opened = models.BooleanField(default=False)
    opened_package_quantity = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                                   help_text="Ochilgan qop/rulondagi qoldiq (base_unit da)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
    def convert_to_base_unit(self, quantity, from_unit='sell'):
        """Convert quantity to base unit"""
        if from_unit == 'sell':
            return Decimal(str(quantity)) * self.unit_ratio
        return Decimal(str(quantity))
    
    def convert_to_sell_unit(self, quantity):
        """Convert base unit quantity to sell unit"""
        if self.unit_ratio == 0:
            return Decimal(0)
        return Decimal(str(quantity)) / self.unit_ratio
    
    def get_all_barcodes(self):
        """Get all barcodes for this product"""
        return self.barcodes.all()
    
    def mark_package_opened(self, remaining_qty):
        """Mark package as opened and track remaining quantity"""
        self.is_package_opened = True
        self.opened_package_quantity = remaining_qty
        self.save()
    
    def close_opened_package(self):
        """Close opened package (when depleted)"""
        self.is_package_opened = False
        self.opened_package_quantity = 0
        self.save()
    
    def get_stock_display(self):
        """Get human-readable stock display"""
        full_packages = int(self.stock // self.unit_ratio)
        remainder = self.stock % self.unit_ratio
        
        if remainder > 0:
            return f"{full_packages} {self.sell_unit} + {remainder} {self.base_unit}"
        return f"{full_packages} {self.sell_unit}"
    
    @property
    def is_low_stock(self):
        """Check if stock is below minimum"""
        return self.stock <= self.min_stock

class Barcode(models.Model):
    """Multi-barcode support for products"""
    BARCODE_TYPE_CHOICES = [
        ('factory', 'Zavod barcode'),
        ('package', 'Qop/Rulon barcode'),
        ('internal', 'Ichki barcode'),
        ('manual', 'Manual kod'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='barcodes')
    code = models.CharField(max_length=100, unique=True, db_index=True)
    barcode_type = models.CharField(max_length=20, choices=BARCODE_TYPE_CHOICES, default='internal')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                                    null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['code']),
        ]
    
    def __str__(self):
        return f"{self.code} ({self.product.name})"

class StockMovement(models.Model):
    MOVEMENT_Types = [
        ('in', 'Kirim'),
        ('out', 'Chiqim'),
        ('transfer', 'Kochirish'),
        ('adjustment', 'Tuzatish'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='movements')
    type = models.CharField(max_length=20, choices=MOVEMENT_Types)
    quantity = models.DecimalField(max_digits=15, decimal_places=2, help_text="Quantity in base_unit")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    # Metadata
    date = models.DateTimeField(auto_now_add=True)
    doc_number = models.CharField(max_length=50, blank=True, null=True)
    batch = models.CharField(max_length=50, blank=True, null=True)
    reason = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.type.upper()} {self.product.name} {self.quantity} {self.product.base_unit}"
