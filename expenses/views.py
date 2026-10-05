import io
import csv
from  django.http import HttpResponse
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics,filters
from rest_framework.permissions import IsAuthenticated

from drf_spectacular.openapi import AutoSchema
from budgets.models import Budget
from django.utils import timezone
from django.db.models import Sum, Count
from users.permissions import CategoryPermission
from .models import Category, Expense, ActivityLog
from .serializers import CategorySerializer, ExpenseSerializer, ActivityLogSerializer
from users.permissions import AdminReadOnlyOrUserWrite
from rest_framework.response import Response


class CategoryListCreateView(generics.ListCreateAPIView):
    serializer_class = CategorySerializer
    permission_classes = [CategoryPermission]

    def get_queryset(self):
        user = self.request.user

        if user.is_staff:
            return Category.objects.all()

        return Category.objects.filter(
            Q(owner=user) | Q(owner__is_staff=True)
        )

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CategorySerializer
    permission_classes = [CategoryPermission]

    def get_queryset(self):
        user = self.request.user

        if user.is_staff:
            return Category.objects.all()

        return Category.objects.filter(
            Q(owner=user) | Q(owner__is_staff=True)
        )


class ExpenseListCreateView(generics.ListCreateAPIView):
    serializer_class = ExpenseSerializer
    permission_classes = [AdminReadOnlyOrUserWrite]

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_fields = ['category', 'currency', 'date']
    search_fields = ['description']
    ordering_fields = ['amount', 'date', 'created_at']
    ordering = ['-date']

    def get_queryset(self):
        user = self.request.user

        if user.is_staff:
            return Expense.objects.all()

        return Expense.objects.filter(user=user)

    def perform_create(self, serializer):
        expense = serializer.save(user=self.request.user)

        ActivityLog.objects.create(
            user=self.request.user,
            action="EXPENSE_CREATED",
            description=f"Expense #{expense.id} created"
    )

class ExpenseDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ExpenseSerializer
    permission_classes = [AdminReadOnlyOrUserWrite]

    def get_queryset(self):
        user = self.request.user

        if user.is_staff:
            return Expense.objects.all()

        return Expense.objects.filter(user=user)

    def perform_update(self, serializer):
        expense = serializer.save()

        ActivityLog.objects.create(
            user=self.request.user,
            action="EXPENSE_UPDATED",
            description=f"Expense #{expense.id} updated"
    )

    def perform_destroy(self, instance):
        ActivityLog.objects.create(
            user=self.request.user,
            action="EXPENSE_DELETED",
            description=f"Expense #{instance.id} deleted"
    )

        instance.delete()

class DashboardSummaryView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        current_month = timezone.now().strftime("%Y-%m")

        expenses = Expense.objects.filter(
            user=request.user,
            date__year=timezone.now().year,
            date__month=timezone.now().month
        )

        total_expenses = expenses.count()

        total_spent = expenses.aggregate(
            total=Sum("amount_in_base_currency")
        )["total"] or 0

        total_budget = Budget.objects.filter(
            user=request.user,
            month=current_month
        ).aggregate(
            total=Sum("limit_amount")
        )["total"] or 0

        remaining_budget = total_budget - total_spent

        category_summary = expenses.values(
            "category__name"
        ).annotate(
            total=Sum("amount_in_base_currency")
        ).order_by("-total")

        return Response({
             "month": current_month,
             "total_expenses": total_expenses,
             "total_spent": total_spent,
             "total_budget": total_budget,
             "remaining_budget": remaining_budget,
             "category_summary": [
                  {
                     "category": item["category__name"],
                     "total": item["total"]
                  }
                  for item in category_summary
        ],
})

class ExpenseCSVExportView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        expenses = Expense.objects.filter(
            user=request.user
        ).order_by("-date")

        response = HttpResponse(
            content_type="text/csv"
        )

        response["Content-Disposition"] = (
            'attachment; filename="expenses.csv"'
        )

        writer = csv.writer(response)

        writer.writerow([
            "ID",
            "Category",
            "Amount",
            "Currency",
            "Amount in INR",
            "Description",
            "Date",
        ])

        for expense in expenses:
            writer.writerow([
                expense.id,
                expense.category.name,
                expense.amount,
                expense.currency,
                expense.amount_in_base_currency,
                expense.description,
                expense.date,
            ])

        return response

class ExpenseCSVImportView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        csv_file = request.FILES.get("file")

        if not csv_file:
            return Response(
                {"error": "CSV file is required."},
                status=400
            )

        if not csv_file.name.endswith(".csv"):
            return Response(
                {"error": "Only CSV files are allowed."},
                status=400
            )

        decoded_file = csv_file.read().decode("utf-8")
        reader = csv.DictReader(io.StringIO(decoded_file))

        created = 0

        for row in reader:
            category = Category.objects.filter(
                name=row["Category"]
            ).first()

            if not category:
                continue

            Expense.objects.create(
                user=request.user,
                category=category,
                amount=row["Amount"],
                currency=row["Currency"].upper(),
                description=row["Description"],
                date=row["Date"],
                amount_in_base_currency=row.get("Amount in INR") or None
            )

            created += 1

        return Response({
            "message": "CSV imported successfully",
            "created": created
        })

class ActivityLogListView(generics.ListAPIView):
    serializer_class = ActivityLogSerializer
    permission_classes = [IsAuthenticated]

    schema = AutoSchema()

    def get_queryset(self):
        return ActivityLog.objects.filter(
            user=self.request.user
        )