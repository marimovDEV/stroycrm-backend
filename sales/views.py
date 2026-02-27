from rest_framework import viewsets, views, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Sum, Count, F, Q
from django.utils import timezone
from datetime import timedelta
import django_filters
from .models import Sale, SaleItem
from .serializers import SaleSerializer, SaleItemSerializer

class SaleFilter(django_filters.FilterSet):
    min_date = django_filters.DateTimeFilter(field_name="created_at", lookup_expr='gte')
    max_date = django_filters.DateTimeFilter(field_name="created_at", lookup_expr='lte')
    payment_method = django_filters.CharFilter(field_name="payment_method")
    
    class Meta:
        model = Sale
        fields = ['status', 'payment_method', 'min_date', 'max_date']

class SaleViewSet(viewsets.ModelViewSet):
    queryset = Sale.objects.all()
    serializer_class = SaleSerializer
    filterset_class = SaleFilter
    search_fields = ['receipt_id', 'customer__name']

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Sale.objects.none()
        
        status_filter = self.request.query_params.get('status')
        qs = Sale.objects.all().order_by('-created_at')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    def perform_create(self, serializer):
        serializer.save(seller=self.request.user)

    @action(detail=True, methods=['post'], url_path='confirm-payment')
    def confirm_payment(self, request, pk=None):
        """Confirm a pending sale, record payment, and update stock/debt."""
        sale = self.get_object()
        if sale.status != 'pending':
            return Response({'error': 'Faqat kutilayotgan buyurtmalarni tasdiqlash mumkin.'}, status=status.HTTP_400_BAD_REQUEST)
        
        payment_method = request.data.get('payment_method')
        if not payment_method:
            return Response({'error': 'To\'lov turi talab qilinadi.'}, status=status.HTTP_400_BAD_REQUEST)
        
        if payment_method == 'debt' and not sale.customer:
            return Response({'error': 'Qarzga sotish uchun mijoz tanlangan bo\'lishi majburiy.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Update Sale
        sale.status = 'completed'
        sale.payment_method = payment_method
        sale.cashier = request.user
        sale.save()

        # Business Logic: Update Debt (Stock already deducted on creation)
        from core.models import AuditLog
        from decimal import Decimal

        # Customer Debt
        if sale.payment_method == 'debt' and sale.customer:
            from customers.models import DebtTransaction
            DebtTransaction.objects.create(
                customer=sale.customer,
                transaction_type='debt_added',
                amount=sale.total_amount,
                note=f"Sotuv tasdiqlandi: {sale.receipt_id}",
                sale_id=sale.receipt_id
            )
            sale.customer.debt += Decimal(str(sale.total_amount))
            sale.customer.save()

        # Audit Log
        AuditLog.objects.create(
            user=request.user,
            action_type='sale_confirmed',
            description=f"Savdo tasdiqlandi: {sale.receipt_id} ({sale.total_amount} so'm)",
            metadata={'receipt_id': sale.receipt_id, 'amount': float(sale.total_amount)}
        )

        return Response(SaleSerializer(sale).data)

    @action(detail=True, methods=['post'], url_path='cancel-order')
    def cancel_order(self, request, pk=None):
        """Cancel a pending order."""
        sale = self.get_object()
        if sale.status != 'pending':
            return Response({'error': 'Faqat kutilayotgan buyurtmalarni bekor qilish mumkin.'}, status=status.HTTP_400_BAD_REQUEST)
        
        sale.status = 'cancelled'
        sale.save()

        # Return stock
        from products.models import StockMovement
        for item in sale.items.all():
            if item.product:
                # Stock Movement (Return)
                StockMovement.objects.create(
                    product=item.product,
                    type='in',
                    quantity=item.quantity,
                    user=request.user,
                    doc_number=sale.receipt_id,
                    reason=f"Buyurtma bekor qilindi (Skladga qaytish): {sale.receipt_id}"
                )
                # Add back Stock
                item.product.stock += item.quantity
                item.product.save()

        return Response({'status': 'Buyurtma bekor qilindi va mahsulotlar skladga qaytarildi.'})

class SaleItemViewSet(viewsets.ModelViewSet):
    queryset = SaleItem.objects.all()
    serializer_class = SaleItemSerializer
    filterset_fields = ['sale', 'product']

class DashboardStatsView(views.APIView):
    def get(self, request):
        today = timezone.now().date()
        start_of_today = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
        
        # Base Querysets
        sales_qs = Sale.objects.all()
        from products.models import Product
        products_qs = Product.objects.all()
        from customers.models import Customer
        customers_qs = Customer.objects.all()

        # Today's Sales
        today_sales = sales_qs.filter(created_at__gte=start_of_today, status='completed')
        today_total = today_sales.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        
        # Optimized profit calculation
        from django.db.models import ExpressionWrapper, DecimalField
        today_items = SaleItem.objects.filter(sale__in=today_sales)
        today_profit = today_items.annotate(
            profit=ExpressionWrapper(
                (F('price') - F('cost_price_at_sale')) * F('quantity'),
                output_field=DecimalField()
            )
        ).aggregate(total_profit=Sum('profit'))['total_profit'] or 0

        # Inventory Value (Selling Price based)
        inventory_value = products_qs.annotate(
            value=ExpressionWrapper(
                F('stock') * (F('sale_price') / F('unit_ratio')),
                output_field=DecimalField()
            )
        ).aggregate(total_val=Sum('value'))['total_val'] or 0

        # Category Breakdown
        category_breakdown = products_qs.values('category').annotate(
            value=Sum('stock')
        ).order_by('-value')

        total_debt = customers_qs.aggregate(Sum('debt'))['debt__sum'] or 0

        low_stock = products_qs.filter(stock__lte=F('min_stock')).values(
            'id', 'name', 'stock', 'base_unit', 'min_stock'
        ).order_by('stock')[:5]

        # Top Products (Last 30 days for better visibility)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        top_items = SaleItem.objects.filter(
            sale__created_at__gte=thirty_days_ago, 
            sale__status='completed'
        )
        top_products = top_items.values('product__name').annotate(
            quantity=Sum('quantity')
        ).order_by('-quantity')[:5]

        chart_data = []
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            day_start = timezone.make_aware(timezone.datetime.combine(day, timezone.datetime.min.time()))
            day_end = timezone.make_aware(timezone.datetime.combine(day, timezone.datetime.max.time()))
            
            day_sales = sales_qs.filter(created_at__range=(day_start, day_end), status='completed')
            day_total = day_sales.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            
            chart_data.append({
                'name': day.strftime('%d.%m'),
                'total': float(day_total)
            })

        data = {
            'today_sales': float(today_total),
            'today_profit': float(today_profit),
            'total_debt': float(total_debt),
            'inventory_value': float(inventory_value),
            'category_breakdown': list(category_breakdown),
            'low_stock_products': list(low_stock),
            'top_products': list(top_products),
            'chart_data': chart_data
        }
        return Response(data)

class ReportsView(views.APIView):
    def get(self, request):
        # Filters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        cashier_id = request.query_params.get('cashier_id')

        sales_qs = Sale.objects.all()

        if start_date:
            sales_qs = sales_qs.filter(created_at__gte=start_date)
        if end_date:
            sales_qs = sales_qs.filter(created_at__lte=end_date)
        if cashier_id:
            sales_qs = sales_qs.filter(cashier_id=cashier_id)

        # Aggregations
        total_sales = sales_qs.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        sale_count = sales_qs.count()
        avg_check = float(total_sales) / sale_count if sale_count > 0 else 0

        # Profit calculation
        profit = 0
        items_qs = SaleItem.objects.filter(sale__in=sales_qs)
        for item in items_qs:
            profit += (item.price - item.cost_price_at_sale) * item.quantity
        
        margin = (float(profit) / float(total_sales) * 100) if total_sales > 0 else 0

        # Profit-based Product Stats
        from django.db.models import ExpressionWrapper, DecimalField
        profitable_products = items_qs.annotate(
            item_profit=ExpressionWrapper(
                (F('price') - F('cost_price_at_sale')) * F('quantity'),
                output_field=DecimalField()
            )
        ).values('product__name').annotate(
            total_profit=Sum('item_profit'),
            qty=Sum('quantity'),
            total_sales=Sum('total')
        ).order_by('-total_profit')[:10]

        # Payment Methods Breakdown
        payment_stats = sales_qs.exclude(payment_method='transfer').values('payment_method').annotate(
            total=Sum('total_amount'),
            count=Count('id')
        ).order_by('-total')

        # Chart Data
        chart_data = []
        now = timezone.now()
        for i in range(14, -1, -1):
            day = now.date() - timedelta(days=i)
            day_start = timezone.make_aware(timezone.datetime.combine(day, timezone.datetime.min.time()))
            day_end = timezone.make_aware(timezone.datetime.combine(day, timezone.datetime.max.time()))
            
            day_sales_qs = sales_qs.filter(created_at__range=(day_start, day_end))
            day_total = day_sales_qs.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            
            day_profit = 0
            day_items = SaleItem.objects.filter(sale__in=day_sales_qs)
            for item in day_items:
                day_profit += (item.price - item.cost_price_at_sale) * item.quantity
            
            chart_data.append({
                'name': day.strftime('%d.%m'),
                'sales': float(day_total),
                'profit': float(day_profit)
            })

        # Debt Payments
        from customers.models import DebtTransaction
        debt_payments_qs = DebtTransaction.objects.filter(transaction_type='payment')
        if start_date:
            debt_payments_qs = debt_payments_qs.filter(date__gte=start_date)
        if end_date:
            debt_payments_qs = debt_payments_qs.filter(date__lte=end_date)
        
        total_debt_payments = debt_payments_qs.aggregate(Sum('amount'))['amount__sum'] or 0
        recent_debt_payments = debt_payments_qs.values(
            'id', 'customer__name', 'amount', 'date', 'note'
        ).order_by('-date')[:10]

        return Response({
            'overview': {
                'total_sales': float(total_sales),
                'sale_count': sale_count,
                'total_profit': float(profit),
                'margin': round(float(margin), 2),
                'avg_check': round(float(avg_check), 2),
                'total_debt_payments': float(total_debt_payments),
            },
            'profitable_products': list(profitable_products),
            'payment_stats': list(payment_stats),
            'debt_payments': list(recent_debt_payments),
            'chart_data': chart_data
        })

class AuditLogView(views.APIView):
    def get(self, request):
        from core.models import AuditLog
        from core.serializers import AuditLogSerializer
        
        logs = AuditLog.objects.all().order_by('-timestamp')
        
        serializer = AuditLogSerializer(logs[:100], many=True)
        return Response(serializer.data)
