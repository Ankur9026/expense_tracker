from django.urls import path
from .views import CurrencyConvertView

urlpatterns = [
    path(
        "currency/convert/",
        CurrencyConvertView.as_view(),
        name="currency-convert"
    ),
]