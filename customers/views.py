from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Customer, DebtTransaction
from .serializers import CustomerSerializer, DebtTransactionSerializer

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    search_fields = ['name', 'phone']
    filterset_fields = ['status', 'customer_type']

    def get_queryset(self):
        qs = Customer.objects.all().order_by('-created_at')
        debt_gt = self.request.query_params.get('debt__gt')
        if debt_gt is not None:
            qs = qs.filter(debt__gt=debt_gt)
        return qs

    @action(detail=True, methods=['get'])
    def transactions(self, request, pk=None):
        customer = self.get_object()
        transactions = customer.transactions.all().order_by('-date')
        serializer = DebtTransactionSerializer(transactions, many=True)
        return Response(serializer.data)

class DebtTransactionViewSet(viewsets.ModelViewSet):
    queryset = DebtTransaction.objects.all()
    serializer_class = DebtTransactionSerializer
    filterset_fields = ['customer', 'transaction_type']
    ordering_fields = ['date']
    ordering = ['-date']

