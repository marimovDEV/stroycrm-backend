from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from products.models import Product
from customers.models import Customer
from sales.models import Sale

class StroyMarketTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # Authenticate
        from django.contrib.auth.models import User
        self.user = User.objects.create_user(username='testadmin', password='password')
        self.client.force_authenticate(user=self.user)
        
        # Create Product
        self.product = Product.objects.create(
            name='Sement',
            category='Construction',
            cost_price=30000,
            sale_price=40000,
            stock=100
        )
        
        # Create Customer
        self.customer = Customer.objects.create(
            name='Ali Valiyev',
            phone='+998901234567'
        )

    def test_create_product(self):
        data = {
            'name': 'Gisht',
            'category': 'Construction',
            'cost_price': 1000,
            'sale_price': 1500,
            'stock': 5000,
            'base_unit': 'dona',
            'sell_unit': 'dona'
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
        sale_id = response.data['id']
        
        # Confirm payment
        confirm_resp = self.client.post(f'/api/sales/{sale_id}/confirm-payment/', {'payment_method': 'cash'}, format='json')
        self.assertEqual(confirm_resp.status_code, status.HTTP_200_OK)
        
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
        sale_id = response.data['id']
        
        # Confirm payment
        confirm_resp = self.client.post(f'/api/sales/{sale_id}/confirm-payment/', {'payment_method': 'debt'}, format='json')
        self.assertEqual(confirm_resp.status_code, status.HTTP_200_OK)
        
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

class PrintApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        # Create dependencies for auto-generation test
        from products.models import Product
        from customers.models import Customer
        from django.contrib.auth.models import User
        
        self.user = User.objects.create_user(username='testcashier', password='password')
        self.product = Product.objects.create(name='Sement', cost_price=30000, sale_price=40000, stock=100)
        self.customer = Customer.objects.create(name='Test Customer')
        self.sale = Sale.objects.create(
            customer=self.customer, total_amount=40000, cashier=self.user, payment_method='cash'
        )
        self.sale.items.create(product=self.product, quantity=1, price=40000, total=40000)

    def test_add_print_job_manual(self):
        """Test sending manual receipt data"""
        data = {
            'shop_name': 'My Shop',
            'items': [{'name': 'Test', 'quantity': 1, 'price': 100, 'total': 100}],
            'total_amount': 100
        }
        response = self.client.post('/api/print/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('job_id', response.data)
        
        from core.models import PrintJob
        job = PrintJob.objects.get(id=response.data['job_id'])
        self.assertEqual(job.status, 'pending')
        self.assertEqual(job.data['shop_name'], 'My Shop')

    def test_add_print_job_from_sale(self):
        """Test auto-generating receipt data from an existing Sale"""
        response = self.client.post('/api/print/', {'sale_id': self.sale.id}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        from core.models import PrintJob
        job = PrintJob.objects.get(id=response.data['job_id'])
        self.assertEqual(job.status, 'pending')
        self.assertEqual(job.sale, self.sale)
        self.assertTrue(len(job.data['items']) > 0)
        self.assertEqual(job.data['items'][0]['name'], 'Sement')

    def test_poll_print_jobs(self):
        """Test agent polling for pending jobs"""
        from core.models import PrintJob
        job1 = PrintJob.objects.create(data={'test': 1})
        
        response = self.client.get('/api/print/poll/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data.get('job'))
        self.assertEqual(response.data['job']['id'], str(job1.id))
        
        job1.refresh_from_db()
        self.assertEqual(job1.status, 'processing')
        
        # Second poll should return None if no other pending jobs
        response = self.client.get('/api/print/poll/')
        self.assertIsNone(response.data.get('job'))

    def test_ack_print_job(self):
        """Test agent acknowledging successful print"""
        from core.models import PrintJob
        job = PrintJob.objects.create(status='processing', data={})
        
        response = self.client.post(f'/api/print/ack/{job.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        job.refresh_from_db()
        self.assertEqual(job.status, 'printed')
        self.assertIsNotNone(job.printed_at)

    def test_fail_print_job(self):
        """Test agent reporting print failure"""
        from core.models import PrintJob
        job = PrintJob.objects.create(status='processing', data={})
        
        response = self.client.post(f'/api/print/fail/{job.id}/', {'error': 'Paper out'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        job.refresh_from_db()
        self.assertEqual(job.status, 'failed')
        self.assertEqual(job.error_message, 'Paper out')

    def test_print_status(self):
        """Test checking status of a specific job"""
        from core.models import PrintJob
        job = PrintJob.objects.create(status='failed', error_message='Test error', data={})
        
        # Need auth for this endpoint
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'/api/print/status/{job.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'failed')
        self.assertEqual(response.data['error'], 'Test error')
