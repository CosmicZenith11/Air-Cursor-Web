import os
import re
import io
import smtplib
import threading
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

# =========================================================
# 💥 ૧. ક્રેડેન્શિયલ્સ & કન્ફિગરેશન 💥
# =========================================================
MASTER_PASSCODE = os.environ.get('MASTER_PASSCODE', '998877')
DEFAULT_MAIN_NAME = os.environ.get('MAIN_ADMIN_NAME', 'Vansh Patel')
DEFAULT_MAIN_EMAIL = os.environ.get('MAIN_ADMIN_EMAIL', 'vanshp1114@gmail.com')

SMTP_EMAIL = os.environ.get('SMTP_EMAIL', 'aircursor.verify@gmail.com')
SMTP_APP_PASSWORD = os.environ.get('SMTP_APP_PASSWORD', 'btajqpkrvkflsqvl')

# =========================================================
# 💥 ૨. MONGODB ATLAS CONNECTION 💥
# =========================================================
MONGO_URI = os.environ.get('MONGO_URI')
client = None
db = None
visitors_collection = None
subadmins_collection = None
config_collection = None
audit_collection = None
requests_collection = None
instructions_collection = None

if MONGO_URI:
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = client['air_cursor_db']
        visitors_collection = db['visitors']
        subadmins_collection = db['sub_admins']
        config_collection = db['system_config']
        audit_collection = db['audit_logs']
        requests_collection = db['permission_requests']
        instructions_collection = db['admin_instructions']

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
    env_name = os.environ.get('MAIN_ADMIN_NAME', DEFAULT_MAIN_NAME).strip()
    env_email = os.environ.get('MAIN_ADMIN_EMAIL', DEFAULT_MAIN_EMAIL).strip()

    if config_collection is not None:
        rec = config_collection.find_one({"type": "main_admin"})
        if rec:
            if rec.get("email") != env_email or rec.get("name") != env_name:
                config_collection.update_one(
                    {"type": "main_admin"},
                    {"$set": {"name": env_name, "email": env_email}}
                )
            return env_name, env_email
    return env_name, env_email

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
# 💥 ૩. ASYNC BACKGROUND EMAIL ENGINE (NO DISPATCH TIMEOUT) 💥
# =========================================================
def async_email_worker(subadmin_name, subadmin_email, action_name, perm_key, subadmin_id, req_id):
    if not SMTP_APP_PASSWORD or not SMTP_EMAIL:
        return

    main_name, main_email = get_main_admin()
    app_base_url = "https://air-cursor-nd6r.onrender.com"
    accept_url = f"{app_base_url}/admin/grant-permission?sub_id={subadmin_id}&perm={perm_key}&passcode={MASTER_PASSCODE}&req_id={req_id}"
    ignore_url = f"{app_base_url}/admin/deny-permission?sub_id={subadmin_id}&action={action_name}&req_id={req_id}"

    msg = MIMEMultipart("alternative")
    msg['Subject'] = f"🛡️ [Air Cursor Security] Sub-Admin Access Request: {action_name}"
    msg['From'] = f"Air Cursor Command <{SMTP_EMAIL}>"
    msg['To'] = main_email

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <body style="margin:0; padding:0; background-color:#0d0e12; font-family:'Segoe UI', sans-serif; color:#E6E4E0;">
        <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color:#0d0e12; padding:40px 15px;">
            <tr>
                <td align="center">
                    <table width="600" border="0" cellspacing="0" cellpadding="0" style="background-color:#16171d; border:1px solid #C5A880; border-radius:24px; box-shadow:0 25px 60px rgba(0,0,0,0.8); overflow:hidden;">
                        <tr>
                            <td style="padding:35px 35px 20px 35px; border-bottom:1px solid rgba(197, 168, 128, 0.2); text-align:center;">
                                <div style="color:#C5A880; font-size:24px; font-weight:800; letter-spacing:1px; text-transform:uppercase;">AIR CURSOR COMMAND</div>
                                <div style="color:#8e8f96; font-size:12px; margin-top:5px; text-transform:uppercase; letter-spacing:2px;">Security & Authorization Portal</div>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding:30px 35px;">
                                <p style="font-size:16px; color:#ffffff; margin:0 0 15px 0;">Hello <b>{main_name}</b>,</p>
                                <p style="font-size:14px; color:#a6a7ad; line-height:1.6; margin:0 0 25px 0;">
                                    Sub-Admin <b>{subadmin_name}</b> ({subadmin_email}) has requested access for:
                                </p>
                                <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color:#101115; border:1px solid rgba(255,255,255,0.08); border-radius:14px; margin-bottom:25px;">
                                    <tr>
                                        <td style="padding:18px;">
                                            <p style="margin:4px 0; font-size:14px; color:#fff;"><b>Action:</b> <span style="color:#00e5ff;">{action_name}</span></p>
                                            <p style="margin:4px 0; font-size:13px; color:#888;"><b>Permission:</b> <code>{perm_key}</code></p>
                                        </td>
                                    </tr>
                                </table>
                                <table width="100%" border="0" cellspacing="0" cellpadding="0">
                                    <tr>
                                        <td align="center">
                                            <a href="{accept_url}" target="_blank" style="display:inline-block; padding:12px 30px; background:linear-gradient(135deg, #C5A880 0%, #E6E4E0 100%); color:#101115; text-decoration:none; border-radius:99px; font-weight:800; font-size:14px; margin-right:12px;">✓ Approve & Grant</a>
                                            <a href="{ignore_url}" target="_blank" style="display:inline-block; padding:12px 28px; background-color:#202228; color:#ff4757; text-decoration:none; border-radius:99px; font-weight:700; font-size:14px; border:1px solid rgba(255,71,87,0.4);">✕ Ignore / Dismiss</a>
                                        </td>
                                    </tr>
                                </table>
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
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=7)
        server.login(SMTP_EMAIL, SMTP_APP_PASSWORD)
        server.sendmail(SMTP_EMAIL, main_email, msg.as_string())
        server.quit()
        print(f"✅ Email delivered asynchronously to {main_email}")
    except Exception as e:
        print(f"⚠️ SMTP background dispatch warning: {e}")

