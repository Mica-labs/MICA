import sqlite3

def submit_info(user_name, items, discount, address, contact):
    # connect to database
    conn = sqlite3.connect('user_info.db')
    cursor = conn.cursor()
    
    # create table (if not exist)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_submission (
        user_name TEXT,
        items TEXT,
        discount REAL,
        address TEXT,
        contact TEXT
    )
    ''')

    # insert data into table
    cursor.execute('''
    INSERT INTO user_submission (user_name, items, discount, address, contact)
    VALUES (?, ?, ?, ?, ?)
    ''', (user_name, items, discount, address, contact))

    # close transaction
    conn.commit()
    conn.close()

    print("Success")
