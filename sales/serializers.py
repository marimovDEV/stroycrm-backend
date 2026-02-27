from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Sale, SaleItem
from products.models import Product
from customers.models import Customer
from decimal import Decimal

User = get_user_model()

class SaleItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')

    class Meta:
        model = SaleItem
        fields = ['id', 'product', 'product_name', 'quantity', 'price', 'total']

class SaleSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(many=True)
    customer_name = serializers.ReadOnlyField(source='customer.name')
    seller_name = serializers.ReadOnlyField(source='seller.username')
    status = serializers.CharField(read_only=True)

    class Meta:
        model = Sale
        fields = ['id', 'receipt_id', 'status', 'customer', 'customer_name', 'total_amount', 'discount_amount', 'payment_method', 'seller', 'seller_name', 'cashier', 'created_at', 'items']
        read_only_fields = ['receipt_id', 'created_at', 'status']

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        
        if 'seller' not in validated_data and 'request' in self.context:
            validated_data['seller'] = self.context['request'].user

        sale = Sale.objects.create(status='pending', **validated_data)
        
        # Deduct stock immediately on creation
        from products.models import StockMovement
        
        for item_data in items_data:
            product = item_data['product']
            quantity = item_data['quantity']
            
            # Create SaleItem
            SaleItem.objects.create(
                sale=sale, 
                cost_price_at_sale=product.cost_price if product else 0,
                **item_data
            )

            if product:
                # Stock Movement
                StockMovement.objects.create(
                    product=product,
                    type='out',
                    quantity=-quantity,
                    user=validated_data.get('seller'),
                    doc_number=sale.receipt_id,
                    reason=f"Sotuv yaratildi (kutilmoqda): {sale.receipt_id}"
                )
                # Deduct Stock
                product.stock -= quantity
                product.save()

        return sale
