from django.db import connection
from django.utils import timezone
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Category


class ExpenseAPITestCase(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="TestPassword123"
        )

        self.category = Category.objects.create(
            name="Food",
            owner=self.user
        )

        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}"
        )

    def test_expense_list_requires_authentication(self):
        response = self.client.get("/api/expenses/")

        self.assertEqual(response.status_code, 200)

    def test_create_expense(self):
        data = {
            "category": self.category.id,
            "amount": "500.00",
            "currency": "INR",
            "description": "Test Lunch",
            "date": "2026-10-04",
        }

        response = self.client.post(
            "/api/expenses/",
            data,
            format="json"
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["amount"], "500.00")
        self.assertEqual(response.data["currency"], "INR")
        self.assertEqual(
            response.data["description"],
            "Test Lunch"
        )

    def test_user_cannot_see_other_users_expense(self):
        from .models import Expense

        other_user = User.objects.create_user(
            username="otheruser",
            password="TestPassword123"
        )

        other_category = Category.objects.create(
            name="Travel",
            owner=other_user
        )

        other_expense = Expense.objects.create(
            user=other_user,
            category=other_category,
            amount="1000.00",
            currency="INR",
            description="Other User Expense",
            date="2026-10-04"
        )

        response = self.client.get(
            f"/api/expenses/{other_expense.id}/"
        )

        self.assertEqual(response.status_code, 404)

    def test_foreign_currency_conversion(self):
        data = {
            "category": self.category.id,
            "amount": "100.00",
            "currency": "USD",
            "description": "Foreign Currency Test",
            "date": "2026-10-04",
        }

        response = self.client.post(
            "/api/expenses/",
            data,
            format="json"
        )

        self.assertEqual(response.status_code, 201)

        self.assertEqual(
            response.data["currency"],
            "USD"
        )

        self.assertIsNotNone(
            response.data["amount_in_base_currency"]
        )

        self.assertGreater(
            float(response.data["amount_in_base_currency"]),
            0
        )

    def test_overspent_budget(self):
        from budgets.models import Budget
        from .models import Expense

        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            month="2026-10",
            limit_amount="1000.00"
        )

        Expense.objects.create(
            user=self.user,
            category=self.category,
            amount="1500.00",
            currency="INR",
            amount_in_base_currency="1500.00",
            description="Overspent Test",
            date="2026-10-04"
        )

        response = self.client.get(
            "/api/reports/budget-vs-actual/?month=2026-10"
        )

        self.assertEqual(response.status_code, 200)

        data = response.data

        self.assertEqual(response.status_code, 200)

    def test_monthly_category_percentages_sum_to_100(self):
        from .models import Expense

        Expense.objects.create(
            user=self.user,
            category=self.category,
            amount="600.00",
            currency="INR",
            amount_in_base_currency="600.00",
            description="Food 1",
            date="2026-10-05"
        )

        Expense.objects.create(
            user=self.user,
            category=self.category,
            amount="400.00",
            currency="INR",
            amount_in_base_currency="400.00",
            description="Food 2",
            date="2026-10-10"
        )

        response = self.client.get(
            "/api/reports/monthly/?month=2026-10"
        )

        self.assertEqual(response.status_code, 200)

        data = response.data

        categories = data["categories"]

        total_percentage = sum(
            float(item["percentage"])
            for item in categories
        )

        self.assertAlmostEqual(
            total_percentage,
            100.0,
            places=1
        ) 

    def test_trend_month_over_month_percentage(self):
        from .models import Expense

        # September spend = 1000
        Expense.objects.create(
            user=self.user,
            category=self.category,
            amount="1000.00",
            currency="INR",
            amount_in_base_currency="1000.00",
            description="September Expense",
            date="2026-09-15"
        )

        # October spend = 1500
        Expense.objects.create(
            user=self.user,
            category=self.category,
            amount="1500.00",
            currency="INR",
            amount_in_base_currency="1500.00",
            description="October Expense",
            date="2026-10-15"
        )

        response = self.client.get(
            "/api/reports/trend/"
        )

        self.assertEqual(response.status_code, 200)

        data = response.data


    def test_currency_stale_cache_refresh(self):
        from datetime import timedelta
        from decimal import Decimal
        from unittest.mock import patch

        from integrations.models import ExchangeRate
        from integrations import currency

        # 1. Create old cached rate
        cached_rate = ExchangeRate.objects.create(
            base_currency="USD",
            target_currency="INR",
            rate=Decimal("90.00"),
        )

        # 2. Make cache 7 hours old
        stale_time = timezone.now() - timedelta(hours=7)

        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE integrations_exchangerate
                SET fetched_at = %s
                WHERE id = %s
                """,
                [stale_time, cached_rate.id]
            )

        cached_rate.refresh_from_db()

        # 3. Confirm cache is stale
        cache_age = timezone.now() - cached_rate.fetched_at

        self.assertGreater(
            cache_age,
            timedelta(hours=6)
        )

        # 4. Mock external currency API
        with patch.object(
             currency.requests,
             "get"
        ) as mock_get:

            mock_response = mock_get.return_value

            mock_response.raise_for_status.return_value = None

            mock_response.json.return_value = {
                "result": "success",
                "rates": {
                     "INR": 95.99
                }
            }

            # 5. Convert using stale cache
            result = currency.convert_to_inr(
                Decimal("100.00"),
                "USD"
            )

            # 6. New API rate must be used
            self.assertEqual(
                result,
                Decimal("9599.00")
            )

            # 7. External API must be called once
            mock_get.assert_called_once()

        # 8. New rate must be saved in database
        cached_rate.refresh_from_db()

        self.assertEqual(
            cached_rate.rate,
            Decimal("95.99")
        )

    def test_currency_api_unavailable_uses_stale_cache(self):
        from datetime import timedelta
        from decimal import Decimal
        from unittest.mock import patch
        from integrations.models import ExchangeRate
        from integrations import currency

        cached_rate = ExchangeRate.objects.create(
            base_currency="USD",
            target_currency="INR",
            rate=Decimal("90.00"),
        )

        stale_time = timezone.now() - timedelta(hours=7)

        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE integrations_exchangerate
                SET fetched_at = %s
                WHERE id = %s
                """,
               [stale_time, cached_rate.id]
        )

        cached_rate.refresh_from_db()

        with patch.object(
            currency.requests,
            "get",
            side_effect=Exception("Currency API is down")
        ) as mock_get:

           result = currency.convert_to_inr(
               Decimal("100.00"),
               "USD"
           )

           self.assertEqual(result, Decimal("9000.00"))
           mock_get.assert_called_once()

    def test_no_cache_api_failure_does_not_create_expense(self):
        from decimal import Decimal
        from unittest.mock import patch
        from integrations import currency
        from .models import Expense

        category = Category.objects.create(
            name="Test Category",
            owner=self.user
        )

        before_count = Expense.objects.count()

        with patch.object(
            currency.requests,
            "get",
            side_effect=Exception("Currency API is down")
        ):
            response = self.client.post(
                "/api/expenses/",
                {
                    "category": category.id,
                    "amount": "100.00",
                    "currency": "USD",
                    "description": "API failure test",
                    "date": "2026-10-01"
                },
                format="json"
            )

        after_count = Expense.objects.count()

        self.assertEqual(response.status_code, 503)
        self.assertEqual(before_count, after_count)

    def test_negative_expense_amount(self):
        category = Category.objects.create(
            name="Validation Test",
            owner=self.user
        )

        response = self.client.post(
            "/api/expenses/",
            {
               "category": category.id,
               "amount": "-100.00",
               "currency": "INR",
               "description": "Negative amount",
               "date": "2026-10-01"
            },
            format="json"
        )

        self.assertEqual(response.status_code, 400)


    def test_future_expense_date(self):
        category = Category.objects.create(
            name="Future Test",
            owner=self.user
        )

        response = self.client.post(
            "/api/expenses/",
            {
                "category": category.id,
                "amount": "100.00",
                "currency": "INR",
                "description": "Future expense",
                "date": "2099-01-01"
            },
            format="json"
        )

        self.assertEqual(response.status_code, 400)


    def test_invalid_currency(self):
        category = Category.objects.create(
            name="Currency Test",
            owner=self.user
        )

        response = self.client.post(
           "/api/expenses/",
           {
              "category": category.id,
              "amount": "100.00",
              "currency": "XYZ",
              "description": "Invalid currency",
              "date": "2026-10-01"
            },
            format="json"
        )

        self.assertEqual(response.status_code, 400) 


    def test_pagination_search_filter_ordering(self):
        category = Category.objects.create(
            name="Food",
            owner=self.user
        )

        for i in range(5):
            self.client.post(
                 "/api/expenses/",
                 {
                    "category": category.id,
                    "amount": str(100 + i),
                    "currency": "INR",
                    "description": f"Lunch {i}",
                    "date": f"2026-10-0{i + 1}"
                },
                format="json"
            )

        # Pagination
        response = self.client.get("/api/expenses/?page=1")
        self.assertEqual(response.status_code, 200)
        self.assertIn("results", response.data)

        # Search
        response = self.client.get(
             "/api/expenses/?search=Lunch%202"
        )
        self.assertEqual(response.status_code, 200)

        # Filter
        response = self.client.get(
             f"/api/expenses/?category={category.id}"
        )
        self.assertEqual(response.status_code, 200)

        # Ordering
        response = self.client.get(
            "/api/expenses/?ordering=-amount"
        )
        self.assertEqual(response.status_code, 200)



    def test_admin_is_read_only(self):
        from django.contrib.auth.models import User
        from .models import Expense

        admin = User.objects.create_superuser(
            username="testadmin",
            email="admin@test.com",
            password="Admin@12345"
        )

        self.client.force_authenticate(user=admin)

        category = Category.objects.create(
            name="Admin Test",
            owner=self.user
        )

        # Admin can READ
        response = self.client.get("/api/expenses/")
        self.assertEqual(response.status_code, 200)

        # Admin cannot CREATE
        response = self.client.post(
            "/api/expenses/",
            {
                "category": category.id,
                "amount": "500.00",
                "currency": "INR",
                "description": "Admin create test",
                "date": "2026-10-01"
            },
            format="json"
        )
        self.assertEqual(response.status_code, 403)

        # Create expense as normal user for update/delete tests
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            "/api/expenses/",
            {
                "category": category.id,
                "amount": "100.00",
                "currency": "INR",
                "description": "Admin readonly test",
                "date": "2026-10-01"
            },
            format="json"
        )

        self.assertEqual(response.status_code, 201)

        expense_id = response.data["id"]

        # Admin cannot UPDATE
        self.client.force_authenticate(user=admin)

        response = self.client.patch(
            f"/api/expenses/{expense_id}/",
            {"amount": "999.00"},
            format="json"
        )
        self.assertEqual(response.status_code, 403)

        # Admin cannot DELETE
        response = self.client.delete(
            f"/api/expenses/{expense_id}/"
        )
        self.assertEqual(response.status_code, 403)