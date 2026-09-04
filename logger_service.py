import os
import json
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

# Formatters
STANDARD_FORMATTER = logging.Formatter(
    '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def _setup_logger(name, filename, level=logging.INFO, formatter=STANDARD_FORMATTER):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False
    
    # Avoid duplicate handlers if reloaded
    if not logger.handlers:
        filepath = os.path.join(LOGS_DIR, filename)
        handler = RotatingFileHandler(filepath, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # Also log to console for development visibility
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
    return logger

app_logger = _setup_logger('application', 'application.log')
sec_logger = _setup_logger('security', 'security.log')
audit_file_logger = _setup_logger('audit', 'audit.log')
err_logger = _setup_logger('error', 'error.log', level=logging.ERROR)

def log_application(message, level='info'):
    if level == 'warning':
        app_logger.warning(message)
    elif level == 'error':
        app_logger.error(message)
    else:
        app_logger.info(message)

def log_security(event, user_id=None, username=None, role=None, ip_address=None, status='SUCCESS', details=''):
    entry = f"Event: {event} | UserID: {user_id} | Username: {username} | Role: {role} | IP: {ip_address} | Status: {status} | Details: {details}"
    sec_logger.info(entry)

def log_audit(user_id=None, user_role=None, action=None, target_resource=None, ip_address=None, status='SUCCESS', details=None):
    audit_data = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "user_id": user_id,
        "user_role": user_role,
        "action": action,
        "target_resource": target_resource,
        "ip_address": ip_address,
        "status": status,
        "details": details or {}
    }
    # JSON-Lines formatting for audit.log
    audit_file_logger.info(json.dumps(audit_data))

def log_error(message, exc_info=True):
    err_logger.error(message, exc_info=exc_info)

def clear_external_log_files():
    """
    Empties the physical log files in LOGS_DIR (application.log, security.log, audit.log, error.log).
    """
    log_files = ['application.log', 'security.log', 'audit.log', 'error.log']
    cleared = []
    for fname in log_files:
        fpath = os.path.join(LOGS_DIR, fname)
        if os.path.exists(fpath):
            try:
                with open(fpath, 'w', encoding='utf-8') as f:
                    f.truncate(0)
                cleared.append(fname)
            except Exception as e:
                log_error(f"Failed to clear log file {fname}: {e}")
    return cleared
