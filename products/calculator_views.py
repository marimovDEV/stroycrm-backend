from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Product
import math

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def calculate_material(request):
    """
    Calculate how many units needed based on area/volume
    
    POST /api/products/calculator/
    {
        "product_id": 1,
        "measurement_type": "area" | "volume" | "length",
        "value": 100,  // m², m³, or m
        "wastage_percent": 10  // optional, default 10%
    }
    
    Returns:
    {
        "product": {...},
        "input_value": 100,
        "measurement_type": "area",
        "wastage_percent": 10,
        "base_quantity": 110,  // with wastage
        "sell_units": 2.2,  // qop, rulon, etc
        "explanation": "100 m² + 10% wastage = 110 m² ≈ 2.2 qop"
    }
    """
    try:
        product_id = request.data.get('product_id')
        measurement_type = request.data.get('measurement_type', 'area')
        value = float(request.data.get('value', 0))
        wastage_percent = float(request.data.get('wastage_percent', 10))
        
        if not product_id or value <= 0:
            return Response({
                'error': 'product_id va value majburiy'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({
                'error': 'Mahsulot topilmadi'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Calculate with wastage
        value_with_wastage = value * (1 + wastage_percent / 100)
        
        # Calculate base quantity needed
        base_quantity = value_with_wastage
        
        # Calculate sell units
        if product.unit_ratio and product.unit_ratio > 0:
            sell_units = base_quantity / product.unit_ratio
        else:
            sell_units = base_quantity
        
        # Round up to nearest sellable unit
        sell_units_rounded = math.ceil(sell_units * 10) / 10  # round to 1 decimal
        base_quantity_rounded = sell_units_rounded * (product.unit_ratio or 1)
        
        # Create explanation
        explanation = f"{value} {measurement_type}"
        if wastage_percent > 0:
            explanation += f" + {wastage_percent}% wastage = {value_with_wastage:.1f} {product.base_unit or 'birlik'}"
        
        if product.unit_ratio and product.unit_ratio > 0:
            explanation += f" ≈ {sell_units_rounded} {product.sell_unit}"
        
        # Check stock availability
        has_stock = product.stock >= base_quantity_rounded
        stock_shortage = 0 if has_stock else base_quantity_rounded - product.stock
        
        return Response({
            'product': {
                'id': product.id,
                'name': product.name,
                'base_unit': product.base_unit,
                'sell_unit': product.sell_unit,
                'unit_ratio': product.unit_ratio,
                'stock': product.stock,
                'sale_price': product.sale_price
            },
            'input_value': value,
            'measurement_type': measurement_type,
            'wastage_percent': wastage_percent,
            'base_quantity': round(base_quantity_rounded, 2),
            'sell_units': round(sell_units_rounded, 2),
            'explanation': explanation,
            'has_stock': has_stock,
            'stock_shortage': round(stock_shortage, 2) if stock_shortage > 0 else 0,
            'total_price': round(sell_units_rounded * float(product.sale_price), 2)
        })
        
    except ValueError as e:
        return Response({
            'error': 'Noto\'g\'ri qiymat kiritildi'
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def calculate_coverage(request):
    """
    Calculate coverage area/volume for a product
    
    GET /api/products/calculator/coverage/?product_id=1&quantity=5
    
    Returns how much area/volume can be covered with given quantity
    """
    try:
        product_id = request.GET.get('product_id')
        quantity = float(request.GET.get('quantity', 1))
        
        if not product_id:
            return Response({
                'error': 'product_id majburiy'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        product = Product.objects.get(id=product_id)
        
        # Calculate base quantity
        base_quantity = quantity * (product.unit_ratio or 1)
        
        return Response({
            'product_name': product.name,
            'quantity': quantity,
            'unit': product.sell_unit or product.base_unit,
            'base_quantity': base_quantity,
            'base_unit': product.base_unit,
            'explanation': f"{quantity} {product.sell_unit or product.base_unit} = {base_quantity} {product.base_unit}"
        })
        
    except Product.DoesNotExist:
        return Response({
            'error': 'Mahsulot topilmadi'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
