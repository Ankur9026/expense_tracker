from rest_framework import serializers
from .models import Budget


class BudgetSerializer(serializers.ModelSerializer):

    class Meta:
        model = Budget
        fields = [
            "id",
            "category",
            "month",
            "limit_amount",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_month(self, value):
        if len(value) != 7 or value[4] != "-":
            raise serializers.ValidationError(
                "Month must be in YYYY-MM format."
            )

        return value

    def validate(self, data):
        user = self.context["request"].user
        category = data.get("category")
        month = data.get("month")

        if Budget.objects.filter(
            user=user,
            category=category,
            month=month
        ).exists():
            raise serializers.ValidationError(
                "Budget already exists for this category and month."
            )

        return data