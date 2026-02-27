from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from products.models import Product, Barcode
from products.serializers import BarcodeSerializer, ProductSerializer
from django.db.models import Q


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def barcode_lookup(request):
    """
    Lookup product by barcode (any type)
    POST /api/products/barcode/lookup/
    Body: {"code": "1234567890"}
    """
    code = request.data.get('code', '').strip()
    
    if not code:
        return Response(
            {'error': 'Barcode code is required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Try to find barcode
        barcode = Barcode.objects.select_related('product').get(code=code)
        product = barcode.product
        
        # Check if product has stock
        has_stock = product.stock > 0
        
        return Response({
            'success': True,
            'product': ProductSerializer(product).data,
            'barcode_type': barcode.barcode_type,
            'has_stock': has_stock,
            'voice_message': f"{product.name} topildi" if has_stock else f"{product.name} - zaxira yo'q"
        })
        
    except Barcode.DoesNotExist:
        # Try short_code as fallback
        try:
            product = Product.objects.get(short_code=code)
            return Response({
                'success': True,
                'product': ProductSerializer(product).data,
                'barcode_type': 'short_code',
                'has_stock': product.stock > 0,
                'voice_message': f"{product.name} topildi"
            })
        except Product.DoesNotExist:
            return Response(
                {
                    'success': False,
                    'error': 'Mahsulot topilmadi',
                    'voice_message': 'Mahsulot topilmadi'
                }, 
                status=status.HTTP_404_NOT_FOUND
            )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_barcode(request):
    """
    Add barcode to product
    POST /api/products/barcode/add/
    Body: {"product_id": 1, "code": "1234567890", "barcode_type": "factory"}
    """
    product_id = request.data.get('product_id')
    code = request.data.get('code', '').strip()
    barcode_type = request.data.get('barcode_type', 'internal')
    
    if not product_id or not code:
        return Response(
            {'error': 'Product ID and code are required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return Response(
            {'error': 'Product not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check if barcode already exists
    if Barcode.objects.filter(code=code).exists():
        return Response(
            {'error': 'Bu barcode allaqachon mavjud'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    barcode = Barcode.objects.create(
        product=product,
        code=code,
        barcode_type=barcode_type,
        created_by=request.user
    )
    
    return Response({
        'success': True,
        'barcode': BarcodeSerializer(barcode).data
    }, status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_barcode(request, barcode_id):
    """
    Delete barcode
    DELETE /api/products/barcode/{id}/
    """
    try:
        barcode = Barcode.objects.get(id=barcode_id)
        barcode.delete()
        return Response({'success': True, 'message': 'Barcode deleted'})
    except Barcode.DoesNotExist:
        return Response(
            {'error': 'Barcode not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def product_barcodes(request, product_id):
    """
    Get all barcodes for a product
    GET /api/products/{id}/barcodes/
    """
    try:
        product = Product.objects.get(id=product_id)
        barcodes = product.barcodes.all()
        return Response({
            'success': True,
            'barcodes': BarcodeSerializer(barcodes, many=True).data
        })
    except Product.DoesNotExist:
        return Response(
            {'error': 'Product not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
