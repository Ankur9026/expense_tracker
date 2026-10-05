from budgets.models import Budget
from django.utils import timezone
from expenses.models import Expense
from django.db.models import Sum
from decimal import Decimal
from datetime import datetime, date
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics



class MonthlyReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        month = request.query_params.get("month")

        if not month:
            return Response(
                {"month": "Please provide month in YYYY-MM format."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            parsed_month = datetime.strptime(month, "%Y-%m")
            if parsed_month.strftime("%Y-%m") != month:
                raise ValueError
        except ValueError:
            return Response(
                {"month": "Invalid month format. Use YYYY-MM."},
                status=status.HTTP_400_BAD_REQUEST
            )

        year = parsed_month.year
        month_number = parsed_month.month

        expenses = Expense.objects.filter(
            user=request.user,
            date__year=year,
            date__month=month_number
        )

        total_spend = expenses.aggregate(
            total=Sum("amount_in_base_currency")
        )["total"] or Decimal("0.00")

        category_data = expenses.values(
            "category_id",
            "category__name"
        ).annotate(
            spent=Sum("amount_in_base_currency")
        ).order_by("category__name")

        categories = []

        for item in category_data:
            spent = item["spent"] or Decimal("0.00")

            if total_spend > 0:
                percentage = (spent / total_spend) * 100
            else:
                percentage = Decimal("0.00")

            budget = Budget.objects.filter(
                user=request.user,
                category_id=item["category_id"],
                month=month
            ).first()

            limit_amount = (
                budget.limit_amount if budget
                else Decimal("0.00")
            )

            remaining = limit_amount - spent

            categories.append({
                "category_id": item["category_id"],
                "category_name": item["category__name"],
                "spent": str(spent),
                "percentage": round(percentage, 2),
                "budget_limit": str(limit_amount),
                "budget_remaining": str(remaining),
                "is_overspent": spent > limit_amount
                    if budget else False
            })

        return Response({
            "month": month,
            "total_spend": str(total_spend),
            "categories": categories
        })

class MonthlyTrendView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        months_param = request.query_params.get("months", "6")

        try:
            months = int(months_param)
            if months < 1 or months > 24:
                raise ValueError
        except (ValueError, TypeError):
            return Response(
                {"months": "Months must be an integer between 1 and 24."},
                status=status.HTTP_400_BAD_REQUEST
            )

        today = date.today()
        current_year = today.year
        current_month = today.month

        
        month_list = []

        for i in range(months - 1, -1, -1):
            month_index = current_year * 12 + current_month - 1 - i
            year = month_index // 12
            month_number = month_index % 12 + 1
            month_list.append(date(year, month_number, 1))

        results = []
        previous_total = None

        for month_date in month_list:
            total = Expense.objects.filter(
                user=request.user,
                date__year=month_date.year,
                date__month=month_date.month
            ).aggregate(
                total=Sum("amount")
            )["total"] or Decimal("0.00")

            if previous_total is None:
                percentage_change = None
            elif previous_total == 0:
                percentage_change = None if total == 0 else "N/A"
            else:
                change = (
                    (total - previous_total) / previous_total
                ) * 100
                percentage_change = round(change, 2)

            results.append({
                "month": month_date.strftime("%Y-%m"),
                "total_spend": str(total),
                "percentage_change": percentage_change
            })

            previous_total = total

        return Response({
            "months": months,
            "trend": results
        })

class BudgetVsActualView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        
        month = request.query_params.get("month")

        if not month:
            return Response(
                {"month": "This field is required. Use YYYY-MM."},
                status=status.HTTP_400_BAD_REQUEST
            )

        
        try:
            parsed_month = datetime.strptime(month, "%Y-%m")

            if parsed_month.strftime("%Y-%m") != month:
                raise ValueError

        except ValueError:
            return Response(
                {"month": "Invalid month format. Use YYYY-MM."},
                status=status.HTTP_400_BAD_REQUEST
            )

        
        budgets = Budget.objects.filter(
            user=request.user,
            month=month
        ).select_related("category")

        results = []
        total_budget = Decimal("0.00")
        total_actual_spend = Decimal("0.00")

        for budget in budgets:
            actual_spend = Expense.objects.filter(
                user=request.user,
                category=budget.category,
                date__year=parsed_month.year,
                date__month=parsed_month.month
            ).aggregate(
                total=Sum("amount_in_base_currency")
            )["total"] or Decimal("0.00")

            remaining = budget.limit_amount - actual_spend

            total_budget += budget.limit_amount
            total_actual_spend += actual_spend

            results.append({
                "category_id": budget.category.id,
                "category": budget.category.name,
                "budget": str(budget.limit_amount),
                "actual_spend": str(actual_spend),
                "remaining": str(remaining),
                "is_overspent": actual_spend > budget.limit_amount
            })

        
        return Response({
            "month": month,
            "total_budget": str(total_budget),
            "total_actual_spend": str(total_actual_spend),
            "total_remaining": str(total_budget - total_actual_spend),
            "categories": results
        })

class MonthlyExpenseReportView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        expenses = Expense.objects.filter(
            user=request.user
        )

        monthly_report = expenses.values(
            "date__year",
            "date__month"
        ).annotate(
            total=Sum("amount")
        ).order_by(
            "-date__year",
            "-date__month"
        )

        result = []

        for item in monthly_report:
            month = f"{item['date__year']}-{item['date__month']:02d}"

            result.append({
                "month": month,
                "total": item["total"]
            })

        return Response({
            "monthly_report": result
        })


class CategoryExpenseReportView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        expenses = Expense.objects.filter(
            user=request.user
        )

        category_report = expenses.values(
            "category__name"
        ).annotate(
            total=Sum("amount")
        ).order_by("-total")

        result = []

        for item in category_report:
            result.append({
                "category": item["category__name"],
                "total": item["total"]
            })

        return Response({
            "category_report": result
        })

class BudgetVsExpenseReportView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        current_month = timezone.now().strftime("%Y-%m")

        total_budget = Budget.objects.filter(
            user=request.user,
            month=current_month
        ).aggregate(
            total=Sum("limit_amount")
        )["total"] or 0

        total_expenses = Expense.objects.filter(
            user=request.user,
            date__year=timezone.now().year,
            date__month=timezone.now().month
        ).aggregate(
            total=Sum("amount_in_base_currency")
        )["total"] or 0

        remaining = total_budget - total_expenses

        return Response({
            "month": current_month,
            "budget": total_budget,
            "spent": total_expenses,
            "remaining": remaining
        })

class DateRangeExpenseReportView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        if not start_date or not end_date:
            return Response({
                "error": "start_date and end_date are required."
            }, status=400)

        expenses = Expense.objects.filter(
            user=request.user,
            date__range=[start_date, end_date]
        )

        total_expenses = expenses.count()

        total_spent = expenses.aggregate(
            total=Sum("amount")
        )["total"] or 0

        return Response({
            "start_date": start_date,
            "end_date": end_date,
            "total_expenses": total_expenses,
            "total_spent": total_spent
        })

