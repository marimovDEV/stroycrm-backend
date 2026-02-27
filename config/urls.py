from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token
from products.views import ProductViewSet, CategoryViewSet, StockMovementViewSet
from products.barcode_views import barcode_lookup, add_barcode, delete_barcode, product_barcodes
from products.calculator_views import calculate_material, calculate_coverage
from customers.views import CustomerViewSet, DebtTransactionViewSet
from sales.views import SaleViewSet, SaleItemViewSet, DashboardStatsView, ReportsView, AuditLogView
from core.views import EmployeeViewSet, dashboard_stats, sales_report, user_profile, pin_login
from core.reports_views import daily_sales_report, customer_debt_report, low_stock_report
from core.print_views import add_print_job, poll_print_jobs, ack_print_job

router = DefaultRouter()
router.register(r'products', ProductViewSet)
router.register(r'categories', CategoryViewSet)
router.register(r'stock-movements', StockMovementViewSet)
router.register(r'customers', CustomerViewSet)
router.register(r'debt-transactions', DebtTransactionViewSet)
router.register(r'sales', SaleViewSet)
router.register(r'sale-items', SaleItemViewSet)
router.register(r'employees', EmployeeViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    
    # Authentication
    path('api/auth/login/', obtain_auth_token, name='api-token-auth'),
    path('api/login/', pin_login, name='login'),  # Custom PIN login
    path('api/me/', user_profile, name='user-profile'),  # User profile
    
    # Dashboard & Reports
    path('api/dashboard/stats/', DashboardStatsView.as_view(), name='dashboard-stats-view'),
    path('api/dashboard-stats/', dashboard_stats, name='dashboard-stats'),
    path('api/sales-report/', sales_report, name='sales-report'),
    path('api/reports/stats/', ReportsView.as_view(), name='reports-stats'),
    path('api/audit-logs/', AuditLogView.as_view(), name='audit-logs'),
    
    # Barcode Management
    path('api/products/barcode/lookup/', barcode_lookup, name='barcode-lookup'),
    path('api/products/barcode/add/', add_barcode, name='barcode-add'),
    path('api/products/barcode/<int:barcode_id>/', delete_barcode, name='barcode-delete'),
    path('api/products/<int:product_id>/barcodes/', product_barcodes, name='product-barcodes'),
    
    # Material Calculator
    path('api/products/calculator/', calculate_material, name='calculator-material'),
    path('api/products/calculator/coverage/', calculate_coverage, name='calculator-coverage'),
    
    # Reports
    path('api/reports/daily-sales/', daily_sales_report, name='reports-daily-sales'),
    path('api/reports/customer-debt/', customer_debt_report, name='reports-customer-debt'),
    path('api/reports/low-stock/', low_stock_report, name='reports-low-stock'),
    
    # Print Queue (Printer Agent uchun)
    path('api/print/', add_print_job, name='print-add'),
    path('api/print/poll/', poll_print_jobs, name='print-poll'),
    path('api/print/ack/<str:job_id>/', ack_print_job, name='print-ack'),
]
