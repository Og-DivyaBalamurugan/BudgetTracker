# app/budget.py
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import mysql

budget = Blueprint('budget', __name__)

@budget.route('/budget')
@login_required
def index():
    cursor = mysql.connection.cursor()

    # Get current month and year
    cursor.execute("SELECT MONTH(NOW()) as month, YEAR(NOW()) as year")
    current_date = cursor.fetchone()
    current_month = current_date['month']
    current_year = current_date['year']

    # Allow viewing other months via query params
    # e.g. /budget?month=4&year=2026
    month = int(request.args.get('month', current_month))
    year = int(request.args.get('year', current_year))

    # Get all categories
    cursor.execute("SELECT * FROM categories")
    categories = cursor.fetchall()

    # Get budgets for selected month
    cursor.execute("""
        SELECT b.*, c.name as category_name, c.icon as category_icon
        FROM budgets b
        JOIN categories c ON b.category_id = c.id
        WHERE b.user_id = %s AND b.month = %s AND b.year = %s
    """, (current_user.id, month, year))
    budgets = cursor.fetchall()

    # Get actual spending per category for selected month
    cursor.execute("""
        SELECT c.id, c.name, c.icon,
        COALESCE(SUM(t.amount), 0) as spent
        FROM categories c
        LEFT JOIN transactions t ON c.id = t.category_id
        AND t.user_id = %s
        AND t.type = 'expense'
        AND MONTH(t.date) = %s
        AND YEAR(t.date) = %s
        GROUP BY c.id, c.name, c.icon
    """, (current_user.id, month, year))
    spending = cursor.fetchall()

    # Convert spending to dictionary
    spending_dict = {s['id']: s['spent'] for s in spending}

    # Calculate warning status for each budget
    budget_status = []
    for b in budgets:
        spent = float(spending_dict.get(b['category_id'], 0))
        budget_amount = float(b['amount'])
        percentage = (spent / budget_amount * 100) if budget_amount > 0 else 0

        if percentage >= 100:
            status = 'danger'
            status_text = 'Exceeded!'
        elif percentage >= 75:
            status = 'warning'
            status_text = 'Almost there!'
        else:
            status = 'safe'
            status_text = 'On track'

        budget_status.append({
            'id': b['id'],
            'category_id': b['category_id'],
            'category_name': b['category_name'],
            'category_icon': b['category_icon'],
            'budget_amount': budget_amount,
            'spent': spent,
            'percentage': round(percentage, 1),
            'status': status,
            'status_text': status_text
        })

    cursor.close()

    return render_template('budget.html',
        categories=categories,
        budget_status=budget_status,
        month=month,
        year=year,
        current_month=current_month,
        current_year=current_year
    )

@budget.route('/budget/set', methods=['POST'])
@login_required
def set_budget():
    category_id = request.form['category_id']
    amount = request.form['amount']
    month = request.form['month']
    year = request.form['year']

    cursor = mysql.connection.cursor()
    try:
        cursor.execute("""
            SELECT id FROM budgets
            WHERE user_id = %s AND category_id = %s
            AND month = %s AND year = %s
        """, (current_user.id, category_id, month, year))
        existing = cursor.fetchone()

        if existing:
            cursor.execute("""
                UPDATE budgets SET amount = %s
                WHERE user_id = %s AND category_id = %s
                AND month = %s AND year = %s
            """, (amount, current_user.id, category_id, month, year))
            flash('Budget updated successfully!', 'success')
        else:
            cursor.execute("""
                INSERT INTO budgets (user_id, category_id, amount, month, year)
                VALUES (%s, %s, %s, %s, %s)
            """, (current_user.id, category_id, amount, month, year))
            flash('Budget set successfully!', 'success')

        mysql.connection.commit()
    except:
        flash('Error setting budget!', 'danger')
    finally:
        cursor.close()

    # Redirect back to same month view
    return redirect(url_for('budget.index', month=month, year=year))

@budget.route('/budget/delete/<int:id>', methods=['POST'])
@login_required
def delete_budget(id):
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("""
            DELETE FROM budgets
            WHERE id = %s AND user_id = %s
        """, (id, current_user.id))
        mysql.connection.commit()
        flash('Budget deleted!', 'success')
    except:
        flash('Error deleting budget!', 'danger')
    finally:
        cursor.close()

    return redirect(url_for('budget.index'))