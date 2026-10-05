from rest_framework import serializers
from integrations.currency import convert_to_inr

from .models import Category, Expense, ActivityLog


class CategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = Category
        fields = [
            'id',
            'name',
            'owner',
            'created_at',
        ]
        read_only_fields = ['id', 'owner', 'created_at']


class ExpenseSerializer(serializers.ModelSerializer):

    class Meta:
        model = Expense
        fields = [
            'id',
            'user',
            'category',
            'amount',
            'currency',
            'amount_in_base_currency',
            'description',
            'date',
            'created_at',
            'updated_at',
        ]

        read_only_fields = [
            'id',
            'user',
            'amount_in_base_currency',
            'created_at',
            'updated_at',
        ]

    def create(self, validated_data):
        amount = validated_data["amount"]
        currency = validated_data["currency"].upper()

        
        inr_amount = convert_to_inr(amount, currency)

        validated_data["currency"] = currency
        validated_data["amount_in_base_currency"] = inr_amount

        return super().create(validated_data)

    def update(self, instance, validated_data):
        amount = validated_data.get("amount", instance.amount)
        currency = validated_data.get(
            "currency", instance.currency
        ).upper()

        # Recalculate INR
        inr_amount = convert_to_inr(amount, currency)

        validated_data["currency"] = currency
        validated_data["amount_in_base_currency"] = inr_amount

        return super().update(instance, validated_data)

    def validate(self, attrs):
        from django.utils import timezone

        expense_date = attrs.get("date")
        currency = attrs.get("currency", "").upper()

        if expense_date and expense_date > timezone.localdate():
           raise serializers.ValidationError({
               "date": "Expense date cannot be in the future."
           })

        valid_currencies = ["INR", "USD", "EUR", "GBP", "AED", "CAD", "AUD"]

        if currency not in valid_currencies:
            raise serializers.ValidationError({
                "currency": "Invalid currency."
            })

        attrs["currency"] = currency

        return attrs

class ActivityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityLog
        fields = [
            "id",
            "action",
            "description",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
        ]