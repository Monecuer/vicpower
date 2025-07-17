import os
import sqlite3
from flask import Flask, render_template, request, jsonify
import qrcode
import uuid
import hmac
import hashlib

app = Flask(__name__)

DATABASE = 'database.db'
SECRET_KEY = b'your-very-secret-key'  # Change this to a secure secret!

# Initialize or reset database (deletes old DB to avoid schema conflicts)
def init_db():
    if os.path.exists(DATABASE):
        os.remove(DATABASE)
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE tickets (
            id TEXT PRIMARY KEY,
            event TEXT NOT NULL,
            status TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Generate HMAC signature for data integrity
def generate_signature(data):
    return hmac.new(SECRET_KEY, data.encode(), hashlib.sha256).hexdigest()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_ticket():
    event = request.form['event']
    ticket_id = str(uuid.uuid4())
    signature = generate_signature(ticket_id)
    qr_data = f"{ticket_id}:{signature}"

    os.makedirs('static/qr', exist_ok=True)
    qr = qrcode.make(qr_data)
    qr_path = f'static/qr/{ticket_id}.png'
    qr.save(qr_path)

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("INSERT INTO tickets (id, event, status) VALUES (?, ?, ?)", (ticket_id, event, 'pending'))
    conn.commit()
    conn.close()

    return render_template('ticket.html', event=event, ticket_id=ticket_id, qr_path=qr_path)

@app.route('/verify-ticket', methods=['POST'])
def verify_ticket():
    data = request.json.get('data')
    if not data or ':' not in data:
        return jsonify(valid=False, message="Invalid QR data")

    ticket_id, signature = data.split(':', 1)
    expected_signature = generate_signature(ticket_id)

    if not hmac.compare_digest(expected_signature, signature):
        return jsonify(valid=False, message="Signature mismatch")

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT event, status FROM tickets WHERE id=?", (ticket_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        return jsonify(valid=False, message="Ticket not found")

    event, status = row

    if status == 'pending':
        # Mark ticket as approved on first verification
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("UPDATE tickets SET status='approved' WHERE id=?", (ticket_id,))
        conn.commit()
        conn.close()
        status = 'approved'

    return jsonify(valid=True, event=event, status=status)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
