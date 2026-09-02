import os
import re
import io
from datetime import datetime, timedelta
from bson.objectid import ObjectId
from flask import Flask, render_template, request, redirect, url_for, session, make_response, abort, jsonify
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from pymongo import MongoClient
from werkzeug.exceptions import HTTPException, default_exceptions

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'air_cursor_super_secret_key_2026')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

# =========================================================================
# 💥 ૧. તમારા ગુપ્ત એડમિન ક્રેડેન્શિયલ્સ (STRICT CASE-SENSITIVE) 💥
# આ નામ અને ઈમેઇલ બરાબર આ જ કેસમાં નાખશો તો જ એડમિન ખુલશે
# =========================================================================
ADMIN_SECRET_NAME = os.environ.get('ADMIN_SECRET_NAME', 'Vansh Patel')
ADMIN_SECRET_EMAIL = os.environ.get('ADMIN_SECRET_EMAIL', 'admin@aircursor.com')

# =========================================================
# 💥 ૨. MONGODB ATLAS CLOUD CONNECTION 💥
# =========================================================
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

# =========================================================
# 💥 ૩. ડિવાઇસ સિક્યોરિટી (WINDOWS ONLY) 💥
# =========================================================
def is_windows_pc(ua_string):
    if not ua_string:
        return False
    ua = ua_string.lower()
    has_windows = 'windows nt' in ua or 'windows' in ua
    is_blocked_device = any(blocked in ua for blocked in [
        'android', 'iphone', 'ipad', 'ipod', 'mobile',
        'tablet', 'macintosh', 'mac os x', 'mac os', 'linux', 'cros', 'tizen', 'watch'
    ])
    return has_windows and not is_blocked_device

def sanitize_input(text):
    if not text:
        return ""
    clean = re.sub(r'[<>${}]', '', str(text))
    return clean

@app.before_request
def enforce_security_and_devices():
    if request.path.startswith('/static'):
        return None

    ua = request.headers.get('User-Agent', '')
    if not is_windows_pc(ua):
        abort(403, description="Air Cursor touchless tracking algorithms are strictly engineered for Windows PC & Laptops only. Mobile phones, Tablets, Smart Boards, and macOS are strictly blocked.")

@app.after_request
def add_security_headers(response):
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

# =========================================================
# 💥 ૪. ગ્લોબલ એરર હેન્ડલર (દુનિયાની તમામ એરર્સ માટે) 💥
# =========================================================
@app.errorhandler(HTTPException)
def handle_http_exception(e):
    return render_template(
        'error.html',
        code=e.code,
        title=e.name,
        message=e.description
    ), e.code

@app.errorhandler(Exception)
def handle_generic_server_crash(e):
    return render_template(
        'error.html',
        code=500,
        title="Internal Server Error",
        message="An unexpected system failure occurred on backend server. Our team is inspecting it."
    ), 500

@app.route('/error/<int:code>')
def simulate_error(code):
    if code in default_exceptions:
        abort(code)
    else:
        return render_template(
            'error.html',
            code=code,
            title="Custom Status",
            message=f"HTTP Code {code} is experimental or non-standard."
        ), 400

# =========================================================
# 💥 ૫. મુખ્ય વેબસાઇટ અને હિડન એડમિન ગેટવે લોજિક 💥
# =========================================================
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    # અહી કોઈ strip() કે lower() નથી વાપર્યું જેથી કેપિટલ-સ્મોલ અક્ષરો એક્ઝેક્ટ મેચ થાય
    raw_name = request.form.get('name', '')
    raw_email = request.form.get('email', '')
    remember = request.form.get('remember')

    # 🕵️‍♂️ ૧. સ્ટીલ્થ ચેક: જો એક્ઝેક્ટ એડમિન નામ અને ઈમેઇલ નાખવામાં આવે તો
    if raw_name == ADMIN_SECRET_NAME and raw_email == ADMIN_SECRET_EMAIL:
        session['is_admin_authenticated'] = True
        # આ ડેટાબેઝમાં એન્ટર નહીં થાય અને સીધા એડમિન પેનલ પર મોકલી દેશે
        return redirect(url_for('admin_panel'))

    # 👤 ૨. નોર્મલ યુઝર સબમિશન
    name = sanitize_input(raw_name).strip()
    email = sanitize_input(raw_email).strip()

    if not name or not email or '@' not in email:
        abort(400, description="Invalid form submission. Full Name and Email are required.")

    session['user_registered'] = True
    session['user_name'] = name
    session.permanent = bool(remember)
    session['remember_me'] = bool(remember)

    if visitors_collection is not None:
        try:
            record = {
                "name": name,
                "email": email,
                "remember_me": bool(remember),
                "user_agent": request.headers.get('User-Agent', ''),
                "registered_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            }
            visitors_collection.insert_one(record)
            print(f"✅ Normal User Stored: {name}")
        except Exception as err:
            print(f"❌ Storage Failed: {err}")

    return redirect(url_for('download_page'))

# =========================================================
# 💥 ૬. છૂપું એડમિન પેનલ (ડાયરેક્ટ URL ખોલવા પર 404 આપશે) 💥
# =========================================================
@app.route('/admin')
def admin_panel():
    # જો કોઈ સીધું URL લખીને આવશે, તો તેને એવું જ લાગશે કે આવું કોઈ પેજ જ નથી (404 Not Found)
    if not session.get('is_admin_authenticated'):
        abort(404)

    records = []
    if visitors_collection is not None:
        records = list(visitors_collection.find().sort('_id', -1))

    return render_template('admin.html', visitors=records)

@app.route('/admin/delete/<id>')
def admin_delete(id):
    if not session.get('is_admin_authenticated'):
        abort(404)
    if visitors_collection is not None:
        visitors_collection.delete_one({'_id': ObjectId(id)})
    return redirect(url_for('admin_panel'))

@app.route('/admin/logout')
def admin_logout():
    session.pop('is_admin_authenticated', None)
    return redirect(url_for('home'))

# 🚀 REST API (App સપોર્ટ માટે)
@app.route('/api/admin/visitors')
def api_get_visitors():
    if not session.get('is_admin_authenticated'):
        return jsonify({"status": "error", "message": "Resource Not Found"}), 404

    data = []
    if visitors_collection is not None:
        for v in visitors_collection.find().sort('_id', -1):
            data.append({
                "id": str(v['_id']),
                "name": v.get('name'),
                "email": v.get('email'),
                "registered_at": v.get('registered_at'),
                "user_agent": v.get('user_agent')
            })
    return jsonify({"status": "success", "count": len(data), "visitors": data})

# =========================================================
# 💥 ૭. ડાઉનલોડ અને પીડીએફ રૂટ્સ 💥
# =========================================================
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