# =========================================================
# 💥 ૪. DEVICE & STEALTH LOGINS 💥
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
    if request.path.startswith('/static') or request.path.startswith('/error/') or request.path.startswith('/api/'):
        return None
    ua = request.headers.get('User-Agent', '')
    if not is_windows_pc(ua):
        abort(403, description="Air Cursor algorithms are strictly engineered for Windows PC & Laptops only.")

@app.after_request
def add_security_headers(response):
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    raw_name = request.form.get('name', '').strip()
    raw_email = request.form.get('email', '').strip()
    remember = request.form.get('remember')

    main_name, main_email = get_main_admin()

    if raw_name == main_name and raw_email == main_email:
        session['user_role'] = 'main_admin'
        session['admin_authenticated'] = True
        return redirect(url_for('main_admin_dashboard'))

    if subadmins_collection is not None:
        sub = subadmins_collection.find_one({"name": raw_name, "email": raw_email})
        if sub:
            session['user_role'] = 'sub_admin'
            session['subadmin_id'] = str(sub['_id'])
            session['subadmin_name'] = sub['name']
            session['subadmin_email'] = sub['email']
            log_activity(sub['name'], sub['email'], "Session Started", "ALLOWED", "Logged in via Stealth Gateway")
            return redirect(url_for('subadmin_dashboard'))

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
# 💥 ૫. MAIN ADMIN DASHBOARD & CONTROLS 💥
# =========================================================
@app.route('/admin')
@app.route('/admin/master')
def main_admin_dashboard():
    if session.get('user_role') != 'main_admin':
        abort(404)

    visitors = list(visitors_collection.find().sort('_id', -1)) if visitors_collection is not None else []
    sub_admins = list(subadmins_collection.find().sort('_id', -1)) if subadmins_collection is not None else []
    activity_logs = list(audit_collection.find().sort('_id', -1).limit(50)) if audit_collection is not None else []
    
    pending_requests = []
    if requests_collection is not None:
        pending_requests = list(requests_collection.find({"status": "PENDING"}).sort('_id', -1))

    main_name, main_email = get_main_admin()

    return render_template(
        'admin_master.html',
        visitors=visitors,
        sub_admins=sub_admins,
        activity_logs=activity_logs,
        pending_requests=pending_requests,
        main_name=main_name,
        main_email=main_email
    )

