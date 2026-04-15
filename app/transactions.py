# app/transactions.py
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import mysql
import pandas as pd
import io
from app.pdf_parser import parse_gpay_pdf, categorize_gpay_transaction
# Create transactions blueprint
transactions = Blueprint('transactions', __name__)

@transactions.route('/transactions')
@login_required
def index():
    cursor = mysql.connection.cursor()
    
    # Get all transactions for current user
    cursor.execute("""
        SELECT t.*, c.name as category_name, c.icon as category_icon
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = %s
        ORDER BY t.date DESC
    """, (current_user.id,))
    transactions_list = cursor.fetchall()
    
    # Get all categories for the dropdown
    cursor.execute("SELECT * FROM categories")
    categories = cursor.fetchall()
    
    cursor.close()
    
    return render_template('transactions.html',
        transactions=transactions_list,
        categories=categories
    )

@transactions.route('/transactions/add', methods=['POST'])
@login_required
def add_transaction():
    transaction_type = request.form['type']
    amount = request.form['amount']
    description = request.form['description']
    date = request.form['date']
    category_id = request.form['category_id']
    
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("""
            INSERT INTO transactions 
            (user_id, category_id, type, amount, description, date)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (current_user.id, category_id, transaction_type, amount, description, date))
        mysql.connection.commit()
        flash('Transaction added successfully!', 'success')
    except:
        flash('Error adding transaction!', 'danger')
    finally:
        cursor.close()
    
    return redirect(url_for('transactions.index'))

@transactions.route('/transactions/upload', methods=['POST'])
@login_required
def upload_csv():
    if 'csv_file' not in request.files:
        flash('No file selected!', 'danger')
        return redirect(url_for('transactions.index'))
    
    file = request.files['csv_file']
    
    if file.filename == '':
        flash('No file selected!', 'danger')
        return redirect(url_for('transactions.index'))
    
    if not file.filename.endswith('.csv'):
        flash('Please upload a CSV file only!', 'danger')
        return redirect(url_for('transactions.index'))
    
    try:
        # Read CSV file using pandas
        stream = io.StringIO(file.stream.read().decode('UTF-8'))
        df = pd.read_csv(stream)
        
        # Clean column names - remove spaces and lowercase
        df.columns = df.columns.str.strip().str.lower()
        
        cursor = mysql.connection.cursor()
        
        # Get all categories for matching
        cursor.execute("SELECT * FROM categories")
        categories = cursor.fetchall()
        
        success_count = 0
        error_count = 0
        
        for _, row in df.iterrows():
            try:
                # Try to get values from common bank statement column names
                description = str(row.get('description', row.get('narration', row.get('details', ''))))
                amount = float(str(row.get('amount', row.get('debit', 0))).replace(',', ''))
                date = row.get('date', row.get('transaction date', ''))
                transaction_type = str(row.get('type', 'expense')).lower()
                
                # Auto categorize based on description
                category_id = auto_categorize(description, categories)
                
                cursor.execute("""
                    INSERT INTO transactions
                    (user_id, category_id, type, amount, description, date)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (current_user.id, category_id, transaction_type, amount, description, date))
                
                success_count += 1
            except:
                error_count += 1
                continue
        
        mysql.connection.commit()
        cursor.close()
        
        flash(f'Successfully imported {success_count} transactions! {error_count} rows skipped.', 'success')
    
    except Exception as e:
        flash(f'Error reading CSV file. Make sure it is properly formatted!', 'danger')
    
    return redirect(url_for('transactions.index'))

@transactions.route('/transactions/delete/<int:id>', methods=['POST'])
@login_required
def delete_transaction(id):
    cursor = mysql.connection.cursor()
    try:
        # Make sure user owns this transaction
        cursor.execute("""
            DELETE FROM transactions 
            WHERE id = %s AND user_id = %s
        """, (id, current_user.id))
        mysql.connection.commit()
        flash('Transaction deleted!', 'success')
    except:
        flash('Error deleting transaction!', 'danger')
    finally:
        cursor.close()
    
    return redirect(url_for('transactions.index'))


@transactions.route('/transactions/upload_pdf', methods=['POST'])
@login_required
def upload_pdf():
    if 'pdf_file' not in request.files:
        flash('No file selected!', 'danger')
        return redirect(url_for('transactions.index'))
    
    file = request.files['pdf_file']
    
    if file.filename == '':
        flash('No file selected!', 'danger')
        return redirect(url_for('transactions.index'))
    
    if not file.filename.endswith('.pdf'):
        flash('Please upload a PDF file only!', 'danger')
        return redirect(url_for('transactions.index'))
    
    try:
        # Parse the GPay PDF
        parsed_transactions = parse_gpay_pdf(file)
        
        if not parsed_transactions:
            flash('No transactions found in PDF. Make sure it is a GPay statement!', 'danger')
            return redirect(url_for('transactions.index'))
        
        cursor = mysql.connection.cursor()
        
        # Get all categories
        cursor.execute("SELECT * FROM categories")
        categories = cursor.fetchall()
        
        # Convert categories to dict for easy lookup
        category_dict = {c['name']: c['id'] for c in categories}
        
        success_count = 0
        error_count = 0
        
        for t in parsed_transactions:
            try:
                # Get category id based on description
                category_name = categorize_gpay_transaction(t['description'])
                category_id = category_dict.get(category_name, category_dict.get('Other'))
                
                cursor.execute("""
                    INSERT INTO transactions
                    (user_id, category_id, type, amount, description, date)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    current_user.id,
                    category_id,
                    t['type'],
                    t['amount'],
                    t['description'],
                    t['date']
                ))
                success_count += 1
            except:
                error_count += 1
                continue
        
        mysql.connection.commit()
        cursor.close()
        
        flash(f'Successfully imported {success_count} transactions from GPay PDF! {error_count} skipped.', 'success')
    
    except Exception as e:
        flash('Error reading PDF file!', 'danger')
    
    return redirect(url_for('transactions.index'))




def auto_categorize(description, categories):
    # Keywords for each category
    keywords = {
        'Food': ['swiggy', 'zomato', 'restaurant', 'cafe', 'food', 'pizza', 'burger', 'hotel', 'kitchen', 'eat'],
        'Transport': ['uber', 'ola', 'petrol', 'fuel', 'bus', 'train', 'metro', 'auto', 'taxi', 'rapido'],
        'Shopping': ['amazon', 'flipkart', 'myntra', 'mall', 'shop', 'store', 'market', 'meesho'],
        'Entertainment': ['netflix', 'prime', 'hotstar', 'spotify', 'movie', 'theatre', 'game', 'youtube'],
        'Health': ['pharmacy', 'hospital', 'clinic', 'doctor', 'medicine', 'medical', 'apollo', 'lab'],
        'Education': ['udemy', 'coursera', 'college', 'school', 'book', 'course', 'tuition', 'fees'],
        'Bills & Utilities': ['electricity', 'water', 'internet', 'airtel', 'jio', 'bsnl', 'bill', 'recharge', 'vi'],
        'Rent': ['rent', 'landlord', 'pg', 'hostel', 'lease'],
    }
    
    description_lower = description.lower()
    
    # Match description against keywords
    for category in categories:
        category_name = category['name']
        if category_name in keywords:
            for keyword in keywords[category_name]:
                if keyword in description_lower:
                    return category['id']
    
    # If no match found return Other category
    for category in categories:
        if category['name'] == 'Other':
            return category['id']
    
    return None