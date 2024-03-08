from flask import Flask, request, jsonify
import sqlite3

app = Flask(__name__)

# Connect to SQLite database
conn = sqlite3.connect('bot_database.db')
c = conn.cursor()

# Endpoint to handle verification
@app.route('/verify', methods=['POST'])
def verify():
    data = request.json
    verification_code = data.get('verification_code')

    # Check if the verification code matches the user ID in the database
    user_id = request.cookies.get('user_id')
    c.execute("SELECT * FROM users WHERE user_id=? AND verification_code=?", (user_id, verification_code))
    user = c.fetchone()
    if user:
        # Verification successful
        return jsonify({'verification_successful': True}), 200
    else:
        # Verification failed
        return jsonify({'verification_successful': False}), 401

if __name__ == '__main__':
    app.run(debug=True)  # Run the Flask app
