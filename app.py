import os
import re
import io
import random
import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate, make_msgid
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
# 💥 ૨. MONGODB ATLAS CLOUD CONNECTION 💥
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
messages_collection = None
otp_collection = None

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
        messages_collection = db['subadmin_messages']
        otp_collection = db['security_otps']

        if config_collection.count_documents({"type": "main_admin"}) == 0:
            config_collection.insert_one({
                "type": "main_admin",
                "name": DEFAULT_MAIN_NAME,
                "email": DEFAULT_MAIN_EMAIL,
                "passcode": MASTER_PASSCODE
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
            return env_name, env_email, rec.get("passcode", MASTER_PASSCODE)
    return env_name, env_email, MASTER_PASSCODE

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
# 💥 ૩. ANTI-SPAM ASYNC EMAIL ENGINE 💥
# =========================================================
def send_system_email(to_email, subject, plain_text, html_body):
    if not SMTP_APP_PASSWORD or not SMTP_EMAIL:
        return False
    msg = MIMEMultipart("alternative")
    msg['Subject'] = subject
    msg['From'] = f"Air Cursor Security <{SMTP_EMAIL}>"
    msg['To'] = to_email
    msg['Reply-To'] = SMTP_EMAIL
    msg['Date'] = formatdate(localtime=True)
    msg['Message-ID'] = make_msgid(domain='aircursor.verify')

    msg.attach(MIMEText(plain_text, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=10)
        server.login(SMTP_EMAIL, SMTP_APP_PASSWORD)
        server.sendmail(SMTP_EMAIL, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"⚠️ SMTP Error: {e}")
        return False

# =========================================================
# 💥 ૪. DEVICE & STEALTH ROUTING 💥
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
        abort(403, description="Air Cursor is strictly engineered for Windows PC & Laptops only.")

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

    main_name, main_email, _ = get_main_admin()

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

    forbidden_symbols = re.compile(r'[+\-*\/~`!#$%^&()=_{}\[\]:;"\'<>,?|\\]')
    if forbidden_symbols.search(raw_name) or forbidden_symbols.search(raw_email):
        abort(400, description="Symbols (+, -, *, /) are strictly prohibited! Only letters, numbers, @, and . are allowed.")

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
# 💥 ૫. MAIN ADMIN DASHBOARD & OTP WORKFLOWS 💥
# =========================================================
@app.route('/admin')
@app.route('/admin/master')
def main_admin_dashboard():
    if session.get('user_role') != 'main_admin':
        abort(404)

    visitors = list(visitors_collection.find().sort('_id', -1)) if visitors_collection is not None else []
    sub_admins = list(subadmins_collection.find().sort('_id', -1)) if subadmins_collection is not None else []
    activity_logs = list(audit_collection.find().sort('_id', -1).limit(50)) if audit_collection is not None else []
    pending_requests = list(requests_collection.find({"status": "PENDING"}).sort('_id', -1)) if requests_collection is not None else []
    work_messages = list(messages_collection.find().sort('_id', -1).limit(40)) if messages_collection is not None else []

    main_name, main_email, _ = get_main_admin()

    return render_template(
        'admin_master.html',
        visitors=visitors,
        sub_admins=sub_admins,
        activity_logs=activity_logs,
        pending_requests=pending_requests,
        work_messages=work_messages,
        main_name=main_name,
        main_email=main_email
    )

# 💥 OTP Generation for Profile/Passcode Update 💥
@app.route('/admin/request-profile-otp', methods=['POST'])
def request_profile_otp():
    if session.get('user_role') != 'main_admin':
        return jsonify({"status": "unauthorized"}), 401

    main_name, main_email, _ = get_main_admin()
    otp = f"{random.randint(100000, 999999)}"

    if otp_collection is not None:
        otp_collection.delete_many({"email": main_email})
        otp_collection.insert_one({
            "email": main_email,
            "otp": otp,
            "created_at": datetime.utcnow(),
            "verified": False
        })

    verify_url = "https://air-cursor-nd6r.onrender.com/admin/security-verify"
    subject = "🔐 [Air Cursor Security] One-Time Security Passcode (OTP)"
    plain = f"Your Security OTP is: {otp}\nVerify here: {verify_url}"
    html = f"""
    <div style="background:#0d0e12; color:#E6E4E0; padding:30px; font-family:sans-serif;">
        <div style="max-width:500px; margin:auto; background:#16171d; border:1px solid #C5A880; border-radius:20px; padding:30px; text-align:center;">
            <h2 style="color:#C5A880;">Security Authorization</h2>
            <p>Hello {main_name}, a request to modify Root Profile / Passcode was triggered.</p>
            <div style="font-size:32px; font-weight:800; letter-spacing:8px; color:#00e5ff; margin:20px 0;">{otp}</div>
            <p style="font-size:13px; color:#888;">Valid for 10 minutes. Click below to verify and unlock credential updates:</p>
            <a href="{verify_url}" style="display:inline-block; padding:12px 28px; background:linear-gradient(135deg, #C5A880 0%, #E6E4E0 100%); color:#000; border-radius:99px; font-weight:bold; text-decoration:none; margin-top:15px;">Verify Security OTP</a>
        </div>
    </div>
    """
    threading.Thread(target=send_system_email, args=(main_email, subject, plain, html), daemon=True).start()
    return jsonify({"status": "success", "message": f"Security OTP dispatched to {main_email}. Please check your inbox."})

@app.route('/admin/security-verify')
def security_verify_page():
    main_name, main_email, _ = get_main_admin()
    return render_template('security_verify.html', main_name=main_name, main_email=main_email)

@app.route('/api/admin/validate-otp', methods=['POST'])
def validate_otp():
    data = request.get_json() or {}
    otp = data.get('otp', '').strip()
    main_name, main_email, _ = get_main_admin()

    if otp_collection is not None:
        rec = otp_collection.find_one({"email": main_email, "otp": otp})
        if rec and (datetime.utcnow() - rec.get("created_at", datetime.utcnow())).total_seconds() < 600:
            token = str(rec['_id'])
            otp_collection.update_one({"_id": rec['_id']}, {"$set": {"verified": True}})
            return jsonify({"status": "success", "token": token})
    return jsonify({"status": "error", "message": "Invalid or Expired OTP"}), 400

@app.route('/admin/execute-profile-update', methods=['POST'])
def execute_profile_update():
    token = request.form.get('verified_token')
    new_name = request.form.get('new_name', '').strip()
    new_email = request.form.get('new_email', '').strip()
    new_passcode = request.form.get('new_passcode', '').strip()
    curr_passcode = request.form.get('current_passcode', '').strip()

    main_name, main_email, active_passcode = get_main_admin()

    if curr_passcode != active_passcode:
        abort(403, description="Access Denied: Current Master Passcode verification failed.")

    if otp_collection is not None and token:
        try:
            valid_otp = otp_collection.find_one({"_id": ObjectId(token), "verified": True})
            if not valid_otp:
                abort(403, description="Unauthorized: OTP verification token missing or expired.")
        except Exception:
            abort(403)

    update_payload = {"name": new_name, "email": new_email}
    if new_passcode:
        update_payload["passcode"] = new_passcode

    if config_collection is not None:
        config_collection.update_one({"type": "main_admin"}, {"$set": update_payload}, upsert=True)

    if otp_collection is not None and token:
        otp_collection.delete_one({"_id": ObjectId(token)})

    log_activity("Main Admin", new_email, "Updated Root Profile Credentials", "ALLOWED")
    return redirect(url_for('main_admin_dashboard'))

# 💥 Forgot Passcode Dispatch 💥
@app.route('/admin/forgot-passcode', methods=['POST'])
def forgot_passcode():
    main_name, main_email, active_passcode = get_main_admin()
    subject = "🔑 [Air Cursor Security] Master Passcode Recovery"
    plain = f"Hello {main_name},\n\nYour Master Passcode is: {active_passcode}"
    html = f"""
    <div style="background:#0d0e12; color:#fff; padding:30px; font-family:sans-serif;">
        <div style="max-width:500px; margin:auto; background:#16171d; border:1px solid #C5A880; border-radius:20px; padding:30px; text-align:center;">
            <h2 style="color:#C5A880;">Passcode Recovery</h2>
            <p>Your current Master Authorization Passcode is:</p>
            <div style="font-size:28px; font-weight:800; color:#2ed573; margin:15px 0;">{active_passcode}</div>
            <p style="font-size:12px; color:#888;">Do not share this passcode with unauthorized personnel.</p>
        </div>
    </div>
    """
    threading.Thread(target=send_system_email, args=(main_email, subject, plain, html), daemon=True).start()
    return jsonify({"status": "success", "message": f"Your Master Passcode has been emailed to {main_email}."})

# 💥 LIVE REFRESH API (NO FULL PAGE RELOADS) 💥
@app.route('/api/admin/live-sync')
def api_admin_live_sync():
    if session.get('user_role') != 'main_admin':
        return jsonify({"status": "unauthorized"}), 401

    visitors = list(visitors_collection.find().sort('_id', -1)) if visitors_collection is not None else []
    sub_admins = list(subadmins_collection.find().sort('_id', -1)) if subadmins_collection is not None else []
    activity_logs = list(audit_collection.find().sort('_id', -1).limit(50)) if audit_collection is not None else []
    pending_requests = list(requests_collection.find({"status": "PENDING"}).sort('_id', -1)) if requests_collection is not None else []
    work_messages = list(messages_collection.find().sort('_id', -1).limit(40)) if messages_collection is not None else []

    def serialize(docs):
        res = []
        for d in docs:
            c = dict(d)
            c['_id'] = str(c['_id'])
            res.append(c)
        return res

    return jsonify({
        "status": "success",
        "visitors": serialize(visitors),
        "sub_admins": serialize(sub_admins),
        "activity_logs": serialize(activity_logs),
        "pending_requests": serialize(pending_requests),
        "work_messages": serialize(work_messages)
    })

@app.route('/admin/send-instruction', methods=['POST'])
def send_instruction():
    if session.get('user_role') != 'main_admin':
        abort(404)
    sub_id = request.form.get('subadmin_id')
    title = request.form.get('title', 'Direct Admin Order').strip()
    message = request.form.get('message', '').strip()
    priority = request.form.get('priority', 'Urgent Protocol')

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
        log_activity("Main Admin", DEFAULT_MAIN_EMAIL, f"Directive Issued to {sub_name}", "ALLOWED", title)

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

            # Handle Sub-Admin Profile Change Approval
            if perm_key == "profile_change":
                subadmins_collection.update_one(
                    {"_id": ObjectId(sub_id)},
                    {"$set": {"name": req_item.get('new_name'), "email": req_item.get('new_email')}}
                )
            else:
                subadmins_collection.update_one(
                    {"_id": ObjectId(sub_id)},
                    {"$set": {perm_key: True}}
                )

            requests_collection.update_one(
                {"_id": ObjectId(req_id)},
                {"$set": {"status": "APPROVED", "resolved_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}}
            )
            log_activity(req_item.get('subadmin_name'), req_item.get('subadmin_email'), f"Approved: {req_item.get('action')}", "ALLOWED")
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

@app.route('/admin/delete-message/<id>')
def delete_subadmin_message(id):
    if session.get('user_role') != 'main_admin':
        abort(404)
    if messages_collection is not None:
        messages_collection.delete_one({"_id": ObjectId(id)})
    return redirect(url_for('main_admin_dashboard'))

@app.route('/api/admin/poll-messages')
def api_admin_poll_messages():
    if session.get('user_role') != 'main_admin':
        return jsonify({"status": "unauthorized"}), 401
    latest_msg = None
    if messages_collection is not None:
        item = messages_collection.find_one({"status": "UNREAD"}, sort=[('_id', -1)])
        if item:
            latest_msg = {
                "id": str(item['_id']),
                "from": item.get('subadmin_name'),
                "subject": item.get('subject'),
                "content": item.get('content')
            }
            messages_collection.update_one({"_id": item['_id']}, {"$set": {"status": "DELIVERED"}})
    return jsonify({"new_message": latest_msg})

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

@app.route('/admin/delete-lead/<id>')
def delete_lead(id):
    is_main = session.get('user_role') == 'main_admin'
    is_sub_allowed = False
    if session.get('user_role') == 'sub_admin' and subadmins_collection is not None:
        sub = subadmins_collection.find_one({"_id": ObjectId(session.get('subadmin_id'))})
        if sub and sub.get('can_delete_visitors'):
            is_sub_allowed = True
        log_activity(
            session.get('subadmin_name'), session.get('subadmin_email'),
            f"Delete Lead ID: {id}", "ALLOWED" if is_sub_allowed else "RESTRICTED"
        )
    if not is_main and not is_sub_allowed:
        abort(403)
    if visitors_collection is not None:
        visitors_collection.delete_one({"_id": ObjectId(id)})
    return redirect(request.referrer or url_for('home'))

# =========================================================
# 💥 ૬. SUB-ADMIN WORKSPACE & PROFILE REQUESTS 💥
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

    visitors = list(visitors_collection.find().sort('_id', -1)) if visitors_collection is not None else []
    instructions = list(instructions_collection.find({"subadmin_id": sub_id}).sort('_id', -1)) if instructions_collection is not None else []

    return render_template('subadmin.html', subadmin_info=sub_info, visitors=visitors, instructions=instructions)

@app.route('/subadmin/request-profile-update', methods=['POST'])
def subadmin_request_profile_update():
    if session.get('user_role') != 'sub_admin':
        return jsonify({"status": "unauthorized"}), 401
    data = request.get_json() or {}
    new_name = data.get('name', '').strip()
    new_email = data.get('email', '').strip()
    sub_id = session.get('subadmin_id')
    sub_name = session.get('subadmin_name')
    sub_email = session.get('subadmin_email')

    if requests_collection is not None:
        requests_collection.insert_one({
            "subadmin_id": sub_id,
            "subadmin_name": sub_name,
            "subadmin_email": sub_email,
            "action": f"Profile Update: Name to '{new_name}', Email to '{new_email}'",
            "permission_key": "profile_change",
            "new_name": new_name,
            "new_email": new_email,
            "status": "PENDING",
            "requested_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        })
        log_activity(sub_name, sub_email, "Requested Profile Credential Change", "RESTRICTED")

    return jsonify({"status": "success", "message": "Profile update request has been routed to Main Admin for approval!"})

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

    if requests_collection is not None:
        requests_collection.insert_one({
            "subadmin_id": sub_id,
            "subadmin_name": sub_name,
            "subadmin_email": sub_email,
            "action": action_name,
            "permission_key": perm_key,
            "status": "PENDING",
            "requested_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        })
    log_activity(sub_name, sub_email, f"Requested Access: {action_name}", "RESTRICTED", perm_key)
    return jsonify({"status": "success", "message": f"Your request for '{action_name}' has been routed to Main Admin's command center!"})

@app.route('/subadmin/send-message', methods=['POST'])
def subadmin_send_message():
    if session.get('user_role') != 'sub_admin':
        return jsonify({"status": "error"}), 401
    data = request.get_json() or {}
    subject = data.get('subject', 'Work Query').strip()
    content = data.get('content', '').strip()
    sub_name = session.get('subadmin_name', 'Sub-Admin')
    sub_email = session.get('subadmin_email', '')

    if messages_collection is not None and content:
        messages_collection.insert_one({
            "subadmin_name": sub_name,
            "subadmin_email": sub_email,
            "subject": subject,
            "content": content,
            "status": "UNREAD",
            "sent_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        })
        log_activity(sub_name, sub_email, "Dispatched Work Note", "ALLOWED", subject)

    return jsonify({"status": "success", "message": "Message sent directly to Main Admin's inbox!"})

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
            requests_collection.update_one({"_id": resolved['_id']}, {"$set": {"notified": True}})
    return jsonify(result)

@app.route('/subadmin/instruction-action', methods=['POST'])
def instruction_action():
    if session.get('user_role') != 'sub_admin':
        return jsonify({"status": "unauthorized"}), 401
    data = request.get_json() or {}
    inst_id = data.get('id')
    action = data.get('action')
    if instructions_collection is not None and inst_id:
        instructions_collection.update_one({"_id": ObjectId(inst_id)}, {"$set": {"status": action}})
    return jsonify({"status": "success"})

@app.route('/admin/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# =========================================================
# 💥 ૭. ERROR HANDLERS & DOWNLOADS 💥
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

    # =========================================================
# 💥 DEFAULT AVATAR (EXACT RECREATION OF LAST IMAGE) 💥
# =========================================================
DEFAULT_AVATAR = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><defs><linearGradient id='g' x1='0' y1='0' x2='0' y2='1'><stop offset='0%25' stop-color='%234ea5ff'/><stop offset='50%25' stop-color='%232a85ff'/><stop offset='100%25' stop-color='%231868db'/></linearGradient><linearGradient id='a' x1='0' y1='0' x2='0' y2='1'><stop offset='0%25' stop-color='%23ffffff'/><stop offset='100%25' stop-color='%23e2edfc'/></linearGradient></defs><circle cx='50' cy='50' r='50' fill='url(%23g)'/><circle cx='50' cy='37' r='15' fill='url(%23a)'/><path d='M 23.5 80 C 23.5 63 35 56 50 56 C 65 56 76.5 63 76.5 80 Z' fill='url(%23a)'/></svg>"

# ૧. MAIN ADMIN AVATAR UPLOAD
@app.route('/api/admin/avatar/upload', methods=['POST'])
def api_admin_avatar_upload():
    if session.get('user_role') != 'main_admin':
        return jsonify({"status": "unauthorized"}), 401
    data = request.get_json() or {}
    avatar_url = data.get('avatar_url')
    if config_collection is not None and avatar_url:
        config_collection.update_one({"type": "main_admin"}, {"$set": {"avatar": avatar_url}}, upsert=True)
        log_activity("Main Admin", DEFAULT_MAIN_EMAIL, "Updated Profile Avatar", "ALLOWED")
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 400

# ૨. MAIN ADMIN AVATAR REMOVE (RESETS TO DEFAULT IN MONGODB)
@app.route('/api/admin/avatar/remove', methods=['POST'])
def api_admin_avatar_remove():
    if session.get('user_role') != 'main_admin':
        return jsonify({"status": "unauthorized"}), 401
    if config_collection is not None:
        config_collection.update_one({"type": "main_admin"}, {"$unset": {"avatar": ""}})
        log_activity("Main Admin", DEFAULT_MAIN_EMAIL, "Removed Custom Avatar", "ALLOWED")
        return jsonify({"status": "success", "default_avatar": DEFAULT_AVATAR})
    return jsonify({"status": "error"}), 400

# ૩. SUB-ADMIN AVATAR UPLOAD
@app.route('/api/subadmin/avatar/upload', methods=['POST'])
def api_subadmin_avatar_upload():
    if session.get('user_role') != 'sub_admin':
        return jsonify({"status": "unauthorized"}), 401
    data = request.get_json() or {}
    avatar_url = data.get('avatar_url')
    sub_id = session.get('subadmin_id')
    if subadmins_collection is not None and avatar_url and sub_id:
        subadmins_collection.update_one({"_id": ObjectId(sub_id)}, {"$set": {"avatar": avatar_url}})
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 400

# ૪. SUB-ADMIN AVATAR REMOVE (RESETS TO DEFAULT IN MONGODB)
@app.route('/api/subadmin/avatar/remove', methods=['POST'])
def api_subadmin_avatar_remove():
    if session.get('user_role') != 'sub_admin':
        return jsonify({"status": "unauthorized"}), 401
    sub_id = session.get('subadmin_id')
    if subadmins_collection is not None and sub_id:
        subadmins_collection.update_one({"_id": ObjectId(sub_id)}, {"$unset": {"avatar": ""}})
        return jsonify({"status": "success", "default_avatar": DEFAULT_AVATAR})
    return jsonify({"status": "error"}), 400

if __name__ == '__main__':
    app.run(debug=True)
