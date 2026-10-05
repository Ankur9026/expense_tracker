from django.urls import path

from .views import CategoryListCreateView, CategoryDetailView, ExpenseListCreateView, ExpenseDetailView,DashboardSummaryView, ExpenseCSVExportView, ExpenseCSVImportView, ActivityLogListView

urlpatterns = [
    path('categories/', CategoryListCreateView.as_view(), name='category-list-create'),
    path('categories/<int:pk>/', CategoryDetailView.as_view(), name='category-detail'),
    path('expenses/', ExpenseListCreateView.as_view(), name='expense-list-create'),
    path('expenses/<int:pk>/',ExpenseDetailView.as_view(),name='expense-detail'),
    path("dashboard/", DashboardSummaryView.as_view(), name="dashboard-summary"),
    path("expenses/export/",ExpenseCSVExportView.as_view(),name="expense-csv-export"),
    path("expenses/import/",ExpenseCSVImportView.as_view(),name="expense-csv-import"),
    path("activity-logs/",ActivityLogListView.as_view(),name="activity-log-list"),
]