from django.db import models


class ExchangeRate(models.Model):
    base_currency = models.CharField(max_length=3)
    target_currency = models.CharField(max_length=3)
    rate = models.DecimalField(max_digits=18, decimal_places=8)
    fetched_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["base_currency", "target_currency"],
                name="unique_exchange_rate_pair"
            )
        ]

    def __str__(self):
        return f"{self.base_currency} to {self.target_currency}"
