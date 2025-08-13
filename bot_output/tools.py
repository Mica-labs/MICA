import sqlite3
import subprocess
import random

def submit_info(user_name, month, amount):
    # connect to database
    conn = sqlite3.connect('billing_info.db')
    cursor = conn.cursor()
    
    # create table (if not exist)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_submission (
        user_name TEXT,
        month TEXT,
        amount REAL
    )
    ''')

    # insert data into table
    cursor.execute('''
    INSERT INTO user_submission (user_name, month, amount)
    VALUES (?, ?, ?)
    ''', (user_name, month, amount))

    # close transaction
    conn.commit()
    conn.close()

    print("Success")

def query_bill(user_name, month):
    conn = sqlite3.connect('biling_info.db')
    cursor = conn.cursor()

    results = cursor.execute(('''
    SELECT amount FROM user_submission WHERE user_name='{user}' AND month='{mon}'
    ''').format(user='guest', mon='January')).fetchall()
    print(results)
    amt = 0
    for res in results:
        amt += res[0]

    return [{"arg":"amount", "value": amt}]

def run_diagnostic():
    #out = subprocess.run(['ping', 'google.com'], capture_output=True)
    #out_text = out.stdout.decode().split()
    #return out_text[len(out_text)-1][1:]
    speed = random.randint(50,150)
    print(f"The speed is {speed}")
    return [{"arg": "speed", "value": speed}] #just simulating it for now