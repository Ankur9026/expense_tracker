from django.urls import path
from .views import MonthlyReportView, MonthlyTrendView, BudgetVsActualView, MonthlyExpenseReportView, CategoryExpenseReportView,  BudgetVsExpenseReportView, DateRangeExpenseReportView

urlpatterns = [
    path(
        "reports/monthly/",
        MonthlyReportView.as_view(),
        name="monthly-report"
    ),
    path(
    "reports/trend/",
    MonthlyTrendView.as_view(),
    name="monthly-trend"
),
    path(
        "reports/budget-vs-actual/",
        BudgetVsActualView.as_view(),
        name="budget-vs-actual"
    ),
    path(
        "monthly/",
        MonthlyExpenseReportView.as_view(),
        name="monthly-expense-report"
    ),
    path(
    "category/",
    CategoryExpenseReportView.as_view(),
    name="category-expense-report"
),
   path(
    "budget-vs-expense/",
    BudgetVsExpenseReportView.as_view(),
    name="budget-vs-expense-report"
),
   path(
    "date-range/",
    DateRangeExpenseReportView.as_view(),
    name="date-range-expense-report"
),
]