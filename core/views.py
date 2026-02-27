from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Sum, F
from django.utils import timezone
from .models import Employee
from .serializers import EmployeeSerializer

class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    search_fields = ['user__username', 'position']
    filterset_fields = ['role']

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """Simple dashboard stats"""
    from sales.models import Sale
    from products.models import Product
    from customers.models import Customer
    
    today = timezone.now().date()
    start_of_today = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
    
    # No branch filtering
    sales_qs = Sale.objects.all()
    products_qs = Product.objects.all()
    customers_qs = Customer.objects.all()

    today_sales = sales_qs.filter(created_at__gte=start_of_today)
    today_total = today_sales.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    total_debt = customers_qs.aggregate(Sum('debt'))['debt__sum'] or 0
    low_stock = products_qs.filter(stock__lte=F('min_stock')).count()
    
    return Response({
        'today_sales': float(today_total),
        'today_count': today_sales.count(),
        'total_debt': float(total_debt),
        'low_stock_count': low_stock
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sales_report(request):
    """Simple sales report"""
    from sales.models import Sale
    
    sales = Sale.objects.all()
    total = sales.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    return Response({
        'total_sales': float(total),
        'count': sales.count()
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """Get current user's profile information"""
    user = request.user
    role = 'super-admin'
    try:
        employee = user.employee_profile
        ROLE_MAPPING = {
            'super_admin': 'super-admin',
            'branch_admin': 'admin',
            'seller': 'seller',
            'warehouse_keeper': 'omborchi'
        }
        role = ROLE_MAPPING.get(employee.role, 'super-admin')
    except:
        pass
    
    return Response({
        'username': user.username,
        'full_name': f"{user.first_name} {user.last_name}".strip() or user.username,
        'role': role,
        'branch_name': 'Asosiy do\'kon'
    })

from rest_framework.authtoken.models import Token
from rest_framework import status

@api_view(['POST'])
@permission_classes([])
def pin_login(request):
    """Login using PIN code"""
    pin = request.data.get('pin') or request.data.get('username') # Handle 'username' if frontend sends pin in that field
    
    # Debug: Check what frontend sends if pin is missing
    if not pin:
        return Response({'error': 'PIN code required', 'received': request.data}, status=status.HTTP_400_BAD_REQUEST)
        
    ROLE_MAPPING = {
        'super_admin': 'super-admin',
        'branch_admin': 'admin',
        'seller': 'seller',
        'warehouse_keeper': 'omborchi'
    }

    try:
        employee = Employee.objects.get(pin=pin)
        user = employee.user
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.id,
            'role': ROLE_MAPPING.get(employee.role, 'super-admin')
        })
    except Employee.DoesNotExist:
        return Response({'error': 'PIN kod noto\'g\'ri'}, status=status.HTTP_400_BAD_REQUEST)

