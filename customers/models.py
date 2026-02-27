from django.db import models
from decimal import Decimal

class Customer(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('overdue', 'Overdue'),
        ('blocked', 'Blocked'),
        ('blocked_by_debt', 'Blocked by Debt Limit'),
    ]
    
    CUSTOMER_TYPE_CHOICES = [
        ('regular', 'Oddiy mijoz'),
        ('usta', 'Usta'),
        ('brigadir', 'Brigadir'),
        ('firma', 'Firma'),
    ]

    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=50, unique=True)
    address = models.TextField(blank=True, null=True)
    
    # Customer classification
    customer_type = models.CharField(max_length=20, choices=CUSTOMER_TYPE_CHOICES, default='regular')
    
    # Debt management
    debt = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    debt_limit = models.DecimalField(max_digits=15, decimal_places=2, default=0, 
                                     help_text="0 = qarz olish mumkin emas")
    auto_block_on_limit = models.BooleanField(default=True, 
                                              help_text="Limit oshganda avtomatik blok qilish")
    credit_limit = models.DecimalField(max_digits=15, decimal_places=2, default=0)  # Kept for backward compatibility
    
    # Status and tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    notes = models.TextField(blank=True, null=True)
    
    # Purchase tracking
    total_purchases = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    last_purchase_date = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.get_customer_type_display()})"
    
    def can_add_debt(self, amount):
        """Check if customer can take on additional debt"""
        if self.debt_limit == 0:
            return False
        
        potential_debt = self.debt + Decimal(str(amount))
        return potential_debt <= self.debt_limit
    
    def block_customer(self):
        """Block customer due to debt limit"""
        self.status = 'blocked_by_debt'
        self.save()
    
    def unblock_customer(self):
        """Unblock customer"""
        if self.status == 'blocked_by_debt':
            self.status = 'active'
            self.save()
    
    def get_debt_percentage(self):
        """Return debt as percentage of limit"""
        if self.debt_limit == 0:
            return 100 if self.debt > 0 else 0
        return float((self.debt / self.debt_limit) * 100)
    
    def add_debt(self, amount):
        """Add debt and check limit"""
        self.debt += Decimal(str(amount))
        
        if self.auto_block_on_limit and self.debt >= self.debt_limit:
            self.block_customer()
        
        self.save()
    
    def reduce_debt(self, amount):
        """Reduce debt and potentially unblock"""
        self.debt -= Decimal(str(amount))
        
        if self.debt < 0:
            self.debt = 0
        
        # Unblock if debt is now below limit
        if self.status == 'blocked_by_debt' and self.debt < self.debt_limit:
            self.unblock_customer()
        
        self.save()
    
    @property
    def is_blocked(self):
        """Check if customer is blocked"""
        return self.status in ['blocked', 'blocked_by_debt']
    
    @property
    def can_purchase(self):
        """Check if customer can make purchases"""
        return self.status == 'active'

class DebtTransaction(models.Model):
    TYPE_CHOICES = [
        ('debt_added', 'Debt Added'),
        ('payment', 'Payment'),
        ('adjustment', 'Adjustment'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True, null=True)
    
    # Optional link to a sale if the debt was incurred from a sale
    # We will import Sale model lazily or just store ID if strict FK causes circular import
    sale_id = models.CharField(max_length=50, blank=True, null=True) 

    def __str__(self):
        return f"{self.customer.name} - {self.transaction_type} - {self.amount}"

