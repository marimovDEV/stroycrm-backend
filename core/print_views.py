"""
Print Queue API - Chek printerga chiqarish uchun navbat tizimi
Frontend chek ma'lumotlarini yuboradi -> Django navbatga qo'shadi -> Agent (PC) printer orqali chop etadi
"""
import uuid
from datetime import datetime
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status

# Xotirada saqlash (oddiy yechim)
print_jobs = []


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_print_job(request):
    """Frontend chek ma'lumotlarini yuboradi"""
    data = request.data
    job = {
        'id': str(uuid.uuid4()),
        'data': data,
        'created_at': datetime.now().isoformat(),
        'status': 'pending'
    }
    print_jobs.append(job)
    return Response({'status': 'ok', 'job_id': job['id']}, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([AllowAny])
def poll_print_jobs(request):
    """Agent (PC) uchun: yangi vazifa bormi?"""
    pending = [j for j in print_jobs if j['status'] == 'pending']
    if not pending:
        return Response({'job': None})

    job = pending[0]
    job['status'] = 'processing'
    return Response({'job': job})


@api_view(['POST'])
@permission_classes([AllowAny])
def ack_print_job(request, job_id):
    """Agent tasdiqlaydi: Chek chiqdi"""
    global print_jobs
    print_jobs = [j for j in print_jobs if j['id'] != job_id]
    return Response({'status': 'ok'})
