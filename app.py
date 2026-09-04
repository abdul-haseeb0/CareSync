import os
import json
import datetime
from decimal import Decimal
from functools import wraps
from flask import Flask, request, jsonify, session, send_from_directory
from werkzeug.utils import secure_filename
import mysql.connector
from mysql.connector import Error
import logging as _logging
_logging.getLogger("passlib").setLevel(_logging.ERROR)  # suppress bcrypt __about__ warning

from config import Config
from logger_service import log_application, log_security, log_audit, log_error, clear_external_log_files
from app.services.ai_service import AIService
import security

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = Config.SECRET_KEY
app.config['SESSION_COOKIE_NAME'] = 'hims_session'
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(hours=8)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False
app.config['UPLOAD_FOLDER'] = Config.UPLOAD_FOLDER
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ============================================================
# CYBERSECURITY: CACHE-CONTROL & BACK-BUTTON CACHE PREVENTION
# ============================================================
@app.after_request
def apply_security_headers(response):
    """
    Prevents browsers from caching sensitive protected pages and clinical data,
    defeating back-button re-entry vulnerability after logout.
    """
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    return response

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'dcm', 'dicom', 'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ============================================================
# DB HELPERS & SERIALIZATION
# ============================================================

def get_db_connection():
    cfg = Config.DB_CONFIG
    return mysql.connector.connect(
        host=cfg["host"],
        user=cfg["user"],
        password=cfg["password"],
        database=cfg["database"]
    )

def serialize_value(val):
    if isinstance(val, (datetime.date, datetime.datetime)):
        return val.isoformat()
    if isinstance(val, Decimal):
        return float(val)
    return val

def serialize_row(row):
    if row is None:
        return None
    return {k: serialize_value(v) for k, v in row.items()}

def serialize_rows(rows):
    return [serialize_row(row) for row in rows]

# ============================================================
# DECORATORS FOR RBAC & LOGGING
# ============================================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            log_security("UNAUTHORIZED_ACCESS", ip_address=request.remote_addr, status="FAILURE", details=f"Attempted to access {request.path}")
            return jsonify({"error": "Unauthorized", "message": "Please log in to continue."}), 401
        
        # Verify account status is still active
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT status FROM users WHERE id = %s", (session['user']['id'],))
            user = cursor.fetchone()
            if not user or not user['status']:
                log_security("DISABLED_ACCOUNT_ACCESS", user_id=session['user']['id'], username=session['user']['username'], status="FAILURE", details="Account is disabled.")
                session.clear()
                return jsonify({"error": "Forbidden", "message": "Your account has been disabled."}), 403
        finally:
            cursor.close()
            conn.close()
            
        return f(*args, **kwargs)
    return decorated_function

def roles_required(*roles):
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            user_role = session['user']['role']
            if user_role not in roles:
                log_security("ROLE_PRIVILEGE_VIOLATION", user_id=session['user']['id'], username=session['user']['username'], role=user_role, ip_address=request.remote_addr, status="FORBIDDEN", details=f"Required roles: {roles}, User role: {user_role}, Path: {request.path}")
                return jsonify({"error": "Forbidden", "message": "You do not have permission to perform this action."}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def log_activity_dual(user_id, user_role, action, target_resource=None, details=None, status="SUCCESS"):
    """
    Simultaneously writes to MySQL activity_logs table and structured audit.log file
    """
    # 1. Write to MySQL DB
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO activity_logs (user_id, action, details) VALUES (%s, %s, %s)",
            (user_id, action, str(details) if details else None)
        )
        conn.commit()
    except Error as e:
        log_error(f"Failed to log activity into MySQL: {e}")
    finally:
        cursor.close()
        conn.close()
        
    # 2. Write structured JSON-line to logs/audit.log
    log_audit(
        user_id=user_id,
        user_role=user_role,
        action=action,
        target_resource=target_resource,
        ip_address=request.remote_addr if request else None,
        status=status,
        details=details if isinstance(details, dict) else {"message": str(details)}
    )