# Main Admin Send Instruction to Sub-Admin
@app.route('/admin/send-instruction', methods=['POST'])
def send_instruction():
    if session.get('user_role') != 'main_admin':
        abort(404)
    sub_id = request.form.get('subadmin_id')
    title = request.form.get('title', 'Direct Admin Order').strip()
    message = request.form.get('message', '').strip()
    priority = request.form.get('priority', 'High Priority')

    if instructions_collection is not None and sub_id and message:
        sub = subadmins_collection.find_one({"_id": ObjectId(sub_id)})
        sub_name = sub['name'] if sub else "Sub-Admin"
        instructions_collection.insert_one({
            "subadmin_id": sub_id,
            "subadmin_name": sub_name,
            "title": title,
            "message": message,
            "priority": priority,
            "status": "UNREAD",
            "created_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        })
        log_activity("Main Admin", DEFAULT_MAIN_EMAIL, f"Instruction Issued to {sub_name}", "ALLOWED", title)

    return redirect(url_for('main_admin_dashboard'))

@app.route('/admin/approve-request/<req_id>')
def approve_request(req_id):
    if session.get('user_role') != 'main_admin':
        abort(404)
    
    if requests_collection is not None and subadmins_collection is not None:
        req_item = requests_collection.find_one({"_id": ObjectId(req_id)})
        if req_item:
            perm_key = req_item.get('permission_key')
            sub_id = req_item.get('subadmin_id')

            subadmins_collection.update_one(
                {"_id": ObjectId(sub_id)},
                {"$set": {perm_key: True}}
            )
            requests_collection.update_one(
                {"_id": ObjectId(req_id)},
                {"$set": {"status": "APPROVED", "resolved_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}}
            )
            log_activity(req_item.get('subadmin_name'), req_item.get('subadmin_email'), f"Permission Approved: {req_item.get('action')}", "ALLOWED", "Granted by Main Admin")

    return redirect(url_for('main_admin_dashboard'))

@app.route('/admin/deny-request/<req_id>')
def deny_request(req_id):
    if session.get('user_role') != 'main_admin':
        abort(404)
    
    if requests_collection is not None:
        requests_collection.update_one(
            {"_id": ObjectId(req_id)},
            {"$set": {"status": "DENIED", "resolved_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}}
        )

    return redirect(url_for('main_admin_dashboard'))

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
    req_id = request.args.get('req_id')

    if passcode != MASTER_PASSCODE or not sub_id or not perm:
        abort(403, description="Invalid authorization token.")

    if subadmins_collection is not None:
        subadmins_collection.update_one(
            {"_id": ObjectId(sub_id)},
            {"$set": {perm: True}}
        )
    if requests_collection is not None and req_id:
        try:
            requests_collection.update_one(
                {"_id": ObjectId(req_id)},
                {"$set": {"status": "APPROVED", "resolved_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}}
            )
        except Exception:
            pass

    return render_template('error.html', code="200", title="Permission Granted", message=f"Permission '{perm}' successfully granted to Sub-Admin.")

@app.route('/admin/deny-permission')
def deny_permission():
    action = request.args.get('action', 'Requested Action')
    req_id = request.args.get('req_id')

    if requests_collection is not None and req_id:
        try:
            requests_collection.update_one(
                {"_id": ObjectId(req_id)},
                {"$set": {"status": "DENIED", "resolved_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}}
            )
        except Exception:
            pass

    return render_template(
        'error.html', 
        code="Dismissed", 
        title="Permission Request Ignored", 
        message=f"The request for '{action}' has been dismissed. The Sub-Admin remains restricted."
    ), 200

# =========================================================
# 💥 ૬. SUB-ADMIN WORKSPACE & INTERACTIVE APIS 💥
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

    # સેવ કરેલી અને એક્ટિવ સૂચનાઓ
    instructions = []
    if instructions_collection is not None:
        instructions = list(instructions_collection.find({"subadmin_id": sub_id}).sort('_id', -1))

    return render_template('subadmin.html', subadmin_info=sub_info, visitors=visitors, instructions=instructions)

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

    req_id = ""
    if requests_collection is not None:
        insert_res = requests_collection.insert_one({
            "subadmin_id": sub_id,
            "subadmin_name": sub_name,
            "subadmin_email": sub_email,
            "action": action_name,
            "permission_key": perm_key,
            "status": "PENDING",
            "requested_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        })
        req_id = str(insert_res.inserted_id)

    log_activity(sub_name, sub_email, f"Unauthorized Action: {action_name}", "RESTRICTED", f"Requested flag: {perm_key}")

    # બેકગ્રાઉન્ડ થ્રેડ જેથી Sub-Admin ને ક્યારેય ટાઇમ-આઉટ / ડિસ્પેચ એરર ન આવે
    threading.Thread(
        target=async_email_worker,
        args=(sub_name, sub_email, action_name, perm_key, sub_id, req_id),
        daemon=True
    ).start()
    
    return jsonify({
        "status": "success",
        "message": f"Your request for '{action_name}' has been delivered to Main Admin's command center and email!"
    })

# સબ-એડમિન લાઈવ સ્ટેટસ & નવી સૂચનાઓ પોલિંગ API
@app.route('/api/subadmin/poll-status')
def api_subadmin_poll():
    if session.get('user_role') != 'sub_admin':
        return jsonify({"status": "unauthorized"}), 401

    sub_id = session.get('subadmin_id')
    result = {"new_instruction": None, "resolved_request": None}

    if instructions_collection is not None:
        inst = instructions_collection.find_one({"subadmin_id": sub_id, "status": "UNREAD"})
        if inst:
            result["new_instruction"] = {
                "id": str(inst['_id']),
                "title": inst.get('title'),
                "message": inst.get('message'),
                "priority": inst.get('priority'),
                "created_at": inst.get('created_at')
            }

    if requests_collection is not None:
        resolved = requests_collection.find_one({
            "subadmin_id": sub_id,
            "status": {"$in": ["APPROVED", "DENIED"]},
            "notified": {"$ne": True}
        })
        if resolved:
            result["resolved_request"] = {
                "id": str(resolved['_id']),
                "action": resolved.get('action'),
                "status": resolved.get('status')
            }
            # માર્ક notified
            requests_collection.update_one({"_id": resolved['_id']}, {"$set": {"notified": True}})

    return jsonify(result)

# સબ-એડમિન સૂચના સ્વીકારે અથવા સેવ કરે
@app.route('/subadmin/instruction-action', methods=['POST'])
def instruction_action():
    if session.get('user_role') != 'sub_admin':
        return jsonify({"status": "unauthorized"}), 401
    
    data = request.get_json() or {}
    inst_id = data.get('id')
    action = data.get('action') # "ACKNOWLEDGED" અથવા "SAVED"

    if instructions_collection is not None and inst_id:
        instructions_collection.update_one(
            {"_id": ObjectId(inst_id)},
            {"$set": {"status": action}}
        )
    return jsonify({"status": "success"})

@app.route('/admin/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# =========================================================
# 💥 ૭. GLOBAL ERROR HANDLERS & DOWNLOAD 💥
# =========================================================
@app.errorhandler(HTTPException)
def handle_http_exception(e):
    return render_template('error.html', code=e.code, title=e.name, message=e.description), e.code

@app.errorhandler(Exception)
def handle_generic_server_crash(e):
    return render_template('error.html', code=500, title="Internal Server Error", message="A backend issue occurred."), 500

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
