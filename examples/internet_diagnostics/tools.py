import sqlite3
import subprocess
import random

def query_bill(user_name, month):
    conn = sqlite3.connect('billing_info.db')
    cursor = conn.cursor()

    results = cursor.execute(('''
    SELECT amount FROM user_submission WHERE user_name='{user}' AND month='{mon}'
    ''').format(user=user_name, mon=month)).fetchall()
    print(results)
    amt = 0
    for res in results:
        amt += res[0]
    print(f"The amount is {amt} for month {month}")
    return [{"arg":"amount", "value": amt}]

def bill_breakdown(user_name, month):
    conn = sqlite3.connect('billing_info.db')
    cursor = conn.cursor()

    results = cursor.execute(('''
    SELECT amount FROM user_submission WHERE user_name='{user}' AND month='{mon}'
    ''').format(user=user_name, mon=month)).fetchall()
    print(results)
    print("bill_breakdown successfully called\n")
    return [{"arg":"results", "value": results}]

def run_diagnostic():
    #out = subprocess.run(['ping', 'google.com'], capture_output=True)
    #out_text = out.stdout.decode().split()
    #speed = out_text[len(out_text)-1][1:]
    speed = random.randint(50,150)
    print(f"The speed is {speed}")
    return [{"arg": "speed", "value": speed}] #just simulating it for now