# ============================================================
# AUTHENTICATION ENDPOINTS
# ============================================================

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({"error": "Bad Request", "message": "Username and password are required."}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()

        if user is None:
            log_security("LOGIN_FAILED", username=username, ip_address=request.remote_addr, status="FAILURE", details="User does not exist")
            return jsonify({"error": "Unauthorized", "message": "Invalid username or password."}), 401

        if not user['status']:
            log_security("LOGIN_DISABLED_ATTEMPT", user_id=user['id'], username=username, role=user['role'], ip_address=request.remote_addr, status="FAILURE", details="Account disabled")
            return jsonify({"error": "Forbidden", "message": "Your account has been disabled. Please contact the administrator."}), 403

        # Verify password using security.py passlib context
        password_hash = user['password_hash']
        if security.verify_password(password, password_hash):
            # Session Fixation Defense: Invalidate prior session completely
            session.clear()
            
            # Generate new JWT access token with a unique jti (JWT ID)
            token_payload = {
                "sub": user['username'],
                "user_id": user['id'],
                "role": user['role']
            }
            token, jti = security.create_access_token(token_payload)

            session.permanent = True
            session['user'] = {
                "id": user['id'],
                "username": user['username'],
                "full_name": user['full_name'],
                "role": user['role'],
                "jti": jti
            }
            session['access_token'] = token

            log_security("LOGIN_SUCCESS", user_id=user['id'], username=username, role=user['role'], ip_address=request.remote_addr, status="SUCCESS", details=f"User logged in successfully (jti: {jti})")
            log_activity_dual(user['id'], user['role'], "Login", "user", "User logged in successfully")

            resp = jsonify({
                "message": "Login successful",
                "user": session['user'],
                "access_token": token
            })
            resp.set_cookie('access_token', token, httponly=True, samesite='Lax', secure=False)
            return resp
        else:
            log_security("LOGIN_FAILED", user_id=user['id'], username=username, role=user['role'], ip_address=request.remote_addr, status="FAILURE", details="Incorrect password")
            return jsonify({"error": "Unauthorized", "message": "Invalid username or password."}), 401
    except Exception as e:
        log_error(f"Login error for user {username}: {e}")
        return jsonify({"error": "Server Error", "message": "An error occurred during authentication."}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/auth/logout', methods=['POST'])
@login_required
def logout():
    user = session['user']
    log_security("LOGOUT", user_id=user['id'], username=user['username'], role=user['role'], ip_address=request.remote_addr, status="SUCCESS", details="User logged out")
    log_activity_dual(user['id'], user['role'], "Logout", "user", f"User {user['username']} logged out")
    session.clear()
    resp = jsonify({"message": "Logout successful"})
    resp.delete_cookie(app.config['SESSION_COOKIE_NAME'])
    resp.delete_cookie('access_token')
    return resp

@app.route('/api/auth/session', methods=['GET'])
def get_session():
    if 'user' in session:
        return jsonify({"logged_in": True, "user": session['user']})
    return jsonify({"logged_in": False}), 200

# ============================================================
# ADMIN ENDPOINTS: USER MANAGEMENT
# ============================================================

@app.route('/api/admin/users', methods=['GET'])
@roles_required('Admin')
def get_users():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, username, full_name, role, status, created_at FROM users ORDER BY id DESC")
        users = cursor.fetchall()
        return jsonify(serialize_rows(users))
    finally:
        cursor.close()
        conn.close()

@app.route('/api/admin/users', methods=['POST'])
@roles_required('Admin')
def create_user():
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')
    full_name = data.get('full_name', '').strip()
    role = data.get('role', '')

    if not username or not password or not full_name or not role:
        return jsonify({"error": "Bad Request", "message": "All fields are required."}), 400

    valid_roles = ['Admin', 'Doctor', 'Nurse', 'Receptionist', 'Radiologist', 'Lab Operator']
    if role not in valid_roles:
        return jsonify({"error": "Bad Request", "message": f"Invalid role specified. Valid: {valid_roles}"}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            return jsonify({"error": "Conflict", "message": f"Username '{username}' is already taken."}), 409

        hashed = security.get_password_hash(password)
        cursor.execute(
            "INSERT INTO users (username, password_hash, full_name, role) VALUES (%s, %s, %s, %s)",
            (username, hashed, full_name, role)
        )
        conn.commit()
        new_id = cursor.lastrowid
        log_activity_dual(session['user']['id'], session['user']['role'], "Create User", f"user:{new_id}", {"username": username, "role": role, "full_name": full_name})
        return jsonify({"message": "User created successfully", "user_id": new_id}), 201
    finally:
        cursor.close()
        conn.close()

@app.route('/api/admin/users/<int:user_id>', methods=['PUT'])
@roles_required('Admin')
def update_user(user_id):
    data = request.get_json() or {}
    full_name = data.get('full_name', '').strip()
    role = data.get('role', '')
    password = data.get('password', '')

    if not full_name or not role:
        return jsonify({"error": "Bad Request", "message": "Full name and role are required."}), 400

    valid_roles = ['Admin', 'Doctor', 'Nurse', 'Receptionist', 'Radiologist', 'Lab Operator']
    if role not in valid_roles:
        return jsonify({"error": "Bad Request", "message": "Invalid role specified."}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT username FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            return jsonify({"error": "Not Found", "message": "User not found."}), 404

        if password:
            hashed = security.get_password_hash(password)
            cursor.execute(
                "UPDATE users SET full_name = %s, role = %s, password_hash = %s WHERE id = %s",
                (full_name, role, hashed, user_id)
            )
        else:
            cursor.execute(
                "UPDATE users SET full_name = %s, role = %s WHERE id = %s",
                (full_name, role, user_id)
            )
        conn.commit()
        log_activity_dual(session['user']['id'], session['user']['role'], "Update User", f"user:{user_id}", {"username": user['username'], "role": role, "full_name": full_name})
        return jsonify({"message": "User updated successfully"})
    finally:
        cursor.close()
        conn.close()

@app.route('/api/admin/users/<int:user_id>/status', methods=['PATCH'])
@roles_required('Admin')
def toggle_user_status(user_id):
    if user_id == session['user']['id']:
        return jsonify({"error": "Bad Request", "message": "You cannot disable your own account."}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT username, status FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            return jsonify({"error": "Not Found", "message": "User not found."}), 404

        new_status = 0 if user['status'] else 1
        cursor.execute("UPDATE users SET status = %s WHERE id = %s", (new_status, user_id))
        conn.commit()

        status_text = "disabled" if new_status == 0 else "enabled"
        log_activity_dual(session['user']['id'], session['user']['role'], "Toggle User Status", f"user:{user_id}", {"username": user['username'], "status": status_text})
        return jsonify({"message": f"User successfully {status_text}.", "status": new_status})
    finally:
        cursor.close()
        conn.close()

# Permanent Staff Account Deletion (Admin Only)
@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@roles_required('Admin')
def delete_user(user_id):
    if user_id == session['user']['id']:
        return jsonify({"error": "Bad Request", "message": "You cannot delete your own administrative account."}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT username, full_name, role FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            return jsonify({"error": "Not Found", "message": "User account not found."}), 404

        username = user['username']
        role = user['role']

        cursor.execute("UPDATE patients SET created_by = NULL WHERE created_by = %s", (user_id,))
        cursor.execute("UPDATE appointments SET doctor_id = NULL WHERE doctor_id = %s", (user_id,))
        cursor.execute("UPDATE diagnoses SET doctor_id = NULL WHERE doctor_id = %s", (user_id,))
        cursor.execute("UPDATE prescriptions SET doctor_id = NULL WHERE doctor_id = %s", (user_id,))
        cursor.execute("UPDATE vitals SET recorded_by = NULL WHERE recorded_by = %s", (user_id,))
        cursor.execute("UPDATE activity_logs SET user_id = NULL WHERE user_id = %s", (user_id,))
        cursor.execute("UPDATE ai_reports SET user_id = NULL WHERE user_id = %s", (user_id,))

        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()

        log_security("USER_PERMANENTLY_DELETED", user_id=session['user']['id'], username=session['user']['username'], role=session['user']['role'], status="SUCCESS", details=f"Admin deleted user {username} ({role}, ID: {user_id})")
        log_activity_dual(session['user']['id'], session['user']['role'], "Delete Staff Account", f"user:{user_id}", {"deleted_username": username, "deleted_role": role})

        return jsonify({"message": f"Staff account '{username}' ({role}) has been permanently deleted."})
    except Exception as e:
        conn.rollback()
        log_error(f"Error permanently deleting staff account {user_id}: {e}")
        return jsonify({"error": "Server Error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# Activity Logs & Dual Log Purging (Admin Only)
@app.route('/api/admin/logs', methods=['GET'])
@roles_required('Admin')
def get_logs():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT l.id, l.action, l.details, l.created_at, u.username, u.role
            FROM activity_logs l
            LEFT JOIN users u ON l.user_id = u.id
            ORDER BY l.created_at DESC LIMIT 100
        """)
        logs = cursor.fetchall()
        return jsonify(serialize_rows(logs))
    finally:
        cursor.close()
        conn.close()

@app.route('/api/admin/logs/clear', methods=['POST'])
@roles_required('Admin')
def clear_all_logs():
    """
    Purges BOTH the MySQL activity_logs database table AND physical log files in /logs/ directory.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM activity_logs")
        conn.commit()

        cleared_files = clear_external_log_files()

        log_security("LOGS_PURGED", user_id=session['user']['id'], username=session['user']['username'], role="Admin", status="SUCCESS", details=f"Purged database activity logs and files: {cleared_files}")
        log_activity_dual(session['user']['id'], "Admin", "Clear Logs", "system", f"All activity logs purged. External files emptied: {', '.join(cleared_files)}")

        return jsonify({
            "message": "Activity logs and physical log files successfully cleared.",
            "cleared_files": cleared_files
        })
    except Exception as e:
        conn.rollback()
        log_error(f"Error clearing system logs: {e}")
        return jsonify({"error": "Server Error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# ============================================================
# PATIENT ENDPOINTS
# ============================================================

@app.route('/api/patients', methods=['GET'])
@login_required
def get_patients():
    search = request.args.get('search', '').strip()
    sort_by = request.args.get('sort', 'patient_id')
    order = request.args.get('order', 'asc').lower()
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))
    offset = (page - 1) * limit

    allowed_sort = {
        'patient_id': 'patient_id',
        'full_name': 'full_name',
        'dob': 'dob',
        'created_at': 'created_at'
    }
    sort_col = allowed_sort.get(sort_by, 'patient_id')
    sort_order = 'DESC' if order == 'desc' else 'ASC'

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if search:
            query_str = """
                SELECT patient_id, full_name, dob, gender, phone, email, created_at 
                FROM patients
                WHERE patient_id LIKE %s OR full_name LIKE %s OR phone LIKE %s
                ORDER BY {} {}
                LIMIT %s OFFSET %s
            """.format(sort_col, sort_order)
            search_param = f"%{search}%"
            cursor.execute(query_str, (search_param, search_param, search_param, limit, offset))
            patients = cursor.fetchall()

            cursor.execute("""
                SELECT COUNT(*) FROM patients
                WHERE patient_id LIKE %s OR full_name LIKE %s OR phone LIKE %s
            """, (search_param, search_param, search_param))
            total = cursor.fetchone()['COUNT(*)']
        else:
            query_str = """
                SELECT patient_id, full_name, dob, gender, phone, email, created_at 
                FROM patients
                ORDER BY {} {}
                LIMIT %s OFFSET %s
            """.format(sort_col, sort_order)
            cursor.execute(query_str, (limit, offset))
            patients = cursor.fetchall()

            cursor.execute("SELECT COUNT(*) FROM patients")
            total = cursor.fetchone()['COUNT(*)']

        return jsonify({
            "patients": serialize_rows(patients),
            "total": total,
            "page": page,
            "limit": limit
        })
    finally:
        cursor.close()
        conn.close()

@app.route('/api/patients', methods=['POST'])
@roles_required('Receptionist', 'Admin')
def register_patient():
    data = request.get_json() or {}
    full_name = data.get('full_name', '').strip()
    dob = data.get('dob', '')
    gender = data.get('gender', '')
    phone = data.get('phone', '').strip()
    email = data.get('email', '').strip()
    address = data.get('address', '').strip()
    ec_name = data.get('emergency_contact_name', '').strip()
    ec_phone = data.get('emergency_contact_phone', '').strip()
    ec_relation = data.get('emergency_contact_relation', '').strip()

    if not all([full_name, dob, gender, phone, ec_name, ec_phone, ec_relation]):
        return jsonify({"error": "Bad Request", "message": "All required fields must be completed."}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT patient_id FROM patients ORDER BY patient_id DESC LIMIT 1")
        last_patient = cursor.fetchone()
        next_num = 1
        if last_patient:
            last_id = last_patient['patient_id']
            if last_id.startswith("PAT-"):
                try:
                    next_num = int(last_id.replace("PAT-", "")) + 1
                except ValueError:
                    pass
        patient_id = f"PAT-{next_num:04d}"

        cursor.execute("""
            INSERT INTO patients (
                patient_id, full_name, dob, gender, phone, email, address,
                emergency_contact_name, emergency_contact_phone, emergency_contact_relation, created_by
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            patient_id, full_name, dob, gender, phone, email if email else None, address if address else None,
            ec_name, ec_phone, ec_relation, session['user']['id']
        ))
        conn.commit()
        log_activity_dual(session['user']['id'], session['user']['role'], "Register Patient", f"patient:{patient_id}", {"patient_id": patient_id, "name": full_name})
        return jsonify({"message": "Patient registered successfully", "patient_id": patient_id}), 201
    finally:
        cursor.close()
        conn.close()

@app.route('/api/patients/<string:patient_id>', methods=['GET'])
@login_required
def get_patient_by_id(patient_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM patients WHERE patient_id = %s", (patient_id,))
        patient = cursor.fetchone()
        if not patient:
            return jsonify({"error": "Not Found", "message": "Patient not found."}), 404

        return jsonify(serialize_row(patient))
    finally:
        cursor.close()
        conn.close()

@app.route('/api/patients/<string:patient_id>', methods=['PUT'])
@roles_required('Receptionist', 'Admin')
def update_patient(patient_id):
    data = request.get_json() or {}
    full_name = data.get('full_name', '').strip()
    dob = data.get('dob', '')
    gender = data.get('gender', '')
    phone = data.get('phone', '').strip()
    email = data.get('email', '').strip()
    address = data.get('address', '').strip()
    ec_name = data.get('emergency_contact_name', '').strip()
    ec_phone = data.get('emergency_contact_phone', '').strip()
    ec_relation = data.get('emergency_contact_relation', '').strip()

    if not all([full_name, dob, gender, phone, ec_name, ec_phone, ec_relation]):
        return jsonify({"error": "Bad Request", "message": "All required fields must be completed."}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT patient_id FROM patients WHERE patient_id = %s", (patient_id,))
        if not cursor.fetchone():
            return jsonify({"error": "Not Found", "message": "Patient not found."}), 404

        cursor.execute("""
            UPDATE patients SET
                full_name = %s, dob = %s, gender = %s, phone = %s, email = %s, address = %s,
                emergency_contact_name = %s, emergency_contact_phone = %s, emergency_contact_relation = %s
            WHERE patient_id = %s
        """, (
            full_name, dob, gender, phone, email if email else None, address if address else None,
            ec_name, ec_phone, ec_relation, patient_id
        ))
        conn.commit()
        log_activity_dual(session['user']['id'], session['user']['role'], "Update Patient", f"patient:{patient_id}", {"patient_id": patient_id, "name": full_name})
        return jsonify({"message": "Patient details updated successfully"})
    finally:
        cursor.close()
        conn.close()

# Delete Patient (Receptionist, Admin)
@app.route('/api/patients/<string:patient_id>', methods=['DELETE'])
@roles_required('Receptionist', 'Admin')
def delete_patient(patient_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT full_name FROM patients WHERE patient_id = %s", (patient_id,))
        patient = cursor.fetchone()
        if not patient:
            return jsonify({"error": "Not Found", "message": "Patient not found."}), 404

        # Cascade deletion across related records
        cursor.execute("DELETE FROM appointments WHERE patient_id = %s", (patient_id,))
        cursor.execute("DELETE FROM diagnoses WHERE patient_id = %s", (patient_id,))
        cursor.execute("DELETE FROM prescriptions WHERE patient_id = %s", (patient_id,))
        cursor.execute("DELETE FROM vitals WHERE patient_id = %s", (patient_id,))
        cursor.execute("DELETE FROM ai_reports WHERE patient_id = %s", (patient_id,))
        cursor.execute("DELETE FROM patients WHERE patient_id = %s", (patient_id,))
        conn.commit()

        log_activity_dual(session['user']['id'], session['user']['role'], "Delete Patient", f"patient:{patient_id}", {"patient_id": patient_id, "name": patient['full_name']})
        return jsonify({"message": f"Patient '{patient['full_name']}' ({patient_id}) and all clinical records deleted successfully."})
    except Exception as e:
        conn.rollback()
        log_error(f"Failed to delete patient {patient_id}: {e}")
        return jsonify({"error": "Server Error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# Clear Patient History (Receptionist, Doctor, Admin)
@app.route('/api/patients/<string:patient_id>/history/clear', methods=['POST'])
@roles_required('Receptionist', 'Doctor', 'Admin')
def clear_patient_history(patient_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT full_name FROM patients WHERE patient_id = %s", (patient_id,))
        patient = cursor.fetchone()
        if not patient:
            return jsonify({"error": "Not Found", "message": "Patient not found."}), 404

        cursor.execute("DELETE FROM diagnoses WHERE patient_id = %s", (patient_id,))
        cursor.execute("DELETE FROM prescriptions WHERE patient_id = %s", (patient_id,))
        cursor.execute("DELETE FROM vitals WHERE patient_id = %s", (patient_id,))
        cursor.execute("DELETE FROM ai_reports WHERE patient_id = %s", (patient_id,))
        cursor.execute("DELETE FROM appointments WHERE patient_id = %s", (patient_id,))
        conn.commit()

        log_activity_dual(session['user']['id'], session['user']['role'], "Clear Patient History", f"patient:{patient_id}", {"patient_id": patient_id, "patient_name": patient['full_name']})
        return jsonify({"message": f"All historical clinical records, vitals, and reports for patient {patient_id} have been cleared."})
    except Exception as e:
        conn.rollback()
        log_error(f"Failed to clear patient history for {patient_id}: {e}")
        return jsonify({"error": "Server Error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# ============================================================
# CLINICAL ENDPOINTS (DOCTOR & ADMIN)
# ============================================================

@app.route('/api/patients/<string:patient_id>/clinical', methods=['GET'])
@roles_required('Doctor', 'Admin')
def get_clinical_records(patient_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT full_name FROM patients WHERE patient_id = %s", (patient_id,))
        if not cursor.fetchone():
            return jsonify({"error": "Not Found", "message": "Patient not found."}), 404

        cursor.execute("""
            SELECT d.id, d.diagnosis_text, d.symptoms, d.notes, d.created_at, u.full_name AS doctor_name
            FROM diagnoses d
            LEFT JOIN users u ON d.doctor_id = u.id
            WHERE d.patient_id = %s
            ORDER BY d.created_at DESC
        """, (patient_id,))
        diagnoses = cursor.fetchall()

        cursor.execute("""
            SELECT p.id, p.medication, p.dosage, p.frequency, p.duration, p.notes, p.created_at, u.full_name AS doctor_name
            FROM prescriptions p
            LEFT JOIN users u ON p.doctor_id = u.id
            WHERE p.patient_id = %s
            ORDER BY p.created_at DESC
        """, (patient_id,))
        prescriptions = cursor.fetchall()

        return jsonify({
            "diagnoses": serialize_rows(diagnoses),
            "prescriptions": serialize_rows(prescriptions)
        })
    finally:
        cursor.close()
        conn.close()

@app.route('/api/patients/<string:patient_id>/diagnoses', methods=['POST'])
@roles_required('Doctor', 'Admin')
def add_diagnosis(patient_id):
    data = request.get_json() or {}
    diagnosis_text = data.get('diagnosis_text', '').strip()
    symptoms = data.get('symptoms', '').strip()
    notes = data.get('notes', '').strip()

    if not diagnosis_text:
        return jsonify({"error": "Bad Request", "message": "Diagnosis field is required."}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT full_name FROM patients WHERE patient_id = %s", (patient_id,))
        if not cursor.fetchone():
            return jsonify({"error": "Not Found", "message": "Patient not found."}), 404

        cursor.execute("""
            INSERT INTO diagnoses (patient_id, doctor_id, diagnosis_text, symptoms, notes)
            VALUES (%s, %s, %s, %s, %s)
        """, (patient_id, session['user']['id'], diagnosis_text, symptoms if symptoms else None, notes if notes else None))
        conn.commit()
        diag_id = cursor.lastrowid
        log_activity_dual(session['user']['id'], session['user']['role'], "Add Diagnosis", f"patient:{patient_id}", {"diagnosis_id": diag_id, "diagnosis": diagnosis_text})
        return jsonify({"message": "Diagnosis recorded successfully.", "id": diag_id}), 201
    finally:
        cursor.close()
        conn.close()

# Delete Single Diagnosis (Doctor, Admin)
@app.route('/api/diagnoses/<int:diagnosis_id>', methods=['DELETE'])
@roles_required('Doctor', 'Admin')
def delete_diagnosis(diagnosis_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT patient_id, diagnosis_text FROM diagnoses WHERE id = %s", (diagnosis_id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Not Found", "message": "Diagnosis record not found."}), 404

        cursor.execute("DELETE FROM diagnoses WHERE id = %s", (diagnosis_id,))
        conn.commit()

        log_activity_dual(session['user']['id'], session['user']['role'], "Delete Diagnosis", f"patient:{row['patient_id']}", {"diagnosis_id": diagnosis_id, "diagnosis": row['diagnosis_text']})
        return jsonify({"message": "Diagnosis entry successfully deleted."})
    finally:
        cursor.close()
        conn.close()

# Clear All Diagnoses for Patient (Doctor, Admin)
@app.route('/api/patients/<string:patient_id>/diagnoses/clear', methods=['POST'])
@roles_required('Doctor', 'Admin')
def clear_patient_diagnoses(patient_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM diagnoses WHERE patient_id = %s", (patient_id,))
        conn.commit()
        log_activity_dual(session['user']['id'], session['user']['role'], "Clear Diagnoses", f"patient:{patient_id}", {"patient_id": patient_id})
        return jsonify({"message": f"All diagnoses for patient {patient_id} have been cleared."})
    finally:
        cursor.close()
        conn.close()

@app.route('/api/patients/<string:patient_id>/prescriptions', methods=['POST'])
@roles_required('Doctor', 'Admin')
def add_prescription(patient_id):
    data = request.get_json() or {}
    medication = data.get('medication', '').strip()
    dosage = data.get('dosage', '').strip()
    frequency = data.get('frequency', '').strip()
    duration = data.get('duration', '').strip()
    notes = data.get('notes', '').strip()

    if not all([medication, dosage, frequency, duration]):
        return jsonify({"error": "Bad Request", "message": "Medication, dosage, frequency, and duration are required."}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT full_name FROM patients WHERE patient_id = %s", (patient_id,))
        if not cursor.fetchone():
            return jsonify({"error": "Not Found", "message": "Patient not found."}), 404

        cursor.execute("""
            INSERT INTO prescriptions (patient_id, doctor_id, medication, dosage, frequency, duration, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (patient_id, session['user']['id'], medication, dosage, frequency, duration, notes if notes else None))
        conn.commit()
        presc_id = cursor.lastrowid
        log_activity_dual(session['user']['id'], session['user']['role'], "Add Prescription", f"patient:{patient_id}", {"prescription_id": presc_id, "medication": medication})
        return jsonify({"message": "Prescription added successfully.", "id": presc_id}), 201
    finally:
        cursor.close()
        conn.close()

# Delete Single Prescription (Doctor, Admin)
@app.route('/api/prescriptions/<int:prescription_id>', methods=['DELETE'])
@roles_required('Doctor', 'Admin')
def delete_prescription(prescription_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT patient_id, medication FROM prescriptions WHERE id = %s", (prescription_id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Not Found", "message": "Prescription record not found."}), 404

        cursor.execute("DELETE FROM prescriptions WHERE id = %s", (prescription_id,))
        conn.commit()

        log_activity_dual(session['user']['id'], session['user']['role'], "Delete Prescription", f"patient:{row['patient_id']}", {"prescription_id": prescription_id, "medication": row['medication']})
        return jsonify({"message": "Prescription successfully removed."})
    finally:
        cursor.close()
        conn.close()

# Clear All Prescriptions for Patient (Doctor, Admin)
@app.route('/api/patients/<string:patient_id>/prescriptions/clear', methods=['POST'])
@roles_required('Doctor', 'Admin')
def clear_patient_prescriptions(patient_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM prescriptions WHERE patient_id = %s", (patient_id,))
        conn.commit()
        log_activity_dual(session['user']['id'], session['user']['role'], "Clear Prescriptions", f"patient:{patient_id}", {"patient_id": patient_id})
        return jsonify({"message": f"Prescription history for patient {patient_id} has been cleared."})
    finally:
        cursor.close()
        conn.close()

# ============================================================
# VITALS ENDPOINTS (NURSE & DOCTOR & ADMIN)
# ============================================================

@app.route('/api/patients/<string:patient_id>/vitals', methods=['GET'])
@roles_required('Nurse', 'Doctor', 'Admin')
def get_vitals(patient_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT full_name FROM patients WHERE patient_id = %s", (patient_id,))
        if not cursor.fetchone():
            return jsonify({"error": "Not Found", "message": "Patient not found."}), 404

        cursor.execute("""
            SELECT v.*, u.full_name AS recorder_name, u.role AS recorder_role
            FROM vitals v
            LEFT JOIN users u ON v.recorded_by = u.id
            WHERE v.patient_id = %s
            ORDER BY v.created_at DESC
        """, (patient_id,))
        vitals = cursor.fetchall()
        return jsonify(serialize_rows(vitals))
    finally:
        cursor.close()
        conn.close()

@app.route('/api/patients/<string:patient_id>/vitals', methods=['POST'])
@roles_required('Nurse', 'Doctor', 'Admin')
def add_vitals(patient_id):
    data = request.get_json() or {}
    bp_sys = data.get('bp_systolic')
    bp_dia = data.get('bp_diastolic')
    temp = data.get('temperature')
    pulse = data.get('pulse_rate')
    weight = data.get('weight')
    height = data.get('height')
    notes = data.get('nursing_notes', '').strip()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT full_name FROM patients WHERE patient_id = %s", (patient_id,))
        if not cursor.fetchone():
            return jsonify({"error": "Not Found", "message": "Patient not found."}), 404

        sys_val = int(bp_sys) if bp_sys else None
        dia_val = int(bp_dia) if bp_dia else None
        temp_val = float(temp) if temp else None
        pulse_val = int(pulse) if pulse else None
        weight_val = float(weight) if weight else None
        height_val = float(height) if height else None

        cursor.execute("""
            INSERT INTO vitals (
                patient_id, recorded_by, bp_systolic, bp_diastolic,
                temperature, pulse_rate, weight, height, nursing_notes
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            patient_id, session['user']['id'], sys_val, dia_val,
            temp_val, pulse_val, weight_val, height_val, notes if notes else None
        ))
        conn.commit()
        log_activity_dual(session['user']['id'], session['user']['role'], "Log Vitals", f"patient:{patient_id}", {"bp": f"{sys_val}/{dia_val}", "pulse": pulse_val, "temp": temp_val})
        return jsonify({"message": "Vitals recorded successfully."}), 201
    finally:
        cursor.close()
        conn.close()

# Clear Vitals History for Patient (Doctor, Nurse, Admin)
@app.route('/api/patients/<string:patient_id>/vitals/clear', methods=['POST'])
@roles_required('Doctor', 'Nurse', 'Admin')
def clear_patient_vitals(patient_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM vitals WHERE patient_id = %s", (patient_id,))
        conn.commit()
        log_activity_dual(session['user']['id'], session['user']['role'], "Clear Vitals History", f"patient:{patient_id}", {"patient_id": patient_id})
        return jsonify({"message": f"Vitals history for patient {patient_id} has been cleared."})
    finally:
        cursor.close()
        conn.close()

# ============================================================
# AI DIAGNOSTIC PORTAL ENDPOINTS
# ============================================================

# 1. AI Radiology Analyzer (Doctor, Radiologist, Admin)
@app.route('/api/ai/radiology/analyze', methods=['POST'])
@roles_required('Doctor', 'Radiologist', 'Admin')
def ai_analyze_radiology():
    modality = request.form.get('modality', 'X-Ray')
    body_part = request.form.get('body_part', 'Chest')
    clinical_notes = request.form.get('clinical_notes', '')
    patient_id = request.form.get('patient_id', '').strip() or None

    image_path = None
    if 'image' in request.files:
        file = request.files['image']
        if file and allowed_file(file.filename):
            fname = f"radio_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{secure_filename(file.filename)}"
            fpath = os.path.join(app.config['UPLOAD_FOLDER'], fname)
            file.save(fpath)
            image_path = f"/uploads/{fname}"

    try:
        result = AIService.analyze_radiology(
            image_path=image_path,
            modality=modality,
            body_part=body_part,
            clinical_notes=clinical_notes
        )

        # Record analysis into ai_reports table as Pending
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                INSERT INTO ai_reports (patient_id, user_id, report_type, input_summary, image_path, ai_output, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                patient_id,
                session['user']['id'],
                'Radiology',
                f"{modality} - {body_part} ({clinical_notes[:100]})",
                image_path,
                json.dumps(result),
                'Pending'
            ))
            conn.commit()
            report_id = cursor.lastrowid
        finally:
            cursor.close()
            conn.close()

        log_activity_dual(
            session['user']['id'],
            session['user']['role'],
            "AI Radiology Analysis",
            f"ai_report:{report_id}",
            {"patient_id": patient_id, "modality": modality, "diagnosis": result.get("primary_diagnosis")}
        )

        return jsonify({
            "report_id": report_id,
            "analysis": result,
            "image_url": image_path,
            "provider": getattr(result, "get", lambda k: None)("provider", Config.AI_PROVIDER),
            "model": Config.AI_MODEL
        })
    except Exception as e:
        log_error(f"AI Radiology Analysis error: {e}")
        return jsonify({"error": "AI Analysis Failed", "message": str(e)}), 500

# 2. AI Lab Report Analyzer (Doctor, Lab Operator, Admin)
@app.route('/api/ai/lab/analyze', methods=['POST'])
@roles_required('Doctor', 'Lab Operator', 'Admin')
def ai_analyze_lab():
    test_type = request.form.get('test_type', 'Comprehensive Blood Panel')
    raw_text = request.form.get('raw_text', '')
    patient_id = request.form.get('patient_id', '').strip() or None

    file_path = None
    if 'lab_file' in request.files:
        file = request.files['lab_file']
        if file and allowed_file(file.filename):
            fname = f"lab_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{secure_filename(file.filename)}"
            fpath = os.path.join(app.config['UPLOAD_FOLDER'], fname)
            file.save(fpath)
            file_path = f"/uploads/{fname}"

    try:
        result = AIService.analyze_lab_report(
            raw_text=raw_text,
            file_path=file_path,
            test_type=test_type
        )

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                INSERT INTO ai_reports (patient_id, user_id, report_type, input_summary, image_path, ai_output, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                patient_id,
                session['user']['id'],
                'Lab',
                f"{test_type} - Text length: {len(raw_text)} chars",
                file_path,
                json.dumps(result),
                'Pending'
            ))
            conn.commit()
            report_id = cursor.lastrowid
        finally:
            cursor.close()
            conn.close()

        log_activity_dual(
            session['user']['id'],
            session['user']['role'],
            "AI Lab Analysis",
            f"ai_report:{report_id}",
            {"patient_id": patient_id, "test_type": test_type}
        )

        return jsonify({
            "report_id": report_id,
            "analysis": result,
            "file_url": file_path,
            "provider": getattr(result, "get", lambda k: None)("provider", Config.AI_PROVIDER),
            "model": Config.AI_MODEL
        })
    except Exception as e:
        log_error(f"AI Lab Analysis error: {e}")
        return jsonify({"error": "AI Analysis Failed", "message": str(e)}), 500

# 3. AI Clinical Decision Assistant (Doctor, Admin)
@app.route('/api/ai/clinical/assist', methods=['POST'])
@roles_required('Doctor', 'Admin')
def ai_clinical_assist():
    data = request.get_json() or {}
    patient_id = data.get('patient_id', '').strip() or None
    vitals = data.get('vitals', {})
    chief_complaint = data.get('chief_complaint', '')
    symptoms = data.get('symptoms', '')
    medical_history = data.get('medical_history', '')
    current_medications = data.get('current_medications', '')

    try:
        result = AIService.clinical_assistant(
            vitals=vitals,
            chief_complaint=chief_complaint,
            symptoms=symptoms,
            medical_history=medical_history,
            current_medications=current_medications
        )

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                INSERT INTO ai_reports (patient_id, user_id, report_type, input_summary, image_path, ai_output, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                patient_id,
                session['user']['id'],
                'Clinical_Assistant',
                f"Complaint: {chief_complaint[:80]} | Symptoms: {symptoms[:80]}",
                None,
                json.dumps(result),
                'Pending'
            ))
            conn.commit()
            report_id = cursor.lastrowid
        finally:
            cursor.close()
            conn.close()

        log_activity_dual(
            session['user']['id'],
            session['user']['role'],
            "AI Clinical Assistant",
            f"ai_report:{report_id}",
            {"patient_id": patient_id, "chief_complaint": chief_complaint}
        )

        return jsonify({
            "report_id": report_id,
            "suggestions": result,
            "provider": getattr(result, "get", lambda k: None)("provider", Config.AI_PROVIDER),
            "model": Config.AI_MODEL
        })
    except Exception as e:
        log_error(f"AI Clinical Assistant error: {e}")
        return jsonify({"error": "Clinical AI Assistant Failed", "message": str(e)}), 500

# 4. Accept AI Report (Doctor, Radiologist, Lab Operator, Admin)
@app.route('/api/ai/reports/<int:report_id>/accept', methods=['POST'])
@roles_required('Doctor', 'Radiologist', 'Lab Operator', 'Admin')
def accept_ai_report(report_id):
    data = request.get_json() or {}
    feedback_notes = data.get('feedback_notes', 'Verified by clinical specialist.')
    save_to_patient_record = data.get('save_to_patient_record', True)

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM ai_reports WHERE id = %s", (report_id,))
        report = cursor.fetchone()
        if not report:
            return jsonify({"error": "Not Found", "message": "AI report not found."}), 404

        # Role permission checks
        user_role = session['user']['role']
        if user_role == 'Radiologist' and report['report_type'] != 'Radiology':
            return jsonify({"error": "Forbidden", "message": "Radiologists can only accept Radiology AI reports."}), 403
        if user_role == 'Lab Operator' and report['report_type'] != 'Lab':
            return jsonify({"error": "Forbidden", "message": "Lab Operators can only accept Lab AI reports."}), 403

        # Update status
        cursor.execute("""
            UPDATE ai_reports SET status = 'Accepted', feedback_notes = %s WHERE id = %s
        """, (feedback_notes, report_id))

        # If report is attached to a patient and requested, optionally insert into diagnoses table
        patient_id = report.get('patient_id')
        if save_to_patient_record and patient_id:
            try:
                ai_output = json.loads(report['ai_output'])
                diag_text = ai_output.get('primary_diagnosis') or ai_output.get('primary_interpretation') or "AI-Assisted Diagnostic Finding"
                notes_text = f"Report Type: {report['report_type']}. Feedback: {feedback_notes}"
                
                # Check if patient exists
                cursor.execute("SELECT patient_id FROM patients WHERE patient_id = %s", (patient_id,))
                if cursor.fetchone():
                    cursor.execute("""
                        INSERT INTO diagnoses (patient_id, doctor_id, diagnosis_text, symptoms, notes)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (patient_id, session['user']['id'], f"[AI Verified] {diag_text}", report['input_summary'], notes_text))
            except Exception as pe:
                log_error(f"Failed to auto-append AI diagnosis to patient record: {pe}")

        conn.commit()
        log_activity_dual(
            session['user']['id'],
            session['user']['role'],
            "Accept AI Diagnosis",
            f"ai_report:{report_id}",
            {"report_type": report['report_type'], "patient_id": patient_id, "notes": feedback_notes}
        )

        return jsonify({"message": "AI Report accepted and verified successfully."})
    finally:
        cursor.close()
        conn.close()

# 5. Flag AI Report (Doctor, Radiologist, Lab Operator, Admin)
@app.route('/api/ai/reports/<int:report_id>/flag', methods=['POST'])
@roles_required('Doctor', 'Radiologist', 'Lab Operator', 'Admin')
def flag_ai_report(report_id):
    data = request.get_json() or {}
    reason = data.get('reason', '').strip()
    if not reason:
        return jsonify({"error": "Bad Request", "message": "A reason is required when flagging an AI diagnosis."}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM ai_reports WHERE id = %s", (report_id,))
        report = cursor.fetchone()
        if not report:
            return jsonify({"error": "Not Found", "message": "AI report not found."}), 404

        # Update status to Flagged_Incorrect
        cursor.execute("""
            UPDATE ai_reports SET status = 'Flagged_Incorrect', feedback_notes = %s WHERE id = %s
        """, (reason, report_id))
        conn.commit()

        log_activity_dual(
            session['user']['id'],
            session['user']['role'],
            "Flag AI Diagnosis",
            f"ai_report:{report_id}",
            {"report_type": report['report_type'], "flag_reason": reason}
        )

        return jsonify({"message": "AI Report flagged as incorrect. Clinical feedback logged."})
    finally:
        cursor.close()
        conn.close()

# 6. AI Diagnostic History (Doctor, Radiologist, Lab Operator, Admin)
@app.route('/api/ai/history', methods=['GET'])
@roles_required('Doctor', 'Radiologist', 'Lab Operator', 'Admin')
def get_ai_history():
    report_type = request.args.get('type', '').strip()
    status_filter = request.args.get('status', '').strip()
    search = request.args.get('search', '').strip()
    user_role = session['user']['role']

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Base query
        query = """
            SELECT r.id, r.patient_id, r.user_id, r.report_type, r.input_summary,
                   r.image_path, r.ai_output, r.status, r.feedback_notes, r.created_at,
                   u.full_name as specialist_name, u.role as specialist_role,
                   p.full_name as patient_name
            FROM ai_reports r
            LEFT JOIN users u ON r.user_id = u.id
            LEFT JOIN patients p ON r.patient_id = p.patient_id
            WHERE 1=1
        """
        params = []

        # Enforce role scoping
        if user_role == 'Radiologist':
            query += " AND r.report_type = 'Radiology'"
        elif user_role == 'Lab Operator':
            query += " AND r.report_type = 'Lab'"
        elif report_type:
            query += " AND r.report_type = %s"
            params.append(report_type)

        if status_filter:
            query += " AND r.status = %s"
            params.append(status_filter)

        if search:
            query += " AND (r.patient_id LIKE %s OR p.full_name LIKE %s OR r.input_summary LIKE %s)"
            sp = f"%{search}%"
            params.extend([sp, sp, sp])

        query += " ORDER BY r.created_at DESC LIMIT 100"

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        
        # Parse JSON ai_output for friendly client rendering
        for row in rows:
            try:
                row['ai_output_parsed'] = json.loads(row['ai_output']) if row.get('ai_output') else {}
            except Exception:
                row['ai_output_parsed'] = {}

        return jsonify(serialize_rows(rows))
    finally:
        cursor.close()
        conn.close()

# 7. Clear AI Report History (Doctor, Radiologist, Lab Operator, Admin)
@app.route('/api/ai/history/clear', methods=['POST'])
@roles_required('Doctor', 'Radiologist', 'Lab Operator', 'Admin')
def clear_ai_history():
    user_role = session['user']['role']
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if user_role == 'Radiologist':
            cursor.execute("DELETE FROM ai_reports WHERE report_type = 'Radiology'")
            msg = "All Radiology AI report history has been wiped."
        elif user_role == 'Lab Operator':
            cursor.execute("DELETE FROM ai_reports WHERE report_type = 'Lab'")
            msg = "All Laboratory AI report history has been wiped."
        else: # Doctor or Admin
            cursor.execute("DELETE FROM ai_reports")
            msg = "All AI diagnostic report history has been wiped."
            
        conn.commit()
        log_activity_dual(session['user']['id'], user_role, "Clear AI Report History", "ai_reports", msg)
        return jsonify({"message": msg})
    finally:
        cursor.close()
        conn.close()

# Static upload serve route
@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ============================================================
# DASHBOARD STATS ENDPOINT
# ============================================================

@app.route('/api/stats', methods=['GET'])
@login_required
def get_stats():
    role = session['user']['role']
    user_id = session['user']['id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    stats = {}
    try:
        cursor.execute("SELECT COUNT(*) FROM patients")
        stats["total_patients"] = cursor.fetchone()['COUNT(*)']

        if role == 'Admin':
            cursor.execute("SELECT COUNT(*) FROM users")
            stats["total_users"] = cursor.fetchone()['COUNT(*)']
            cursor.execute("SELECT COUNT(*) FROM users WHERE status = 1")
            stats["active_users"] = cursor.fetchone()['COUNT(*)']
            cursor.execute("SELECT COUNT(*) FROM activity_logs")
            stats["total_logs"] = cursor.fetchone()['COUNT(*)']
            cursor.execute("SELECT COUNT(*) FROM ai_reports")
            stats["total_ai_reports"] = cursor.fetchone()['COUNT(*)']
            
        elif role == 'Receptionist':
            today = datetime.date.today().isoformat()
            cursor.execute("SELECT COUNT(*) FROM patients WHERE DATE(created_at) = %s", (today,))
            stats["registered_today"] = cursor.fetchone()['COUNT(*)']
            cursor.execute("SELECT COUNT(*) FROM patients WHERE created_by = %s", (user_id,))
            stats["registered_by_me"] = cursor.fetchone()['COUNT(*)']

        elif role == 'Nurse':
            today = datetime.date.today().isoformat()
            cursor.execute("SELECT COUNT(*) FROM vitals WHERE DATE(created_at) = %s", (today,))
            stats["vitals_logged_today"] = cursor.fetchone()['COUNT(*)']
            cursor.execute("SELECT COUNT(*) FROM vitals WHERE recorded_by = %s", (user_id,))
            stats["vitals_logged_by_me"] = cursor.fetchone()['COUNT(*)']

        elif role == 'Doctor':
            today = datetime.date.today().isoformat()
            cursor.execute("SELECT COUNT(*) FROM diagnoses WHERE doctor_id = %s AND DATE(created_at) = %s", (user_id, today))
            stats["diagnoses_today"] = cursor.fetchone()['COUNT(*)']
            cursor.execute("SELECT COUNT(*) FROM prescriptions WHERE doctor_id = %s AND DATE(created_at) = %s", (user_id, today))
            stats["prescriptions_today"] = cursor.fetchone()['COUNT(*)']
            cursor.execute("SELECT COUNT(*) FROM diagnoses WHERE doctor_id = %s", (user_id,))
            stats["my_total_diagnoses"] = cursor.fetchone()['COUNT(*)']
            cursor.execute("SELECT COUNT(*) FROM ai_reports WHERE user_id = %s", (user_id,))
            stats["my_ai_analyses"] = cursor.fetchone()['COUNT(*)']

        elif role == 'Radiologist':
            cursor.execute("SELECT COUNT(*) FROM ai_reports WHERE report_type = 'Radiology'")
            stats["total_radiology_reports"] = cursor.fetchone()['COUNT(*)']
            cursor.execute("SELECT COUNT(*) FROM ai_reports WHERE report_type = 'Radiology' AND user_id = %s", (user_id,))
            stats["my_radiology_reports"] = cursor.fetchone()['COUNT(*)']
            cursor.execute("SELECT COUNT(*) FROM ai_reports WHERE report_type = 'Radiology' AND status = 'Accepted'")
            stats["accepted_radiology"] = cursor.fetchone()['COUNT(*)']

        elif role == 'Lab Operator':
            cursor.execute("SELECT COUNT(*) FROM ai_reports WHERE report_type = 'Lab'")
            stats["total_lab_reports"] = cursor.fetchone()['COUNT(*)']
            cursor.execute("SELECT COUNT(*) FROM ai_reports WHERE report_type = 'Lab' AND user_id = %s", (user_id,))
            stats["my_lab_reports"] = cursor.fetchone()['COUNT(*)']
            cursor.execute("SELECT COUNT(*) FROM ai_reports WHERE report_type = 'Lab' AND status = 'Accepted'")
            stats["accepted_lab"] = cursor.fetchone()['COUNT(*)']

        return jsonify(stats)
    finally:
        cursor.close()
        conn.close()

@app.route('/')
def index():
    return app.send_static_file('index.html')

if __name__ == '__main__':
    log_application("CareSync Flask Server starting on 127.0.0.1:5000")
    app.run(debug=True, host='127.0.0.1', port=5000)
