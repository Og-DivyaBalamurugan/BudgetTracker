# app/ml_model.py
import numpy as np
from sklearn.linear_model import LinearRegression

def predict_next_month(spending_history):
    """
    Takes a list of monthly spending amounts and
    predicts the next month's spending using Linear Regression.
    
    Example input: [3000, 3500, 2800, 4000, 3200, 3800]
    Example output: 3600.0 (predicted next month)
    """
    
    # Need at least 2 months of data to make a prediction
    if len(spending_history) < 2:
        return None
    
    # X = month numbers [1, 2, 3, 4, 5, 6]
    # Y = spending amounts for each month
    X = np.array(range(1, len(spending_history) + 1)).reshape(-1, 1)
    y = np.array(spending_history)
    
    # Train the Linear Regression model
    model = LinearRegression()
    model.fit(X, y)
    
    # Predict for next month
    next_month = np.array([[len(spending_history) + 1]])
    prediction = model.predict(next_month)[0]
    
    # Never predict negative spending
    return max(0, round(float(prediction), 2))


def get_predictions_for_user(cursor, user_id):
    """
    Gets spending history per category for a user
    and returns predictions for next month.
    """
    
    # Get all categories
    cursor.execute("SELECT * FROM categories")
    categories = cursor.fetchall()
    
    predictions = []
    
    for category in categories:
        # Get last 6 months spending for this category
        cursor.execute("""
            SELECT 
                DATE_FORMAT(date, '%%Y-%%m') as month,
                SUM(amount) as total
            FROM transactions
            WHERE user_id = %s 
            AND category_id = %s
            AND type = 'expense'
            AND date >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
            GROUP BY DATE_FORMAT(date, '%%Y-%%m')
            ORDER BY month ASC
        """, (user_id, category['id']))
        
        monthly_data = cursor.fetchall()
        
        # Only predict if we have spending history
        if len(monthly_data) >= 2:
            spending_history = [float(m['total']) for m in monthly_data]
            predicted_amount = predict_next_month(spending_history)
            
            if predicted_amount and predicted_amount > 0:
                predictions.append({
                    'category_id': category['id'],
                    'category_name': category['name'],
                    'category_icon': category['icon'],
                    'predicted_amount': predicted_amount,
                    'months_of_data': len(monthly_data),
                    'avg_spending': round(sum(spending_history) / len(spending_history), 2)
                })
    
    return predictions