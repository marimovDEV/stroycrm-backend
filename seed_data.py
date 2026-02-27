import os
import django
import random
from decimal import Decimal
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from products.models import Product, StockMovement, Barcode
from customers.models import Customer, DebtTransaction
from sales.models import Sale, SaleItem
from core.models import Employee, StoreSettings
from django.utils import timezone

def seed_data():
    print("Starting mature data seeding for single store setup...")

    # 1. Clear existing data
    SaleItem.objects.all().delete()
    Sale.objects.all().delete()
    StockMovement.objects.all().delete()
    DebtTransaction.objects.all().delete()
    Employee.objects.all().delete()
    Customer.objects.all().delete()
    Barcode.objects.all().delete()
    Product.objects.all().delete()
    StoreSettings.objects.all().delete()

    # Create Store Settings
    StoreSettings.objects.create(
        name="Stroy Material Dukoni",
        address="Urganch shahar, Pahlavon Mahmud ko'chasi",
        phone="+998 90 123 45 67",
        receipt_footer="Xaridingiz uchun rahmat!"
    )

    # Create Users & Employees
    admin_user, _ = User.objects.get_or_create(username='admin', defaults={'is_superuser': True, 'is_staff': True})
    if _:
        admin_user.set_password('admin123')
        admin_user.save()
    
    Employee.objects.update_or_create(
        user=admin_user, 
        defaults={'position': 'CEO', 'salary': 10000000, 'role': 'super_admin', 'pin': '1234'}
    )
    
    manager_configs = [
        {'username': 'oybek_sotuvchi', 'pos': 'Sotuvchi/Menejer', 'salary': 5000000, 'role': 'seller', 'pin': '5678'},
    ]
    
    for conf in manager_configs:
        user, created = User.objects.get_or_create(
            username=conf['username'],
            defaults={'email': f"{conf['username']}@example.com"}
        )
        if created:
            user.set_password('pass123')
            user.save()
        
        Employee.objects.update_or_create(
            user=user,
            defaults={
                'position': conf['pos'],
                'salary': conf['salary'],
                'role': conf['role'],
                'phone': '+998991234567',
                'pin': conf['pin']
            }
        )

    # 2. Products
    products_base = [
        {
            'name': 'Sement M-450', 
            'category': 'Sement', 
            'base_unit': 'kg', 
            'sell_unit': 'qop',
            'unit_ratio': 50,
            'cost': 12400,
            'sale': 15000, 
            'stock_init': 5000, 
            'min': 500,
            'short_code': 'C450'
        },
        {
            'name': 'Sement M-500', 
            'category': 'Sement', 
            'base_unit': 'kg', 
            'sell_unit': 'qop',
            'unit_ratio': 50,
            'cost': 17000, 
            'sale': 22000, 
            'stock_init': 4000,
            'min': 500,
            'short_code': 'C500'
        },
        {
            'name': 'Pishgan gisht qizil', 
            'category': 'Gisht', 
            'base_unit': 'dona', 
            'sell_unit': 'dona',
            'unit_ratio': 1,
            'cost': 1100, 
            'sale': 1450, 
            'stock_init': 50000,
            'min': 5000,
            'short_code': 'GRD'
        },
        {
            'name': 'Armatura 12mm', 
            'category': 'Metall', 
            'base_unit': 'm', 
            'sell_unit': 'm',
            'unit_ratio': 1,
            'cost': 8200, 
            'sale': 9800, 
            'stock_init': 5000,
            'min': 500,
            'short_code': 'A12'
        },
        {
            'name': 'Kafel yelimi Knauf', 
            'category': 'Chimdan', 
            'base_unit': 'kg', 
            'sell_unit': 'qop',
            'unit_ratio': 25,
            'cost': 32000, 
            'sale': 45000, 
            'stock_init': 1250, 
            'min': 250,
            'short_code': 'KNF'
        },
    ]

    for idx, p_data in enumerate(products_base, 1):
        product = Product.objects.create(
            name=p_data['name'],
            category=p_data['category'],
            base_unit=p_data['base_unit'],
            sell_unit=p_data['sell_unit'],
            unit_ratio=p_data['unit_ratio'],
            short_code=p_data['short_code'],
            cost_price=p_data['cost'],
            sale_price=p_data['sale'],
            stock=p_data['stock_init'],
            min_stock=p_data['min']
        )
        
        # Barcodes
        Barcode.objects.create(product=product, code=f"590{idx:05d}0001", barcode_type='factory', created_by=admin_user)
        Barcode.objects.create(product=product, code=p_data['short_code'], barcode_type='internal', created_by=admin_user)
        
        # Stock movement
        StockMovement.objects.create(
            product=product,
            type='in',
            quantity=p_data['stock_init'],
            user=admin_user,
            reason="Dastlabki ombor toldirish",
            date=timezone.now() - timedelta(days=90)
        )

    # 3. Customers
    customers_data = [
        {'name': 'Shovot Qurilish MCHJ', 'phone': '+998901112233', 'customer_type': 'firma', 'debt_limit': 50000000},
        {'name': 'Karimov Usta', 'phone': '+998912223344', 'customer_type': 'usta', 'debt_limit': 5000000},
        {'name': 'Rahimov Brigadir', 'phone': '+998933334455', 'customer_type': 'brigadir', 'debt_limit': 15000000},
    ]

    for c_data in customers_data:
        Customer.objects.create(
            name=c_data['name'],
            phone=c_data['phone'],
            customer_type=c_data['customer_type'],
            debt_limit=c_data['debt_limit'],
            debt=0,
            status='active'
        )

    # 4. Sales
    clients = list(Customer.objects.all())
    products = list(Product.objects.all())
    payment_methods = ['cash', 'card', 'transfer', 'debt']
    start_date = timezone.now() - timedelta(days=90)
    
    for i in range(50):
        days_offset = random.randint(0, 90)
        sale_date = start_date + timedelta(days=days_offset)
        client = random.choice(clients)
        
        sale = Sale.objects.create(
            customer=client,
            total_amount=0,
            payment_method=random.choice(payment_methods),
            cashier=admin_user,
            created_at=sale_date
        )
        
        total_amount = 0
        selected_items = random.sample(products, k=random.randint(1, 3))
        for p in selected_items:
            qty = random.randint(1, 10)
            line_total = p.sale_price * qty
            total_amount += line_total
            
            SaleItem.objects.create(
                sale=sale, product=p, quantity=qty, price=p.sale_price,
                cost_price_at_sale=p.cost_price, total=line_total
            )
            StockMovement.objects.create(
                product=p, type='out', quantity=qty, reason=f"Sotuv #{sale.id}", date=sale_date
            )
            p.stock -= qty
            p.save()
            
        sale.total_amount = total_amount
        sale.save()
        
        if sale.payment_method == 'debt':
            client.debt += total_amount
            client.save()
            DebtTransaction.objects.create(
                customer=client, transaction_type='debt_added', amount=total_amount, date=sale_date
            )

    print("Seeding completed successfully for single store setup.")

if __name__ == '__main__':
    seed_data()
