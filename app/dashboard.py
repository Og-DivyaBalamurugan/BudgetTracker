# app/dashboard.py
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app import mysql
from app.ml_model import get_predictions_for_user

dashboard = Blueprint('dashboard', __name__)

@dashboard.route('/')
@dashboard.route('/dashboard')
@login_required
def index():
    cursor = mysql.connection.cursor()

    # Get current month and year
    cursor.execute("SELECT MONTH(NOW()) as month, YEAR(NOW()) as year")
    current_date = cursor.fetchone()
    month = current_date['month']
    year = current_date['year']

    # Get total income
    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0) as total
        FROM transactions
        WHERE user_id = %s AND type = 'income'
    """, (current_user.id,))
    total_income = float(cursor.fetchone()['total'])

    # Get total expenses
    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0) as total
        FROM transactions
        WHERE user_id = %s AND type = 'expense'
    """, (current_user.id,))
    total_expense = float(cursor.fetchone()['total'])

    # Get recent transactions
    cursor.execute("""
        SELECT t.*, c.name as category_name, c.icon as category_icon
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = %s
        ORDER BY t.date DESC
        LIMIT 5
    """, (current_user.id,))
    recent_transactions = cursor.fetchall()

    # Get spending per category this month (for donut chart)
    cursor.execute("""
        SELECT c.name, c.icon, COALESCE(SUM(t.amount), 0) as total
        FROM categories c
        LEFT JOIN transactions t ON c.id = t.category_id
        AND t.user_id = %s
        AND t.type = 'expense'
        AND MONTH(t.date) = %s
        AND YEAR(t.date) = %s
        GROUP BY c.id, c.name, c.icon
        HAVING total > 0
    """, (current_user.id, month, year))
    category_spending = cursor.fetchall()

    # Get budget vs actual for this month (for bar chart)
    cursor.execute("""
        SELECT c.name, c.icon,
        COALESCE(b.amount, 0) as budget_amount,
        COALESCE(SUM(t.amount), 0) as spent
        FROM categories c
        LEFT JOIN budgets b ON c.id = b.category_id
        AND b.user_id = %s AND b.month = %s AND b.year = %s
        LEFT JOIN transactions t ON c.id = t.category_id
        AND t.user_id = %s AND t.type = 'expense'
        AND MONTH(t.date) = %s AND YEAR(t.date) = %s
        GROUP BY c.id, c.name, c.icon, b.amount
        HAVING budget_amount > 0 OR spent > 0
    """, (current_user.id, month, year, current_user.id, month, year))
    budget_vs_actual = cursor.fetchall()

    # Get monthly spending trend for last 6 months (for line chart)
    cursor.execute("""
        SELECT
        DATE_FORMAT(date, '%%b %%Y') as month_label,
        COALESCE(SUM(amount), 0) as total
        FROM transactions
        WHERE user_id = %s AND type = 'expense'
        AND date >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
        GROUP BY DATE_FORMAT(date, '%%Y-%%m')
        ORDER BY MIN(date) ASC
    """, (current_user.id,))
    monthly_trend = cursor.fetchall()

    # Get active budget warnings
    cursor.execute("""
        SELECT c.name, c.icon, b.amount as budget_amount,
        COALESCE(SUM(t.amount), 0) as spent
        FROM budgets b
        JOIN categories c ON b.category_id = c.id
        LEFT JOIN transactions t ON b.category_id = t.category_id
        AND t.user_id = %s AND t.type = 'expense'
        AND MONTH(t.date) = %s AND YEAR(t.date) = %s
        WHERE b.user_id = %s AND b.month = %s AND b.year = %s
        GROUP BY b.id, c.name, c.icon, b.amount
        HAVING (spent / budget_amount * 100) >= 75
    """, (current_user.id, month, year, current_user.id, month, year))
    warnings = cursor.fetchall()

    
    # Get ML predictions for next month
    predictions = get_predictions_for_user(cursor, current_user.id)
    cursor.close()

    # Prepare chart data
    # Donut chart data
    donut_labels = [c['name'] for c in category_spending]
    donut_data = [float(c['total']) for c in category_spending]

    # Bar chart data
    bar_labels = [b['name'] for b in budget_vs_actual]
    bar_budget = [float(b['budget_amount']) for b in budget_vs_actual]
    bar_spent = [float(b['spent']) for b in budget_vs_actual]

    # Line chart data
    line_labels = [m['month_label'] for m in monthly_trend]
    line_data = [float(m['total']) for m in monthly_trend]

    # Process warnings
    warnings_list = []
    for w in warnings:
        spent = float(w['spent'])
        budget = float(w['budget_amount'])
        percentage = round(spent / budget * 100, 1)
        warnings_list.append({
            'name': w['name'],
            'icon': w['icon'],
            'spent': spent,
            'budget': budget,
            'percentage': percentage,
            'status': 'danger' if percentage >= 100 else 'warning'
        })

    balance = total_income - total_expense

    return render_template('dashboard.html',
        total_income=total_income,
        total_expense=total_expense,
        balance=balance,
        recent_transactions=recent_transactions,
        donut_labels=donut_labels,
        donut_data=donut_data,
        bar_labels=bar_labels,
        bar_budget=bar_budget,
        bar_spent=bar_spent,
        line_labels=line_labels,
        line_data=line_data,
        warnings=warnings_list,
        predictions=predictions,
        month=month,
        year=year
    )