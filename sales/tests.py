from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from products.models import Product, Category
from sales.models import Sale
from customers.models import Customer
from decimal import Decimal

User = get_user_model()

class SaleValidationTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='admin', password='password')
        from core.models import Employee
        Employee.objects.create(user=self.user, position='Manager', role='branch_admin')
        self.client.force_authenticate(user=self.user)
        self.category = Category.objects.create(name='Test Category')
        self.product = Product.objects.create(
            name='Test Product',
            category='Test Category',
            sale_price=10000,
            cost_price=8000,
            stock=100,
            base_unit='dona',
            sell_unit='dona'
        )

    def test_confirm_debt_sale_without_customer_fails(self):
        """Test that confirming a debt sale without a customer returns an error."""
        # Create a pending sale without a customer
        sale = Sale.objects.create(
            total_amount=10000,
            status='pending',
            payment_method='cash', # initially cash
            seller=self.user
        )
        
        url = reverse('sale-confirm-payment', args=[sale.id])
        data = {'payment_method': 'debt'} # try to confirm as debt
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Qarzga sotish uchun mijoz tanlangan bo\'lishi majburiy.')

    def test_confirm_debt_sale_with_customer_succeeds(self):
        """Test that confirming a debt sale with a customer succeeds."""
        customer = Customer.objects.create(name='Test Customer', phone='1234567')
        sale = Sale.objects.create(
            total_amount=10000,
            status='pending',
            payment_method='cash',
            seller=self.user,
            customer=customer
        )
        
        url = reverse('sale-confirm-payment', args=[sale.id])
        data = {'payment_method': 'debt'}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        sale.refresh_from_db()
        self.assertEqual(sale.status, 'completed')
        self.assertEqual(sale.payment_method, 'debt')
