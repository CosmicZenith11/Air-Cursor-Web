import os
import io
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, make_response
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from pymongo import MongoClient

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'air_cursor_super_secret_key_2026')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

# 💥 MongoDB Cloud Connection Setup 💥
MONGO_URI = os.environ.get('MONGO_URI')
client = None
visitors_collection = None

if MONGO_URI:
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = client['air_cursor_db']
        visitors_collection = db['visitors']
        print("✅ MongoDB Atlas Connected Successfully!")
    except Exception as e:
        print(f"❌ MongoDB Connection Failed: {e}")
else:
    print("⚠️ Warning: MONGO_URI not found in Environment Variables.")

# 💥 Windows PC / Laptop વેરિફિકેશન લોજિક 💥
def is_windows_pc(ua_string):
    if not ua_string:
        return False
    ua = ua_string.lower()
    has_windows = 'windows nt' in ua or 'windows' in ua
    is_blocked_device = any(blocked in ua for blocked in [
        'android', 'iphone', 'ipad', 'ipod', 'mobile',
        'tablet', 'macintosh', 'mac os x', 'mac os', 'linux', 'cros'
    ])
    return has_windows and not is_blocked_device

# 💥 ૧. 403 Forbidden: સર્વર લેવલ પર Mobile, Mac, Tablet બ્લોક 💥
@app.before_request
def enforce_windows_only():
    if request.path.startswith('/static'):
        return None
    ua = request.headers.get('User-Agent', '')
    if not is_windows_pc(ua):
        return render_template(
            'error.html', 
            code="403", 
            title="Desktop Only Experience", 
            message="Air Cursor touchless optical tracking algorithms are strictly optimized for Windows PC & Laptops only. Mobile devices, Tablets, and macOS are blocked."
        ), 403

# 💥 ૨. 404 Not Found: ખોટી URL નાખે ત્યારે 💥
@app.errorhandler(404)
def not_found_error(error):
    return render_template(
        'error.html', 
        code="404", 
        title="Page Not Found", 
        message="The page or link you are trying to access does not exist on Air Cursor platform."
    ), 404

# 💥 ૩. 405 Method Not Allowed: ખોટી HTTP મેથડ રિક્વેસ્ટ પર 💥
@app.errorhandler(405)
def method_not_allowed_error(error):
    return render_template(
        'error.html', 
        code="405", 
        title="Method Not Allowed", 
        message="The HTTP method used for this action is strictly restricted."
    ), 405

# 💥 ૪. 500 Internal Server Error: સર્વર ક્રેશ થાય ત્યારે 💥
@app.errorhandler(500)
def internal_server_error(error):
    return render_template(
        'error.html', 
        code="500", 
        title="Internal Server Error", 
        message="An unexpected system error occurred on our server. Our team is looking into it."
    ), 500

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
        session.permanent = bool(remember)
        session['remember_me'] = bool(remember)
        
        # 💥 ડેટા MongoDB Atlas માં સેવ કરવાનું લોજિક 💥
        if visitors_collection is not None:
            try:
                record = {
                    "name": name.strip(),
                    "email": email.strip(),
                    "remember_me": bool(remember),
                    "user_agent": request.headers.get('User-Agent', ''),
                    "registered_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
                }
                visitors_collection.insert_one(record)
                print(f"✅ User Data Saved to MongoDB: {name} ({email})")
            except Exception as err:
                print(f"❌ Error inserting document to MongoDB: {err}")
        else:
            print("⚠️ MongoDB Collection is not accessible. Check MONGO_URI.")
            
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
    app.run(debug=True)
