import os
import re
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
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
# 💥 ૧. MAIN ADMIN & MASTER PASSCODE કન્ફિગરેશન 💥
# =========================================================================
MASTER_PASSCODE = os.environ.get('MASTER_PASSCODE', '998877')  # પ્રોફાઇલ બદલવાનો ગુપ્ત પાસકોડ
DEFAULT_MAIN_NAME = os.environ.get('MAIN_ADMIN_NAME', 'Vansh Patel')
DEFAULT_MAIN_EMAIL = os.environ.get('MAIN_ADMIN_EMAIL', 'admin@aircursor.com')

# SMTP સેટિંગ્સ (Gmail Notification મોકલવા માટે)
SMTP_EMAIL = os.environ.get('SMTP_EMAIL', 'your_email@gmail.com')
SMTP_APP_PASSWORD = os.environ.get('SMTP_APP_PASSWORD', '') # Gmail App Password

# =========================================================
# 💥 ૨. MONGODB ATLAS CONNECTION 💥
# =========================================================
MONGO_URI = os.environ.get('MONGO_URI')
client = None
db = None
visitors_collection = None
subadmins_collection = None
config_collection = None

if MONGO_URI:
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = client['air_cursor_db']
        visitors_collection = db['visitors']
        subadmins_collection = db['sub_admins']
        config_collection = db['system_config']
        
        # Main Admin ના ડાયનેમિક ક્રેડેન્શિયલ્સ DB માં ચેક કરવા
        if config_collection.count_documents({"type": "main_admin"}) == 0:
            config_collection.insert_one({
                "type": "main_admin",
                "name": DEFAULT_MAIN_NAME,
                "email": DEFAULT_MAIN_EMAIL
            })
        print("✅ MongoDB Atlas Configured Successfully!")
    except Exception as e:
        print(f"❌ DB Connection Failed: {e}")

def get_main_admin():
    if config_collection is not None:
        rec = config_collection.find_one({"type": "main_admin"})
        if rec:
            return rec.get("name", DEFAULT_MAIN_NAME), rec.get("email", DEFAULT_MAIN_EMAIL)
    return DEFAULT_MAIN_NAME, DEFAULT_MAIN_EMAIL

# =========================================================
# 💥 ૩. EMAIL DISPATCH ENGINE (LIVE NOTIFICATIONS) 💥
# =========================================================
def send_approval_email(subadmin_name, subadmin_email, action_name, perm_key, subadmin_id):
    if not SMTP_APP_PASSWORD or not SMTP_EMAIL:
        print(f"⚠️ SMTP not configured. Simulating Email for {subadmin_name} requesting {action_name}")
        return False
    
    main_name, main_email = get_main_admin()
    app_base_url = "https://air-cursor-nd6r.onrender.com"
    accept_url = f"{app_base_url}/admin/grant-permission?sub_id={subadmin_id}&perm={perm_key}&passcode={MASTER_PASSCODE}"
    
    msg = MIMEMultipart("alternative")
    msg['Subject'] = f"🛡️ [Air Cursor Security] Sub-Admin Access Request: {action_name}"
    msg['From'] = f"Air Cursor Command <{SMTP_EMAIL}>"
    msg['To'] = main_email

    html_content = f"""
    <html>
    <body style="font-family:sans-serif; background:#141517; color:#E6E4E0; padding:30px;">
        <div style="background:#1c1d22; border:1px solid #C5A880; border-radius:16px; padding:25px; max-width:550px; margin:auto;">
            <h2 style="color:#C5A880; margin-top:0;">Permission Request Alert</h2>
            <p>Hello <b>{main_name}</b>,</p>
            <p>Sub-Admin <b>{subadmin_name}</b> (<code>{subadmin_email}</code>) attempted to execute a restricted action:</p>
            <div style="background:#0f1013; padding:15px; border-radius:8px; margin:15px 0; border-left:4px solid #ff4757;">
                <b style="color:#fff;">Requested Action:</b> {action_name} ({perm_key})
            </div>
            <p>Do you want to grant this permission permanently to this Sub-Admin?</p>
            <div style="margin-top:25px; display:flex; gap:15px;">
                <a href="{accept_url}" style="background:#2ed573; color:#fff; text-decoration:none; padding:12px 24px; border-radius:8px; font-weight:bold;">Accept & Grant</a>
                &nbsp;&nbsp;
                <span style="color:#888; font-size:0.9rem; padding:12px;">(Ignore this email to deny)</span>
            </div>
        </div>
    </body>
    </html>
    """
    msg.attach(MIMEText(html_content, "html"))
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(SMTP_EMAIL, SMTP_APP_PASSWORD)
        server.sendmail(SMTP_EMAIL, main_email, msg.as_string())
        server.quit()
        print(f"✅ Notification Email Dispatched to {main_email}")
        return True
    except Exception as e:
        print(f"❌ Failed sending email: {e}")
        return False

