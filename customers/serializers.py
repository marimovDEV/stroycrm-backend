from rest_framework import serializers
from .models import Customer, DebtTransaction
from decimal import Decimal

class DebtTransactionSerializer(serializers.ModelSerializer):
    customer_name = serializers.ReadOnlyField(source='customer.name')
    class Meta:
        model = DebtTransaction
        fields = '__all__'

    def create(self, validated_data):
        transaction = DebtTransaction.objects.create(**validated_data)
        customer = transaction.customer
        
        # Update customer debt based on transaction type
        if transaction.transaction_type == 'debt_added':
            customer.debt += Decimal(str(transaction.amount))
        elif transaction.transaction_type == 'payment':
            customer.debt -= Decimal(str(transaction.amount))
        elif transaction.transaction_type == 'adjustment':
            # Note: For simple adjustment, we assume 'amount' is the NEW debt or a delta?
            # Let's assume it's a delta for now to keep it simple.
            customer.debt += Decimal(str(transaction.amount))
        
        customer.save()
        return transaction

class CustomerSerializer(serializers.ModelSerializer):
    transactions = DebtTransactionSerializer(many=True, read_only=True)

    class Meta:
        model = Customer
        fields = '__all__'
