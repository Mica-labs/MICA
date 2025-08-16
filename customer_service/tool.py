import sqlite3
from datetime import datetime, timedelta

def check_order_available(order_id):
    # Connect to the database
    conn = sqlite3.connect('your_database.db')
    cursor = conn.cursor()
    
    # Get the current date and the date 30 days ago
    current_date = datetime.now()
    thirty_days_ago = current_date - timedelta(days=30)
    
    # Convert the date 30 days ago to string format (assuming 'YYYY-MM-DD' format in the database)
    thirty_days_ago_str = thirty_days_ago.strftime('%Y-%m-%d')
    
    # Query the order's date from the database
    cursor.execute("SELECT order_date FROM orders WHERE order_id = ?", (order_id,))
    order = cursor.fetchone()
    
    # Close the database connection
    conn.close()
    
    if order:
        order_date_str = order[0]  # Get the order date from the query result
        order_date = datetime.strptime(order_date_str, '%Y-%m-%d')  # Convert the date to a datetime object
        
        # Check if the order is within the last 30 days
        if order_date >= thirty_days_ago:
            print("The order is within 30 days")
        else:
            print("The order is older than 30 days")
    else:
        print("The order does not exist")
