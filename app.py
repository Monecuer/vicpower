from flask import Flask, render_template, request
import qrcode
import os
import sqlite3
import uuid
from itsdangerous import Signer

app = Flask(__name__)
signer = Signer("your-secret-key")

# Ensure folders and database exist
os.makedirs("static/qr", exist_ok=True)
if not os.path.exists("tickets.db"):
    conn = sqlite3.connect("tickets.db")
    conn.execute('CREATE TABLE IF NOT EXISTS tickets (event TEXT, code TEXT, status TEXT)')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_qr():
    event = request.form['event']
    code = str(uuid.uuid4())
    token = signer.sign(code).decode()

    # Save to database
    conn = sqlite3.connect('tickets.db')
    conn.execute('INSERT INTO tickets (event, code, status) VALUES (?, ?, ?)', (event, token, 'pending'))
    conn.commit()
    conn.close()

    # Generate and save QR
    filename = f"{token}.png"
    filepath = os.path.join("static", "qr", filename)
    img = qrcode.make(token)
    img.save(filepath)

    return render_template('generate_success.html', token=token, qr_path=filepath)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
