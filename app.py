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
# 💥 ૧. કન્ફિગરેશન & ક્રેડેન્શિયલ્સ 💥
# =========================================================================
MASTER_PASSCODE = os.environ.get('MASTER_PASSCODE', '112008')
DEFAULT_MAIN_NAME = os.environ.get('MAIN_ADMIN_NAME', 'Vansh Patel')
DEFAULT_MAIN_EMAIL = os.environ.get('MAIN_ADMIN_EMAIL', 'vanshp1114@gmail.com')

# SMTP સેટિંગ્સ
SMTP_EMAIL = os.environ.get('SMTP_EMAIL', 'aircursor.verify@gmail.com')
SMTP_APP_PASSWORD = os.environ.get('SMTP_APP_PASSWORD', 'btajqpkrvkflsqvl')

# =========================================================
# 💥 ૨. MONGODB ATLAS CLOUD CONNECTION 💥
# =========================================================
MONGO_URI = os.environ.get('MONGO_URI')
client = None
db = None
visitors_collection = None
subadmins_collection = None
config_collection = None
audit_collection = None

if MONGO_URI:
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = client['air_cursor_db']
        visitors_collection = db['visitors']
        subadmins_collection = db['sub_admins']
        config_collection = db['system_config']
        audit_collection = db['audit_logs']

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
# 💥 ૩. સબ-એડમિન લાઈવ ઓડિટ લોગર (ACTIVITY TRACKER) 💥
# =========================================================
def log_activity(sub_name, sub_email, action, status="ALLOWED", details=""):
    if audit_collection is not None:
        try:
            audit_collection.insert_one({
                "subadmin_name": sub_name,
                "subadmin_email": sub_email,
                "action": action,
                "status": status,
                "details": details,
                "ip_address": request.headers.get('X-Forwarded-For', request.remote_addr),
                "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            })
        except Exception as e:
            print(f"❌ Log Error: {e}")

# =========================================================
# 💥 ૪. EMAIL DISPATCH ENGINE (GOLD-OBSIDIAN THEME) 💥
# =========================================================
def send_approval_email(subadmin_name, subadmin_email, action_name, perm_key, subadmin_id):
    if not SMTP_APP_PASSWORD or not SMTP_EMAIL:
        print("⚠️ SMTP not configured.")
        return False

    main_name, main_email = get_main_admin()
    app_base_url = "https://air-cursor-nd6r.onrender.com"
    accept_url = f"{app_base_url}/admin/grant-permission?sub_id={subadmin_id}&perm={perm_key}&passcode={MASTER_PASSCODE}"
    ignore_url = f"{app_base_url}/admin/deny-permission?sub_id={subadmin_id}&action={action_name}"

    msg = MIMEMultipart("alternative")
    msg['Subject'] = f"🛡️ [Air Cursor Security] Sub-Admin Access Request: {action_name}"
    msg['From'] = f"Air Cursor Command <{SMTP_EMAIL}>"
    msg['To'] = main_email

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"></head>
    <body style="margin:0; padding:0; background-color:#0d0e12; font-family:'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color:#E6E4E0;">
        <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color:#0d0e12; padding:40px 15px;">
            <tr>
                <td align="center">
                    <table width="600" border="0" cellspacing="0" cellpadding="0" style="background-color:#16171d; border:1px solid #C5A880; border-radius:24px; box-shadow:0 25px 60px rgba(0,0,0,0.8); overflow:hidden;">
                        <tr>
                            <td style="padding:35px 35px 20px 35px; border-bottom:1px solid rgba(197, 168, 128, 0.2); text-align:center;">
                                <div style="color:#C5A880; font-size:24px; font-weight:800; letter-spacing:1px; text-transform:uppercase;">
                                    AIR CURSOR COMMAND
                                </div>
                                <div style="color:#8e8f96; font-size:12px; margin-top:5px; text-transform:uppercase; letter-spacing:2px;">
                                    Security & Access Authorization Gate
                                </div>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding:30px 35px;">
                                <p style="font-size:16px; color:#ffffff; margin:0 0 15px 0;">Hello <b>{main_name}</b>,</p>
                                <p style="font-size:14px; color:#a6a7ad; line-height:1.6; margin:0 0 25px 0;">
                                    A delegated Sub-Admin has encountered an access restriction and is requesting immediate privilege elevation to execute a protected operation:
                                </p>
                                <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color:#101115; border:1px solid rgba(255,255,255,0.08); border-radius:14px; margin-bottom:25px;">
                                    <tr>
                                        <td style="padding:18px;">
                                            <table width="100%" border="0" cellspacing="0" cellpadding="5">
                                                <tr>
                                                    <td width="38%" style="color:#8e8f96; font-size:13px;">Sub-Admin Name:</td>
                                                    <td style="color:#ffffff; font-weight:700; font-size:14px;">{subadmin_name}</td>
                                                </tr>
                                                <tr>
                                                    <td style="color:#8e8f96; font-size:13px;">Sub-Admin Email:</td>
                                                    <td style="color:#C5A880; font-family:monospace; font-size:13px;">{subadmin_email}</td>
                                                </tr>
                                                <tr>
                                                    <td style="color:#8e8f96; font-size:13px;">Requested Action:</td>
                                                    <td style="color:#00e5ff; font-weight:700; font-size:14px;">{action_name}</td>
                                                </tr>
                                                <tr>
                                                    <td style="color:#8e8f96; font-size:13px;">Permission Flag:</td>
                                                    <td style="color:#e056fd; font-family:monospace; font-size:12px;">{perm_key}</td>
                                                </tr>
                                            </table>
                                        </td>
                                    </tr>
                                </table>
                                <p style="font-size:14px; color:#ffffff; margin:0 0 25px 0; font-weight:600;">
                                    Do you want to grant this permission permanently?
                                </p>
                                <table width="100%" border="0" cellspacing="0" cellpadding="0">
                                    <tr>
                                        <td align="center">
                                            <a href="{accept_url}" target="_blank" style="display:inline-block; padding:12px 30px; background:linear-gradient(135deg, #C5A880 0%, #E6E4E0 100%); color:#101115; text-decoration:none; border-radius:99px; font-weight:800; font-size:14px; margin-right:12px;">
                                                ✓ Approve & Grant
                                            </a>
                                            <a href="{ignore_url}" target="_blank" style="display:inline-block; padding:12px 28px; background-color:#202228; color:#ff4757; text-decoration:none; border-radius:99px; font-weight:700; font-size:14px; border:1px solid rgba(255,71,87,0.4);">
                                                ✕ Ignore / Dismiss
                                            </a>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding:20px 35px; background-color:#101115; border-top:1px solid rgba(255,255,255,0.05); text-align:center;">
                                <p style="font-size:11px; color:#60626a; margin:0;">
                                    © 2026 Air Cursor Technologies • Behind Touch Platform<br>
                                    Automated dispatch sent to Root Administrator ({main_email})
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
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
        print(f"❌ Email Failed: {e}")
        return False

# =========================================================
# 💥 ૫. DEVICE RESTRICTION (WINDOWS ONLY) 💥
# =========================================================
def is_windows_pc(ua_string):
    if not ua_string:
        return False
    ua = ua_string.lower()
    has_windows = 'windows nt' in ua or 'windows' in ua
    is_blocked = any(b in ua for b in [
        'android', 'iphone', 'ipad', 'ipod', 'mobile',
        'tablet', 'macintosh', 'mac os x', 'mac os', 'linux', 'cros', 'tizen', 'watch'
    ])
    return has_windows and not is_blocked

def sanitize_input(text):
    if not text:
        return ""
    return re.sub(r'[<>${}]', '', str(text)).strip()

@app.before_request
def enforce_security():
    if request.path.startswith('/static') or request.path.startswith('/error/'):
        return None
    ua = request.headers.get('User-Agent', '')
    if not is_windows_pc(ua):
        abort(403, description="Air Cursor touchless algorithms are strictly engineered for Windows PC & Laptops only. Mobile devices, Tablets, and macOS are blocked.")

@app.after_request
def add_security_headers(response):
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

# =========================================================
# 💥 ૬. STEALTH HONEYPOT GATEWAY 💥
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

    # ૧. Main Admin Honeypot Match
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
            log_activity(sub['name'], sub['email'], "Session Started", "ALLOWED", "Logged in via Stealth Gateway")
            return redirect(url_for('subadmin_dashboard'))

    # ૩. Normal User Lead
    name = sanitize_input(raw_name)
    email = sanitize_input(raw_email)

    if not name or not email or '@' not in email:
        abort(400, description="Valid Full Name and Email are mandatory.")

    session['user_registered'] = True
    session['user_name'] = name
    session.permanent = bool(remember)
    session['remember_me'] = bool(remember)

    if visitors_collection is not None:
        visitors_collection.insert_one({
            "name": name,
            "email": email,
            "remember_me": bool(remember),
            "user_agent": request.headers.get('User-Agent', ''),
            "registered_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        })

    return redirect(url_for('download_page'))

# =========================================================
# 💥 ૭. MAIN ADMIN DASHBOARD & CONTROLS 💥
# =========================================================
@app.route('/admin')
@app.route('/admin/master')
def main_admin_dashboard():
    if session.get('user_role') != 'main_admin':
        abort(404)

    visitors = list(visitors_collection.find().sort('_id', -1)) if visitors_collection is not None else []
    sub_admins = list(subadmins_collection.find().sort('_id', -1)) if subadmins_collection is not None else []
    activity_logs = list(audit_collection.find().sort('_id', -1).limit(50)) if audit_collection is not None else []
    main_name, main_email = get_main_admin()

    return render_template(
        'admin_master.html',
        visitors=visitors,
        sub_admins=sub_admins,
        activity_logs=activity_logs,
        main_name=main_name,
        main_email=main_email
    )

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

@app.route('/admin/remove-subadmin/<id>')
def remove_subadmin(id):
    if session.get('user_role') != 'main_admin':
        abort(404)
    if subadmins_collection is not None:
        subadmins_collection.delete_one({"_id": ObjectId(id)})
    return redirect(url_for('main_admin_dashboard'))

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

@app.route('/admin/delete-lead/<id>')
def delete_lead(id):
    is_main = session.get('user_role') == 'main_admin'
    is_sub_allowed = False
    
    if session.get('user_role') == 'sub_admin' and subadmins_collection is not None:
        sub = subadmins_collection.find_one({"_id": ObjectId(session.get('subadmin_id'))})
        if sub and sub.get('can_delete_visitors'):
            is_sub_allowed = True
        log_activity(
            session.get('subadmin_name'), 
            session.get('subadmin_email'), 
            f"Delete Lead ID: {id}", 
            "ALLOWED" if is_sub_allowed else "RESTRICTED"
        )

    if not is_main and not is_sub_allowed:
        abort(403, description="Privileges required to delete visitor records.")

    if visitors_collection is not None:
        visitors_collection.delete_one({"_id": ObjectId(id)})

    return redirect(request.referrer or url_for('home'))

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

@app.route('/admin/deny-permission')
def deny_permission():
    action = request.args.get('action', 'Requested Action')
    return render_template(
        'error.html', 
        code="Dismissed", 
        title="Permission Request Ignored", 
        message=f"The request for '{action}' has been dismissed. The Sub-Admin remains restricted."
    ), 200

# =========================================================
# 💥 ૮. SUB-ADMIN WORKSPACE & AUDIT 💥
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

    log_activity(sub_info['name'], sub_info['email'], "Viewed Dashboard", "ALLOWED", "Navigated to Sub-Admin Workspace")

    visitors = []
    if sub_info.get('can_view_visitors') and visitors_collection is not None:
        visitors = list(visitors_collection.find().sort('_id', -1))

    return render_template('subadmin.html', subadmin_info=sub_info, visitors=visitors)

@app.route('/subadmin/request-permission', methods=['POST'])
def request_permission():
    if session.get('user_role') != 'sub_admin':
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    
    data = request.get_json() or {}
    action_name = data.get('action', 'Unknown Action')
    perm_key = data.get('permission_key', '')
    sub_id = session.get('subadmin_id')
    sub_name = session.get('subadmin_name')
    sub_email = session.get('subadmin_email')

    log_activity(sub_name, sub_email, f"Unauthorized Action: {action_name}", "RESTRICTED", f"Requested flag: {perm_key}")
    sent = send_approval_email(sub_name, sub_email, action_name, perm_key, sub_id)
    
    if sent:
        return jsonify({"status": "success", "message": "Approval request sent to Main Admin's email!"})
    else:
        return jsonify({"status": "logged", "message": "Request logged in security audit trail."})

@app.route('/admin/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# =========================================================
# 💥 ૯. ગ્લોબલ એરર હેન્ડલર & ડાઉનલોડ 💥
# =========================================================
@app.errorhandler(HTTPException)
def handle_http_exception(e):
    return render_template('error.html', code=e.code, title=e.name, message=e.description), e.code

@app.errorhandler(Exception)
def handle_generic_server_crash(e):
    return render_template('error.html', code=500, title="Internal Server Error", message="An unexpected system failure occurred."), 500

@app.route('/error/<int:code>')
def simulate_error(code):
    if code in default_exceptions:
        abort(code)
    return render_template('error.html', code=code, title="Custom Status", message="Non-standard status code."), 400

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
