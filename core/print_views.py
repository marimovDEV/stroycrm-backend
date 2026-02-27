"""
Print Queue API - Chek printerga chiqarish uchun navbat tizimi
Frontend chek ma'lumotlarini yuboradi -> Django navbatga qo'shadi -> Agent (PC) printer orqali chop etadi
"""
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import PrintJob, StoreSettings
from sales.models import Sale


def generate_receipt_data_from_sale(sale):
    """Sale obyektidan printer uchun JSON data generatsiya qiladi"""
    # Do'kon ma'lumotlarini olish
    store, _ = StoreSettings.objects.get_or_create(id=1)
    
    items = []
    for item in sale.items.all():
        items.append({
            'name': item.product.name if item.product else 'Noma\'lum',
            'price': float(item.price),
            'quantity': float(item.quantity),
            'total': float(item.total),
            'unit': item.unit_type
        })
        
    # Agent tushunadigan formatga o'tkazish
    return {
        'shop_name': store.name,
        'address': [store.address] if store.address else [],
        'receipt_header': store.receipt_header,
        'receipt_footer': store.receipt_footer,
        'table': sale.receipt_id,  # receipt_id as table/check_id for reference
        'check_id': sale.receipt_id,
        'date': timezone.localtime(sale.created_at).strftime("%d.%m.%Y") if sale.created_at else timezone.now().strftime("%d.%m.%Y"),
        'time': timezone.localtime(sale.created_at).strftime("%H:%M") if sale.created_at else timezone.now().strftime("%H:%M"),
        'items': items,
        'total_amount': float(sale.total_amount),
        'payment_method': sale.get_payment_method_display(),
        'cashier': sale.cashier.get_full_name() if sale.cashier else 'Noma\'lum',
        'customer': sale.customer.name if sale.customer else None,
        'discount': float(sale.discount_amount),
    }


@api_view(['POST'])
# @permission_classes([IsAuthenticated]) # Hozircha ochiq qoldirish ham mumkin, loyihaga qarab
@permission_classes([AllowAny])
def add_print_job(request):
    """Frontend chek ma'lumotlarini yuboradi yoki sale_id ni beradi"""
    sale_id = request.data.get('sale_id')
    
    if sale_id:
        # Avtomatik generatsiya
        sale = get_object_or_404(Sale, id=sale_id)
        data = generate_receipt_data_from_sale(sale)
        job = PrintJob.objects.create(sale=sale, data=data)
    else:
        # Custom chek ma'lumotlari
        data = request.data
        if not data:
            return Response({'error': 'No data provided'}, status=status.HTTP_400_BAD_REQUEST)
        job = PrintJob.objects.create(data=data)
        
    return Response({'status': 'ok', 'job_id': str(job.id)}, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([AllowAny])
def poll_print_jobs(request):
    """Agent (PC) uchun: yangi vazifa bormi?"""
    # Eng eski pending jobni olish
    job = PrintJob.objects.filter(status='pending').order_by('created_at').first()
    
    if not job:
        return Response({'job': None})

    # Statusni processing ga o'zgartirish
    job.status = 'processing'
    job.save()
    
    # Eskiroq format - agent kutmoqda job dictini
    job_data = {
        'id': str(job.id),
        'data': job.data,
        'created_at': job.created_at.isoformat(),
        'status': job.status
    }
    
    return Response({'job': job_data})


@api_view(['POST'])
@permission_classes([AllowAny])
def ack_print_job(request, job_id):
    """Agent tasdiqlaydi: Chek chiqdi"""
    job = get_object_or_404(PrintJob, id=job_id)
    job.status = 'printed'
    job.printed_at = timezone.now()
    job.save()
    return Response({'status': 'ok'})


@api_view(['POST'])
@permission_classes([AllowAny])
def fail_print_job(request, job_id):
    """Agent xatolik haqida xabar beradi"""
    job = get_object_or_404(PrintJob, id=job_id)
    job.status = 'failed'
    job.error_message = request.data.get('error', 'Unknown error')
    job.save()
    return Response({'status': 'ok'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_print_status(request, job_id):
    """Frontend chek holatini so'raydi"""
    job = get_object_or_404(PrintJob, id=job_id)
    return Response({
        'id': str(job.id),
        'status': job.status,
        'error': job.error_message
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_print_jobs(request):
    """Admin uchun ohirgi print joblar"""
    jobs = PrintJob.objects.all().order_by('-created_at')[:50]
    data = []
    for j in jobs:
        data.append({
            'id': str(j.id),
            'sale_receipt_id': j.sale.receipt_id if j.sale else None,
            'status': j.status,
            'created_at': j.created_at.isoformat(),
            'printed_at': j.printed_at.isoformat() if j.printed_at else None,
            'error_message': j.error_message
        })
    return Response(data)
