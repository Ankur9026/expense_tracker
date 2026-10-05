# Expense & Budget Tracker API

A Django REST Framework backend API for managing personal expenses,
categories, budgets, reports, and currency conversion.

## Project Overview

The Expense & Budget Tracker API allows authenticated users to:

- Register and login using JWT authentication
- Manage expense categories
- Create and manage expenses
- Create and manage monthly budgets
- Track budget vs actual spending
- Generate monthly and trend reports
- Convert foreign currencies to INR
- Cache exchange rates
- Import and export expenses using CSV
- View activity logs
- Search, filter, order, and paginate expenses

The project also implements user data isolation and admin read-only
access.

---

## Technology Stack

- Python
- Django
- Django REST Framework
- Simple JWT
- django-filter
- drf-spectacular
- SQLite
- REST API
- Postman
- External Currency Exchange API

---

## Main Features

### 1. Authentication

- User registration
- JWT login
- Current user profile
- Change password
- Logout with refresh-token blacklist
- Authentication-protected APIs

### 2. Categories

Users can:

- Create categories
- View categories
- Update categories
- Delete categories

Categories are associated with users.

### 3. Expenses

Users can:

- Create expenses
- View expenses
- Update expenses
- Delete expenses

Expense information includes:

- Amount
- Currency
- Category
- Description
- Date
- Amount in base currency

### 4. Expense Search, Filter and Ordering

Expense APIs support:

- Pagination
- Search by description
- Filter by category
- Filter by currency
- Filter by date
- Ordering by amount
- Ordering by date
- Ordering by creation date

Example:

```text
GET /api/expenses/?search=Lunch
GET /api/expenses/?category=1
GET /api/expenses/?currency=USD
GET /api/expenses/?ordering=-amount
GET /api/expenses/?page=2