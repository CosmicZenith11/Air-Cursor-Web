import os
import sqlite3
import io
from datetime import timedelta
from flask import Flask, render_template, request, redirect, url_for, session, make_response
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors

app = Flask(__name__)
app.secret_key = 'air_cursor_super_secret_key_2026'

app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
DB_PATH = os.path.join(app.root_path, 'users.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS visitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# 💥 સર્વર-સાઇડ ડિવાઇસ વેરિફિકેશન (માત્ર Windows PC / Laptop જ પાસ થશે) 💥
def is_windows_pc(ua_string):
    if not ua_string:
        return False
    ua = ua_string.lower()
    
    # Windows હોવું ફરજિયાત છે
    has_windows = 'windows nt' in ua or 'windows' in ua
    
    # Mobile, Tablet, Mac, Linux, Android, iOS હોવું ન જોઈએ
    is_blocked_device = any(blocked in ua for blocked in [
        'android', 'iphone', 'ipad', 'ipod', 'mobile',
        'tablet', 'macintosh', 'mac os x', 'mac os', 'linux', 'cros'
    ])
    
    return has_windows and not is_blocked_device

# 💥 અસલ સિક્યોરિટી ગાર્ડ: સર્વર લેવલ પર અન્ય ડિવાઇસને અટકાવશે 💥
@app.before_request
def enforce_windows_only():
    # સ્ટેટિક ફાઇલો (CSS/Icons) ને બ્લોક ન કરવી
    if request.path.startswith('/static'):
        return None

    ua = request.headers.get('User-Agent', '')
    if not is_windows_pc(ua):
        # સર્વર અસલ પેજનો HTML મોકલશે જ નહીં, જેથી Inspect Element થી પણ બાયપાસ ન થાય
        return render_template('blocked.html'), 403

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    name = request.form.get('name')
    email = request.form.get('email')
    remember = request.form.get('remember')
    
    if name and email:
        session['user_registered'] = True
        session['user_name'] = name
        
        if remember:
            session.permanent = True
            session['remember_me'] = True
        else:
            session.permanent = False
            session['remember_me'] = False
        
        init_db()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO visitors (name, email) VALUES (?, ?)", (name, email))
        conn.commit()
        conn.close()
        
    return redirect(url_for('download_page'))

@app.route('/download')
def download_page():
    if not session.get('user_registered'):
        return redirect(url_for('home', action='download_click'))
    return render_template('download.html')

@app.route('/reset-session')
def reset_session():
    if not session.get('remember_me'):
        session.clear()
    return redirect(url_for('home'))

@app.route('/download-pdf')
def download_pdf():
    if not session.get('user_registered'):
        return redirect(url_for('home', action='download_click'))
    
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    p.setFillColor(colors.HexColor("#03071e"))
    p.rect(0, height - 130, width, 130, fill=1, stroke=0)

    logo_path = os.path.join(app.root_path, 'static', 'favicon.png')
    text_x = 45
    
    if os.path.exists(logo_path):
        p.drawImage(logo_path, 40, height - 100, width=65, height=65, preserveAspectRatio=True, mask='auto')
        text_x = 120

    p.setFillColor(colors.HexColor("#00e5ff"))
    p.setFont("Helvetica-Bold", 26)
    p.drawString(text_x, height - 60, "AIR CURSOR")

    p.setFillColor(colors.HexColor("#ffffff"))
    p.setFont("Helvetica-Bold", 13)
    p.drawString(text_x, height - 85, "Behind Touch")

    p.setFillColor(colors.HexColor("#0f172a"))
    p.setFont("Helvetica-Bold", 20)
    p.drawString(45, height - 180, "Thank You For Downloading!")

    user_name = session.get('user_name', 'Valued User')
    p.setFont("Helvetica", 12)
    p.setFillColor(colors.HexColor("#334155"))
    p.drawString(45, height - 215, f"Hello {user_name}, your Air Cursor installer package is ready.")
    p.drawString(45, height - 238, "We are thrilled to transform how you interact with your desktop instantly.")

    p.setFillColor(colors.HexColor("#f8fafc"))
    p.setStrokeColor(colors.HexColor("#00e5ff"))
    p.setLineWidth(1)
    p.roundRect(45, height - 365, width - 90, 95, 10, fill=1, stroke=1)

    p.setFillColor(colors.HexColor("#0f172a"))
    p.setFont("Helvetica-Bold", 12)
    p.drawString(65, height - 295, "License & Session Details:")

    p.setFont("Helvetica", 10.5)
    p.setFillColor(colors.HexColor("#475569"))
    p.drawString(65, height - 322, "• Product Version: Air Cursor Desktop Client v1.0 (Enterprise)")
    p.drawString(65, height - 344, "• Status: Authenticated & Secure Session Active")

    p.setStrokeColor(colors.HexColor("#e2e8f0"))
    p.setLineWidth(0.8)
    p.line(45, 65, width - 45, 65)

    p.setFillColor(colors.HexColor("#64748b"))
    p.setFont("Helvetica", 9)
    p.drawString(45, 45, "© 2026 Air Cursor Technologies. All rights reserved.")
    
    p.setFillColor(colors.HexColor("#0077ff"))
    p.setFont("Helvetica-Bold", 9.5)
    p.drawRightString(width - 45, 45, "Powered By:- Developer Mode")

    p.showPage()
    p.save()

    buffer.seek(0)
    response = make_response(buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=AirCursor.pdf'
    return response

if __name__ == '__main__':
    init_db()
    app.run(debug=True)