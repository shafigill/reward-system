from flask import Flask, render_template, request, jsonify
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)

# Function to initialize the database and create the users table if it doesn't exist
def init_db():
    conn = sqlite3.connect('rewards.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        streak INTEGER NOT NULL,
        total_mbs INTEGER NOT NULL,
        last_claim_time TIMESTAMP,
        next_enable_time TIMESTAMP
    )
    ''')
    conn.commit()
    conn.close()

# Function to get a new database connection
def get_db_connection():
    conn = sqlite3.connect('rewards.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_user_data', methods=['POST'])
def get_user_data():
    user_id = request.json.get('user_id')
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()

    if user is None:
        # Initialize new user data if not found
        current_time = datetime.now()
        cursor.execute('INSERT INTO users (user_id, streak, total_mbs, last_claim_time, next_enable_time) VALUES (?, ?, ?, ?, ?)',
                       (user_id, 0, 0, current_time, current_time))
        conn.commit()
        user = {'streak': 0, 'total_mbs': 0, 'last_claim_time': current_time.isoformat(), 'next_enable_time': current_time.isoformat()}
    else:
        user = dict(user)
        now = datetime.now()
        next_enable_time = datetime.fromisoformat(user['next_enable_time'])

        # Check if the user missed the claim window
        if now > next_enable_time + timedelta(minutes=2) and user['streak'] > 0:
            user['streak'] = 0
            cursor.execute('UPDATE users SET streak = ?, last_claim_time = ?, next_enable_time = ? WHERE user_id = ?',
                           (0, now, now, user_id))
            conn.commit()

        user['next_enable_time'] = next_enable_time.isoformat()

    conn.close()
    return jsonify(user)

@app.route('/claim_reward', methods=['POST'])
def claim_reward():
    user_id = request.json.get('user_id')
    day = request.json.get('day')

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()

    if user is None:
        return jsonify({'error': 'User not found'})

    user = dict(user)
    now = datetime.now()
    next_enable_time = datetime.fromisoformat(user['next_enable_time'])

    # Ensure the button is enabled and user claims within the allowed time
    if day != user['streak'] + 1 or now < next_enable_time:
        conn.close()
        return jsonify({'error': 'Reward not available yet or you missed your claim window.'})

    new_streak = user['streak'] + 1
    new_total_mbs = user['total_mbs'] + (25 + (day - 1) * 5)

    # Determine the next button enable time
    new_next_enable_time = now + timedelta(minutes=2)

    if new_streak >= 7:
        new_streak = 0  # Reset after Day 7
        new_next_enable_time = now + timedelta(minutes=2)  # Reset to allow Day 1

    cursor.execute('UPDATE users SET streak = ?, total_mbs = ?, last_claim_time = ?, next_enable_time = ? WHERE user_id = ?',
                   (new_streak, new_total_mbs, now, new_next_enable_time, user_id))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'new_streak': new_streak, 'new_total_mbs': new_total_mbs, 'next_enable_time': new_next_enable_time.isoformat()})

if __name__ == '__main__':
    init_db()  # Initialize the database when the app starts
    app.run(debug=True)
