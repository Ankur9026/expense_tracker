from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from expenses.models import Category


class Budget(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="budgets"
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="budgets"
    )

    month = models.CharField(
        max_length=7
    )

    limit_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "category", "month"],
                name="unique_user_category_month_budget"
            )
        ]

    def __str__(self):
        return f"{self.user.username} - {self.category.name} - {self.month}"
