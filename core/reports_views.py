from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from datetime import timedelta
from sales.models import Sale, SaleItem
from products.models import Product
from customers.models import Customer
from decimal import Decimal

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def daily_sales_report(request):
    """
    Get today's sales summary
    """
    today = timezone.now().date()
    
    # Today's sales
    today_sales = Sale.objects.filter(
        created_at__date=today
    )
    
    total_amount = today_sales.aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    
    total_count = today_sales.count()
    
    # Payment method breakdown
    cash_sales = today_sales.filter(payment_method='cash').aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    
    card_sales = today_sales.filter(payment_method='card').aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    
    debt_sales = today_sales.filter(payment_method='debt').aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    
    # Top products today
    top_products = SaleItem.objects.filter(
        sale__created_at__date=today
    ).values(
        'product__name'
    ).annotate(
        qty=Sum('quantity'),
        revenue=Sum('total')
    ).order_by('-revenue')[:5]
    
    return Response({
        'date': today.isoformat(),
        'summary': {
            'total_sales': float(total_amount),
            'total_count': total_count,
            'average_sale': float(total_amount / total_count) if total_count > 0 else 0
        },
        'by_payment_method': {
            'cash': float(cash_sales),
            'card': float(card_sales),
            'debt': float(debt_sales)
        },
        'top_products': list(top_products)
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def customer_debt_report(request):
    """
    Get customers with debt summary
    """
    customers_with_debt = Customer.objects.filter(
        debt__gt=0
    ).order_by('-debt')
    
    total_debt = customers_with_debt.aggregate(
        total=Sum('debt')
    )['total'] or 0
    
    # Group by customer type
    debt_by_type = {}
    for cust_type in ['regular', 'usta', 'brigadir', 'firma']:
        debt_by_type[cust_type] = Customer.objects.filter(
            customer_type=cust_type,
            debt__gt=0
        ).aggregate(
            total=Sum('debt'),
            count=Count('id')
        )
    
    # Near limit customers (>80% of limit)
    near_limit = []
    for customer in customers_with_debt:
        if customer.debt_limit and customer.debt_limit > 0:
            usage_percent = (float(customer.debt) / float(customer.debt_limit)) * 100
            if usage_percent >= 80:
                near_limit.append({
                    'id': customer.id,
                    'name': customer.name,
                    'debt': float(customer.debt),
                    'limit': float(customer.debt_limit),
                    'usage_percent': round(usage_percent, 1)
                })
    
    return Response({
        'summary': {
            'total_debt': float(total_debt),
            'total_customers': customers_with_debt.count()
        },
        'by_type': {
            k: {
                'total_debt': float(v['total'] or 0),
                'count': v['count'] or 0
            } for k, v in debt_by_type.items()
        },
        'near_limit_customers': near_limit,
        'top_debtors': [
            {
                'id': c.id,
                'name': c.name,
                'debt': float(c.debt),
                'customer_type': c.customer_type or 'regular'
            }
            for c in customers_with_debt[:10]
        ]
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def low_stock_report(request):
    """
    Get products with low stock
    """
    # Products below minimum
    low_stock = Product.objects.filter(
        stock__lt=F('min_stock')
    ).order_by('stock')
    
    # Critical (below 50% of minimum)
    critical_stock = Product.objects.filter(
        stock__lt=F('min_stock') * 0.5
    )
    
    return Response({
        'summary': {
            'low_stock_count': low_stock.count(),
            'critical_count': critical_stock.count()
        },
        'low_stock_products': [
            {
                'id': p.id,
                'name': p.name,
                'current_stock': float(p.stock),
                'min_stock': float(p.min_stock),
                'shortage': float(p.min_stock - p.stock),
                'base_unit': p.base_unit or 'unit',
                'sell_unit': p.sell_unit
            }
            for p in low_stock
        ],
        'critical_products': [
            {
                'id': p.id,
                'name': p.name,
                'current_stock': float(p.stock),
                'min_stock': float(p.min_stock),
                'base_unit': p.base_unit or 'unit'
            }
            for p in critical_stock
        ]
    })