# =========================================================
# 💥 ૪. DEVICE & BROWSER SECURITY (WINDOWS ONLY) 💥
# =========================================================
def is_windows_pc(ua_string):
    if not ua_string:
        return False
    ua = ua_string.lower()
    has_windows = 'windows nt' in ua or 'windows' in ua
    is_blocked = any(blocked in ua for blocked in [
        'android', 'iphone', 'ipad', 'ipod', 'mobile',
        'tablet', 'macintosh', 'mac os x', 'mac os', 'linux', 'cros', 'tizen', 'watch'
    ])
    return has_windows and not is_blocked

@app.before_request
def enforce_security():
    if request.path.startswith('/static') or request.path.startswith('/error/'):
        return None
    
    ua = request.headers.get('User-Agent', '')
    if not is_windows_pc(ua):
        abort(403, description="Air Cursor is strictly engineered for Windows PC & Laptops only. Other devices are restricted.")

# =========================================================
# 💥 ૫. STEALTH LOGIN / HONEYPOT GATEWAY 💥
# =========================================================
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    raw_name = request.form.get('name', '').strip()
    raw_email = request.form.get('email', '').strip()
    remember = request.form.get('remember')

    main_name, main_email = get_main_admin()

    # ૧. Main Admin Check (Exact Case Match)
    if raw_name == main_name and raw_email == main_email:
        session['user_role'] = 'main_admin'
        session['admin_authenticated'] = True
        return redirect(url_for('main_admin_dashboard'))

    # ૨. Sub-Admin Check
    if subadmins_collection is not None:
        sub = subadmins_collection.find_one({"name": raw_name, "email": raw_email})
        if sub:
            session['user_role'] = 'sub_admin'
            session['subadmin_id'] = str(sub['_id'])
            session['subadmin_name'] = sub['name']
            session['subadmin_email'] = sub['email']
            return redirect(url_for('subadmin_dashboard'))

    # ૩. Normal User Lead
    if not raw_name or not raw_email or '@' not in raw_email:
        abort(400, description="Name and Valid Email are required.")

    session['user_registered'] = True
    session['user_name'] = raw_name
    session.permanent = bool(remember)
    session['remember_me'] = bool(remember)

    if visitors_collection is not None:
        visitors_collection.insert_one({
            "name": raw_name,
            "email": raw_email,
            "remember_me": bool(remember),
            "user_agent": request.headers.get('User-Agent', ''),
            "registered_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        })

    return redirect(url_for('download_page'))

# =========================================================
# 💥 ૬. MAIN ADMIN DASHBOARD & CONTROLS 💥
# =========================================================
@app.route('/admin')
@app.route('/admin/master')
def main_admin_dashboard():
    if session.get('user_role') != 'main_admin':
        abort(404) # સીધું ખોલવા પર 404 Not Found

    visitors = list(visitors_collection.find().sort('_id', -1)) if visitors_collection is not None else []
    sub_admins = list(subadmins_collection.find().sort('_id', -1)) if subadmins_collection is not None else []
    main_name, main_email = get_main_admin()

    return render_template('admin_master.html', visitors=visitors, sub_admins=sub_admins, main_name=main_name, main_email=main_email)

# Sub-Admin ઉમેરવો
@app.route('/admin/create-subadmin', methods=['POST'])
def create_subadmin():
    if session.get('user_role') != 'main_admin':
        abort(404)
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    
    if subadmins_collection is not None and name and email:
        subadmins_collection.insert_one({
            "name": name,
            "email": email,
            "can_view_visitors": bool(request.form.get('can_view_visitors')),
            "can_delete_visitors": bool(request.form.get('can_delete_visitors')),
            "can_export_data": bool(request.form.get('can_export_data')),
            "created_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        })
    return redirect(url_for('main_admin_dashboard'))

# Sub-Admin રિમૂવ કરવો
@app.route('/admin/remove-subadmin/<id>')
def remove_subadmin(id):
    if session.get('user_role') != 'main_admin':
        abort(404)
    if subadmins_collection is not None:
        subadmins_collection.delete_one({"_id": ObjectId(id)})
    return redirect(url_for('main_admin_dashboard'))

# Main Admin ના ક્રેડેન્શિયલ્સ બદલવા (Passcode Protected)
@app.route('/admin/update-credentials', methods=['POST'])
def update_credentials():
    if session.get('user_role') != 'main_admin':
        abort(404)
    passcode = request.form.get('passcode')
    new_name = request.form.get('new_name', '').strip()
    new_email = request.form.get('new_email', '').strip()

    if passcode != MASTER_PASSCODE:
        abort(403, description="Access Denied: Invalid Master Passcode!")

    if config_collection is not None and new_name and new_email:
        config_collection.update_one(
            {"type": "main_admin"},
            {"$set": {"name": new_name, "email": new_email}},
            upsert=True
        )
    return redirect(url_for('main_admin_dashboard'))

# Lead ડિલીટ કરવી
@app.route('/admin/delete-lead/<id>')
def delete_lead(id):
    # Main Admin અથવા Permission ધરાવતો Sub-Admin
    is_main = session.get('user_role') == 'main_admin'
    is_sub_allowed = False
    if session.get('user_role') == 'sub_admin' and subadmins_collection is not None:
        sub = subadmins_collection.find_one({"_id": ObjectId(session.get('subadmin_id'))})
        if sub and sub.get('can_delete_visitors'):
            is_sub_allowed = True

    if not is_main and not is_sub_allowed:
        abort(403, description="Action Prohibited without privileges.")

    if visitors_collection is not None:
        visitors_collection.delete_one({"_id": ObjectId(id)})

    return redirect(request.referrer or url_for('home'))

# મેઇલમાંથી પરમિશન સ્વીકારવાની લિંક
@app.route('/admin/grant-permission')
def grant_permission():
    sub_id = request.args.get('sub_id')
    perm = request.args.get('perm')
    passcode = request.args.get('passcode')

    if passcode != MASTER_PASSCODE or not sub_id or not perm:
        abort(403, description="Invalid authorization token.")

    if subadmins_collection is not None:
        subadmins_collection.update_one(
            {"_id": ObjectId(sub_id)},
            {"$set": {perm: True}}
        )
    return render_template('error.html', code="200", title="Permission Granted", message=f"Permission '{perm}' successfully granted to Sub-Admin.")

# =========================================================
# 💥 ૭. SUB-ADMIN WORKSPACE & EMAIL REQUEST ROUTE 💥
# =========================================================
@app.route('/subadmin')
def subadmin_dashboard():
    if session.get('user_role') != 'sub_admin':
        abort(404)

    sub_id = session.get('subadmin_id')
    sub_info = subadmins_collection.find_one({"_id": ObjectId(sub_id)}) if subadmins_collection is not None else None
    
    if not sub_info:
        session.clear()
        abort(404)

    visitors = []
    if sub_info.get('can_view_visitors') and visitors_collection is not None:
        visitors = list(visitors_collection.find().sort('_id', -1))

    return render_template('subadmin.html', subadmin_info=sub_info, visitors=visitors)

# સબ-એડમિન જ્યારે પરમિશન વગરની વસ્તુ પર ક્લિક કરે ત્યારે મેઇલ મોકલવો
@app.route('/subadmin/request-permission', methods=['POST'])
def request_permission():
    if session.get('user_role') != 'sub_admin':
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    
    data = request.get_json()
    action_name = data.get('action')
    perm_key = data.get('permission_key')
    sub_id = session.get('subadmin_id')
    sub_name = session.get('subadmin_name')
    sub_email = session.get('subadmin_email')

    # ઈમેઈલ મોકલવો
    sent = send_approval_email(sub_name, sub_email, action_name, perm_key, sub_id)
    if sent:
        return jsonify({"status": "success", "message": f"Request sent to Main Admin's email! Awaiting approval."})
    else:
        return jsonify({"status": "logged", "message": f"Request registered. Main Admin will review on dashboard."})

@app.route('/admin/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# =========================================================
# 💥 ૮. ડાઉનલોડ & એરર હેન્ડલિંગ 💥
# =========================================================
@app.errorhandler(HTTPException)
def handle_http_exception(e):
    return render_template('error.html', code=e.code, title=e.name, message=e.description), e.code

@app.errorhandler(Exception)
def handle_generic_server_crash(e):
    return render_template('error.html', code=500, title="Internal Server Error", message="A backend issue occurred."), 500

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
    p.drawString(45, height - 215, f"Hello {user_name}, your Air Cursor package is ready.")
    p.showPage()
    p.save()
    buffer.seek(0)
    res = make_response(buffer.read())
    res.headers['Content-Type'] = 'application/pdf'
    res.headers['Content-Disposition'] = 'attachment; filename=AirCursor.pdf'
    return res

if __name__ == '__main__':
    app.run(debug=True)
