from rest_framework import viewsets
from .models import Product, StockMovement, Category
from .serializers import ProductSerializer, StockMovementSerializer, CategorySerializer

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
from rest_framework.decorators import action
from rest_framework.response import Response

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    search_fields = ['name', 'sku']
    filterset_fields = ['category']

    @action(detail=False, methods=['get'])
    def stats(self, request):
        queryset = self.get_queryset()
        from django.db.models import Sum, F, Avg
        
        total_products = queryset.count()
        # Calculate total value of stock (stock * sale_price)
        # Note: SQLite might struggle with efficient sums but it's fine for now
        total_value = sum(p.stock * p.sale_price for p in queryset)
        
        low_stock_count = queryset.filter(stock__lte=F('min_stock')).count()
        
        # Avg Margin
        avg_margin = 0
        products_with_price = [p for p in queryset if p.sale_price > 0]
        if products_with_price:
            margins = [((p.sale_price - p.cost_price) / p.sale_price) * 100 for p in products_with_price]
            avg_margin = sum(margins) / len(margins)

        return Response({
            'totalProducts': total_products,
            'totalValue': total_value,
            'lowStockCount': low_stock_count,
            'avgMargin': round(avg_margin, 1)
        })

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Product.objects.none()
        return Product.objects.all()

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        instance = self.get_object()
        old_stock = instance.stock
        new_product = serializer.save()
        new_stock = new_product.stock

        if old_stock != new_stock:
            diff = new_stock - old_stock
            StockMovement.objects.create(
                product=new_product,
                type='in' if diff > 0 else 'out',
                quantity=diff,
                user=self.request.user,
                reason=f"Stock updated manually via Inventory/Product UI (Old: {old_stock}, New: {new_stock})"
            )

class StockMovementViewSet(viewsets.ModelViewSet):
    queryset = StockMovement.objects.all()
    serializer_class = StockMovementSerializer
    filterset_fields = ['type', 'product']

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return StockMovement.objects.none()
        return StockMovement.objects.all().order_by('-date')
