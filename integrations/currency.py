import requests
from decimal import Decimal
from datetime import timedelta

from django.utils import timezone
from rest_framework.exceptions import APIException

from .models import ExchangeRate


CACHE_TTL = timedelta(hours=6)


class CurrencyAPIError(APIException):
    status_code = 503
    default_detail = "Currency exchange service is unavailable."


def get_exchange_rate(from_currency, to_currency="INR"):
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    if from_currency == to_currency:
        return Decimal("1")

    cached_rate = ExchangeRate.objects.filter(
        base_currency=from_currency,
        target_currency=to_currency
    ).first()

    if cached_rate and timezone.now() - cached_rate.fetched_at < CACHE_TTL:
        return cached_rate.rate

    try:
        url = f"https://open.er-api.com/v6/latest/{from_currency}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()

        if data.get("result") != "success":
            raise ValueError("Exchange rate API error")

        rate_value = data["rates"].get(to_currency)

        if rate_value is None:
            raise ValueError("Target currency not supported")

        rate = Decimal(str(rate_value))

        if rate <= 0:
            raise ValueError("Invalid exchange rate")

        ExchangeRate.objects.update_or_create(
            base_currency=from_currency,
            target_currency=to_currency,
            defaults={"rate": rate}
        )

        return rate

    except Exception as exc:
        if cached_rate:
            return cached_rate.rate

        raise CurrencyAPIError() from exc


def convert_to_inr(amount, from_currency):
    rate = get_exchange_rate(from_currency, "INR")
    converted_amount = Decimal(str(amount)) * rate
    return converted_amount.quantize(Decimal("0.01"))