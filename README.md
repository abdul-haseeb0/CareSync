# 🏥 CareSync — AI-Powered Hospital Management System (HMS)

<p align="left">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white">
  <img alt="MySQL" src="https://img.shields.io/badge/MySQL-8.0%2B-4479A1?logo=mysql&logoColor=white">
  <img alt="TailwindCSS" src="https://img.shields.io/badge/TailwindCSS-Frontend-38B2AC?logo=tailwindcss&logoColor=white">
  <img alt="License" src="https://img.shields.io/badge/License-MIT-yellow.svg">
  <img alt="Security" src="https://img.shields.io/badge/Security-RBAC%20%7C%20bcrypt-critical">
  <img alt="Status" src="https://img.shields.io/badge/Status-Academic%20Prototype-informational">
</p>

> ### ⚠️ Academic Prototype Disclaimer
> This project was developed as an **academic prototype with AI assistance** to demonstrate end-to-end full-stack software development, role-based access control (RBAC), healthcare privacy compliance, and human-in-the-loop AI integration. It is designed strictly for **educational and demonstration purposes** and is not intended for use with real patient data.

---

## 📌 Table of Contents

- [Overview](#-overview)
- [Key Features & Role Access Matrix](#-key-features--role-access-matrix)
- [AI Integration & Human-in-the-Loop](#-ai-integration--human-in-the-loop)
- [Security Controls & Risk Management](#️-security-controls--risk-management)
- [Logging & Audit Architecture](#-logging--audit-architecture)
- [Tech Stack](#️-tech-stack)
- [Installation & Local Setup](#-installation--local-setup)
- [Default Demo Credentials](#-default-demo-credentials)
- [License](#-license)

---

## 📸 Overview

**CareSync** is a full-stack Hospital Management System (HMS) designed for healthcare facilities. It streamlines clinical workflows, manages electronic health records (EHR), schedules appointments, issues prescriptions, and incorporates cutting-edge **AI Diagnostic Assistance** for radiology and pathology analysis — with mandatory professional oversight built into every step.

---

## 👥 Key Features & Role Access Matrix

The system enforces strict server-side **Least-Privilege Role-Based Access Control (RBAC)** across six distinct user roles:

| Feature / Module | Admin | Doctor | Nurse | Receptionist | Radiologist | Lab Operator |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Staff & User Account Management | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| System Audit & External Log Clearing | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Patient Registration & Profile Edits | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| Appointment Scheduling & Status Toggle | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| Prescription Management (Add/Remove) | ✅ | ✅ | 👁️ View Only | ❌ | ❌ | ❌ |
| Clinical & Nursing Notes | ✅ | ✅ Notes | ✅ Vitals | ❌ | ❌ | ❌ |
| AI Radiology Analyzer (X-Ray/MRI/CT) | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ |
| AI Lab Report Analyzer (Blood/Pathology) | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ |
| AI Clinical Decision Assistant | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Accept AI / Flag Incorrect Reports | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ |

---

## 🧠 AI Integration & Human-in-the-Loop

CareSync integrates an **AI Diagnostic Portal** designed to assist medical personnel while maintaining strict safety controls:

- **AI Radiology Analyzer** — Accepts DICOM, PNG, JPG, and WEBP image uploads. Generates key observations, primary and differential diagnoses, and treatment recommendations.
- **AI Lab Report Analyzer** — Parses pathology data, blood panels, and urinalysis text or PDFs to flag critical out-of-range values and interpret findings.
- **AI Clinical Decision Assistant** — Integrated into the Doctor Workspace to evaluate patient vitals, symptoms, and medical history to suggest treatment plans.

### Human-in-the-Loop (HITL) Workflow

Every AI analysis outputs a mandatory warning:

> ⚠️ **AI-Generated Analysis. Human-in-the-Loop required.** Must be reviewed by a licensed medical professional.

Medical professionals must explicitly choose to **"Accept AI Diagnosis"** (saving it to the patient record) or **"Flag as Incorrect / Malicious"** (prompting a feedback model and logging the disagreement).

**Zero-Crash Graceful Fallback:** If no valid `AI_API_KEY` is provided in the configuration, the system automatically transitions to a structured, realistic local mock generator — preventing server errors.

---

## 🛡️ Security Controls & Risk Management

Healthcare applications handle Sensitive Personal Data (SPD) and Protected Health Information (PHI). The table below outlines how specific cyber risks are managed:

| Threat / Risk Vector | Severity | Implemented Security Control |
|---|:---:|---|
| Unauthorized Data Access | 🔴 CRITICAL | Server-side JWT validation in `HttpOnly`, `SameSite=Lax` cookies; strict RBAC middleware on every endpoint. |
| SQL Injection (SQLi) | 🔴 CRITICAL | Complete parameterized queries and ORM via SQLAlchemy. Raw SQL string concatenation is strictly prohibited. |
| Cross-Site Request Forgery (CSRF) | 🟠 HIGH | Custom anti-CSRF token verification required on state-changing API requests (POST, PUT, DELETE). |
| Brute-Force Login Attacks | 🟠 HIGH | IP-based request rate-limiting via `slowapi` (e.g., max 5 login attempts per minute). |
| Credential & Secret Exposure | 🟠 HIGH | Passwords hashed using `bcrypt` (work factor 12). All DB/API keys stored in environment variables (`.env`). Secrets excluded from git. |
| Privilege Escalation | 🟠 HIGH | Role checks executed strictly at the backend level. Frontend UI element toggling is purely cosmetic. |
| Cross-Site Scripting (XSS) | 🟡 MEDIUM | HTML escaping across all Jinja2 templates, output sanitization, and strict `HttpOnly` cookie storage for session tokens. |
| Data Pollution / Invalidation | 🟡 MEDIUM | Logical soft-deletion (`is_deleted` flags) for audit persistence; multi-step operations protected with DB transactions. |

---

## 📂 Logging & Audit Architecture

CareSync enforces a **Dual-Layer Audit Trail**:

### 1. Database Audit Trail (`audit_logs` table)
Records critical actions (logins, staff updates, patient modifications, prescription changes, AI report accept/flag decisions, and log clear events) with user context, IP address, and timestamp.

### 2. External File Logging (`logs/` directory)
Structured log files are maintained with automatic size-based log rotation:

- `logs/application.log` — Application lifecycle, routing activity, and system state changes.
- `logs/security.log` — Authentication attempts, rate-limiting triggers, and unauthorized access attempts.
- `logs/audit.log` — JSON-lines structured entries recording every data mutation.
- `logs/error.log` — Exception stack traces and unhandled system failures.

---

## 🛠️ Tech Stack

| Layer | Technologies |
|---|---|
| **Backend** | Python 3.11+, FastAPI, Uvicorn, SQLAlchemy ORM, Pydantic, Passlib (bcrypt) |
| **Frontend** | HTML5, Jinja2 Templates, Tailwind CSS, Vanilla JavaScript (ES6+) |
| **Database** | MySQL 8.0+ (PyMySQL driver) |
| **AI Engine** | API Integration (with automatic mock fallback) |

---

## 🚀 Installation & Local Setup

Follow these steps to set up and run CareSync locally on your machine using your own installed MySQL server.

### Prerequisites
- Python 3.11 or higher
- MySQL Server 8.0+ running locally (e.g., via MySQL Workbench, XAMPP, or MySQL CLI)
- bcrypt 4.0.1

### Step 1: Clone the Repository

```bash
git clone https://github.com/your-username/caresync.git
cd caresync
```

### Step 2: Create a Virtual Environment

**Windows:**
```bash
python -m venv venv
```

**macOS / Linux:**
```bash
python3 -m venv venv
```

### Step 3: Activate the Virtual Environment

**Windows (Command Prompt):**
```bash
venv\Scripts\activate
```

**Windows (PowerShell):**
```bash
venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
source venv/bin/activate
```

> Once activated, your terminal prompt should be prefixed with `(venv)`.

### Step 4: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 5: Pre-Setup Configuration (Required Before Running)

Before starting the application, configure your database connection and AI API key. You have **two options**:

**Option A — Edit `config.py` directly**
Open `config.py` and fill in your MySQL credentials and AI API key:
```python
DB_HOST = "localhost"
DB_PORT = 3306
DB_USER = "root"
DB_PASSWORD = "your_mysql_password"
DB_NAME = "caresync_db"

AI_API_KEY = "your_api_key"   # Leave blank to use the local mock fallback
```

**Option B — Use a `.env` file (recommended)**
Copy the provided `.env.example` to `.env` and fill in your own values:
```bash
cp .env.example .env      # macOS/Linux
copy .env.example .env    # Windows
```

`.env.example`:
```env
# ---- Database Configuration ----
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=caresync_db

# ---- Security ----
SECRET_KEY=your_jwt_secret_key

# ---- AI Integration ----
AI_API_KEY=your_openai_api_key
AI_MODEL=gpt-4o-mini
```

> 🔒 Never commit your real `.env` file to version control — only `.env.example` should be tracked in git.

### Step 6: Seed the Database

Populate the database with initial roles, demo staff accounts, and sample data:

```bash
python seed.py
```

### Step 7: Run the Application

```bash
python app.py
```

**Expected output:**
```
[2026-09-05 16:15:53] [INFO] [application] CareSync Flask Server starting on 127.0.0.1:5000
 * Serving Flask app 'app'
 * Debug mode: on
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on http://127.0.0.1:5000
Press CTRL+C to quit
 * Restarting with watchdog (windowsapi)
[2026-09-05 16:15:54] [INFO] [application] CareSync Flask Server starting on 127.0.0.1:5000
 * Debugger is active!
 * Debugger PIN: 239-257-274
```

### Step 8: Access the Application

Open your browser and navigate to:

```
http://127.0.0.1:5000
```

---

## 🔑 Default Demo Credentials

> ⚠️ Update this table with the actual demo accounts created by `seed.py`. Example format below:

| Role | Username / Email | Password |
|---|---|---|
| Admin | admin | *(set by seed.py)* |
| Doctor | doctor | *(set by seed.py)* |
| Nurse | nurse | *(set by seed.py)* |
| Receptionist | reception | *(set by seed.py)* |
| Radiologist | radiologist1 | *(set by seed.py)* |
| Lab Operator | labop | *(set by seed.py)* |

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

<p align="center">Built with ❤️ as an academic prototype demonstrating secure, AI-assisted healthcare software.</p>
