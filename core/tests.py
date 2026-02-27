from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from products.models import Product
from customers.models import Customer
from sales.models import Sale

class StroyMarketTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # Create Product
        self.product = Product.objects.create(
            name='Sement',
            sku='SEM-001',
            category='Construction',
            cost_price=30000,
            sale_price=40000,
            stock=100,
            unit='bag',
            branch='toshkent'
        )
        
        # Create Customer
        self.customer = Customer.objects.create(
            name='Ali Valiyev',
            phone='+998901234567',
            branch='toshkent'
        )

    def test_create_product(self):
        data = {
            'name': 'Gisht',
            'sku': 'GIS-001',
            'category': 'Construction',
            'cost_price': 1000,
            'sale_price': 1500,
            'stock': 5000,
            'unit': 'piece',
            'branch': 'toshkent'
        }
        response = self.client.post('/api/products/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Product.objects.count(), 2)

    def test_create_sale_cash(self):
        """Test simple cash sale reduces stock"""
        data = {
            'customer': self.customer.id,
            'total_amount': 80000,
            'payment_method': 'cash',
            'items': [
                {
                    'product': self.product.id,
                    'quantity': 2,
                    'price': 40000,
                    'total': 80000
                }
            ]
        }
        response = self.client.post('/api/sales/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check stock reduction
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 98) # 100 - 2

    def test_create_sale_debt(self):
        """Test debt sale increases customer debt and creates transaction"""
        data = {
            'customer': self.customer.id,
            'total_amount': 40000,
            'payment_method': 'debt',
            'receipt_id': 'SALE-TEST-001',
            'items': [
                {
                    'product': self.product.id,
                    'quantity': 1,
                    'price': 40000,
                    'total': 40000
                }
            ]
        }
        response = self.client.post('/api/sales/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check customer debt
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.debt, 40000)
        
        # Check debt transaction creation
        self.assertEqual(self.customer.transactions.count(), 1)
        transaction = self.customer.transactions.first()
        self.assertEqual(transaction.transaction_type, 'debt_added')
        self.assertEqual(transaction.amount, 40000)

    def test_customer_transactions_endpoint(self):
        # Create a transaction manually
        from customers.models import DebtTransaction
        DebtTransaction.objects.create(
            customer=self.customer,
            transaction_type='payment',
            amount=10000,
            note='Test payment'
        )
        
        response = self.client.get(f'/api/customers/{self.customer.id}/transactions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
