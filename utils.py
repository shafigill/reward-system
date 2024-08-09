import sqlite3

def create_users_table():
    conn = sqlite3.connect('rewards.db')  # or whatever your database name is
    cursor = conn.cursor()

    # Create table
    cursor.execute('''
    drop table users;
    ''')

    # Commit and close the connection
    conn.commit()
    conn.close()

# Call the function to create the table
create_users_table()
