from rest_framework import serializers
from .models import Product, StockMovement, Category, Barcode

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class BarcodeSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')
    created_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Barcode
        fields = '__all__'
    
    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.username
        return None

class ProductSerializer(serializers.ModelSerializer):
    stock_display = serializers.SerializerMethodField()
    is_low_stock = serializers.ReadOnlyField()
    barcodes = BarcodeSerializer(many=True, read_only=True)
    barcode_count = serializers.SerializerMethodField()
    
    # Frontend compatibility mappings
    currentStock = serializers.DecimalField(source='stock', max_digits=15, decimal_places=2, read_only=True)
    unit = serializers.CharField(source='sell_unit', read_only=True)
    sellPrice = serializers.DecimalField(source='sale_price', max_digits=15, decimal_places=2, read_only=True)
    buyPrice = serializers.DecimalField(source='cost_price', max_digits=15, decimal_places=2, read_only=True)
    minStock = serializers.DecimalField(source='min_stock', max_digits=15, decimal_places=2, read_only=True)

    class Meta:
        model = Product
        fields = '__all__'
    
    def get_stock_display(self, obj):
        return obj.get_stock_display()
    
    def get_barcode_count(self, obj):
        return obj.barcodes.count()

class StockMovementSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')
    
    class Meta:
        model = StockMovement
        fields = '__all__'

