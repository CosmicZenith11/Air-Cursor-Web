import os
import io
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, make_response, abort
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from pymongo import MongoClient
from werkzeug.exceptions import HTTPException, default_exceptions

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'air_cursor_super_secret_key_2026')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

# ==========================================
# 💥 ૧. MONGODB ATLAS CLOUD CONNECTION 💥
# ==========================================
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

# ==========================================
# 💥 ૨. DEVICE SECURITY (WINDOWS ONLY) 💥
# ==========================================
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

# બિફોર રિક્વેસ્ટ: નોન-વિન્ડોઝ ડિવાઇસને 403 Forbidden આપવું
@app.before_request
def enforce_windows_only():
    if request.path.startswith('/static'):
        return None
    
    # લાઇવ ટેસ્ટિંગ રૂટ માટે ડિવાઇસ ચેક બાયપાસ રાખવું જેથી ટેસ્ટ કરી શકાય
    if request.path.startswith('/error/'):
        return None

    ua = request.headers.get('User-Agent', '')
    if not is_windows_pc(ua):
        abort(403, description="Air Cursor touchless optical tracking algorithms are strictly optimized for Windows PC & Laptops only. Mobile devices, Tablets, and macOS are blocked.")

# =========================================================
# 💥 ૩. ગ્લોબલ એરર હેન્ડલર (દુનિયાની તમામ ૪૦+ એરર્સ માટે) 💥
# =========================================================
@app.errorhandler(HTTPException)
def handle_http_exception(e):
    """
    દુનિયાના તમામ સ્ટાન્ડર્ડ HTTP કોડ્સ (400 થી 505) ને પકડીને
    તમારા પ્રીમિયમ error.html પેજમાં ડાયનેમિકલી મોકલે છે.
    """
    return render_template(
        'error.html',
        code=e.code,
        title=e.name,
        message=e.description
    ), e.code

@app.errorhandler(Exception)
def handle_generic_server_crash(e):
    """
    જો કોઈ અણધારી ગંભીર સિસ્ટમ ભૂલ થાય તો 500 પેજ બતાવશે.
    """
    return render_template(
        'error.html',
        code=500,
        title="Internal Server Error",
        message="An unexpected system failure occurred on our backend server. Our team is inspecting it."
    ), 500

# ==========================================
# 💥 ૪. સ્પેશિયલ ટેસ્ટિંગ રૂટ (ALL ERRORS DEMO) 💥
# ==========================================
@app.route('/error/<int:code>')
def simulate_error(code):
    """
    કોઈપણ એરર ટેસ્ટ કરવા માટે: દા.ત. /error/400, /error/418, /error/429, /error/503
    """
    if code in default_exceptions:
        abort(code)
    else:
        # જો કોઈ અસ્તિત્વમાં ન હોય તેવો કોડ નાખે (જેમ કે 365)
        return render_template(
            'error.html',
            code=code,
            title="Custom / Non-Standard Status",
            message=f"HTTP Code {code} is either experimental or not recognized by standard IETF web protocols."
        ), 400

# ==========================================
# 💥 ૫. મુખ્ય એપ્લિકેશન રૂટ્સ 💥
# ==========================================
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    name = request.form.get('name')
    email = request.form.get('email')
    remember = request.form.get('remember')
    
    # 400 Bad Request: જો નામ કે ઈમેઈલ ખાલી હોય તો
    if not name or not email:
        abort(400, description="Invalid form submission. Full Name and Email ID are mandatory fields.")

    session['user_registered'] = True
    session['user_name'] = name
    session.permanent = bool(remember)
    session['remember_me'] = bool(remember)
    
    # MongoDB Atlas માં ડેટા સ્ટોર કરવો
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
        
    return redirect(url_for('download_page'))

@app.route('/download')
def download_page():
    # 401 Unauthorized: જો યુઝર રજીસ્ટર કર્યા વગર સીધો પેજ ખોલવા જાય
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
