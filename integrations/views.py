from decimal import Decimal, InvalidOperation

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from .currency import get_exchange_rate


class CurrencyConvertView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        amount = request.query_params.get("amount")
        from_currency = request.query_params.get("from", "").upper()
        to_currency = request.query_params.get("to", "INR").upper()

        # Validate required amount
        if not amount:
            return Response(
                {"amount": "This field is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate currency codes
        if len(from_currency) != 3 or not from_currency.isalpha():
            return Response(
                {"from": "Enter a valid 3-letter currency code."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(to_currency) != 3 or not to_currency.isalpha():
            return Response(
                {"to": "Enter a valid 3-letter currency code."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate amount
        try:
            amount = Decimal(amount)
            if not amount.is_finite() or amount <= 0:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            return Response(
                {"amount": "Enter a valid positive amount."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Fetch exchange rate and convert
        try:
            rate = get_exchange_rate(from_currency, to_currency)
            converted_amount = (amount * rate).quantize(Decimal("0.01"))

        except Exception:
            return Response(
                {"error": "Currency conversion service is unavailable."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        return Response({
            "amount": str(amount),
            "from_currency": from_currency,
            "to_currency": to_currency,
            "exchange_rate": str(rate),
            "converted_amount": str(converted_amount),
        })
