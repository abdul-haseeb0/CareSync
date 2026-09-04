# 🏥 AI-Powered Hospital Management System (HMS)

[![FastAPI](https://img.shields.io/badge/FastAPI-0.141.1-009688.svg?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg?style=flat-square&logo=python)](https://www.python.org/)
[![MySQL](https://img.shields.io/badge/MySQL-9.7.1-4479A1.svg?style=flat-square&logo=mysql)](https://www.mysql.com/)
[![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-3.4-38B2AC.svg?style=flat-square&logo=tailwind-css)](https://tailwindcss.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)
[![Security](https://img.shields.io/badge/RBAC-Enforced-red.svg?style=flat-square)](https://github.com/)

> **Academic Prototype Disclaimer**  
> This project was developed as an **academic prototype** with **AI assistance** to demonstrate end-to-end full-stack software development, role-based access control (RBAC), healthcare privacy compliance, and human-in-the-loop AI integration. It is designed for educational and demonstration purposes.

---

## 📌 Table of Contents

- [Overview](#-overview)
- [Key Features & Role Access Matrix](#-key-features--role-access-matrix)
- [AI Integration & Human-in-the-Loop](#-ai-integration--human-in-the-loop)
- [Security Controls & Risk Management](#-security-controls--risk-management)
- [Logging & Audit Architecture](#-logging--audit-architecture)
- [Tech Stack](#-tech-stack)
- [Installation & Local Setup](#-installation--local-setup)
- [Default Demo Credentials](#-default-demo-credentials)
- [Project Directory Structure](#-project-directory-structure)
- [License](#-license)

---

## 📸 Overview

The **AI-Powered Hospital Management System (HMS)** is a full-stack web application designed for healthcare facilities. It streamlines clinical workflows, manages electronic health records (EHR), schedules appointments, issues prescriptions, and incorporates cutting-edge **AI Diagnostic Assistance** for radiology and pathology analysis with mandatory professional oversight.

---

## 👥 Key Features & Role Access Matrix

The system enforces strict server-side **Least-Privilege Role-Based Access Control (RBAC)** across six distinct user roles:

| Feature / Module | Admin | Doctor | Nurse | Receptionist | Radiologist | Lab Operator |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Staff & User Account Management** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **System Audit & External Log Clearing** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Patient Registration & Profile Edits** | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| **Appointment Scheduling & Status Toggle** | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| **Prescription Management (Add/Remove)** | ✅ | ✅ | 👁️ View Only | ❌ | ❌ | ❌ |
| **Clinical & Nursing Notes** | ✅ | ✅ Notes | ✅ Vitals | ❌ | ❌ | ❌ |
| **AI Radiology Analyzer (X-Ray/MRI/CT)** | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ |
| **AI Lab Report Analyzer (Blood/Pathology)**| ✅ | ✅ | ❌ | ❌ | ❌ | ✅ |
| **AI Clinical Decision Assistant** | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Accept AI / Flag Incorrect Reports** | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ |

---

## 🧠 AI Integration & Human-in-the-Loop

The system integrates an **AI Diagnostic Portal** designed to assist medical personnel while maintaining strict safety controls:

1. **AI Radiology Analyzer:** Accepts DICOM, PNG, JPG, and WEBP image uploads. Generates key observations, primary and differential diagnoses, and treatment recommendations.
2. **AI Lab Report Analyzer:** Parses pathology data, blood panels, and urinalysis text or PDFs to flag critical out-of-range values and interpret findings.
3. **AI Clinical Decision Assistant:** Integrated into the Doctor Workspace to evaluate patient vitals, symptoms, and medical history to suggest treatment plans.
4. **Human-in-the-Loop (HITL) Workflow:**  
   - Every AI analysis outputs a mandatory warning:  
     > *`⚠️ AI-Generated Analysis. Human-in-the-Loop required. Must be reviewed by a licensed medical professional.`*
   - Medical professionals must explicitly choose to **"Accept AI Diagnosis"** (saving it to the patient record) or **"Flag as Incorrect / Malicious"** (prompting a feedback model and logging the disagreement).
5. **Zero-Crash Graceful Fallback:** If no valid `AI_API_KEY` is provided in the configuration, the system automatically transitions to a structured, realistic local mock generator—preventing server errors.

---

## 🛡️ Security Controls & Risk Management

Healthcare applications handle Sensitive Personal Data (SPD) and Protected Health Information (PHI). The table below outlines how specific cyber risks are managed:

| Threat / Risk Vector | Severity | Implemented Security Control |
| :--- | :---: | :--- |
| **Unauthorized Data Access** | `CRITICAL` | Server-side JWT validation in `HttpOnly`, `SameSite=Lax` cookies; strict RBAC middleware on every endpoint. |
| **SQL Injection (SQLi)** | `CRITICAL` | Complete parameterized queries and object-relational mapping (ORM) via SQLAlchemy. Raw SQL string concatenation is strictly prohibited. |
| **Cross-Site Request Forgery (CSRF)** | `HIGH` | Custom anti-CSRF token verification required on state-changing API requests (`POST`, `PUT`, `DELETE`). |
| **Brute-Force Login Attacks** | `HIGH` | IP-based request rate-limiting implemented via `slowapi` (e.g., maximum 5 login attempts per minute). |
| **Credential & Secret Exposure** | `HIGH` | Passwords hashed using `bcrypt` (work factor 12). All DB/API keys stored in environment variables (`.env`). Secrets excluded from git. |
| **Privilege Escalation** | `HIGH` | Role checks executed strictly at the backend level. Frontend UI element toggling is purely cosmetic. |
| **Cross-Site Scripting (XSS)** | `MEDIUM` | HTML escaping across all Jinja2 templates, output sanitization, and strict HttpOnly cookie storage for session tokens. |
| **Data Pollution / Invalidation** | `MEDIUM` | Logical soft-deletion (`is_deleted` flags) for audit persistence; multi-step operations protected with DB transactions. |

---

## 📂 Logging & Audit Architecture

The application enforces a **Dual-Layer Audit Trail**:

### 1. Database Audit Trail (`audit_logs` table)
Records critical actions (logins, staff updates, patient modifications, prescription changes, AI report accept/flag decisions, and log clear events) with user context, IP address, and timestamp.

### 2. External File Logging (`logs/` directory)
Structured log files are maintained with automatic size-based log rotation:
- `logs/application.log`: Application lifecycle, routing activity, and system state changes.
- `logs/security.log`: Authentication attempts, rate-limiting triggers, and unauthorized access attempts.
- `logs/audit.log`: JSON-lines structured entries recording every data mutation.
- `logs/error.log`: Exception stack traces and unhandled system failures.

---

## 🛠️ Tech Stack

- **Backend:** Python 3.11+, FastAPI, Uvicorn, SQLAlchemy ORM, Pydantic, Passlib (bcrypt), PyJWT, SlowAPI.
- **Frontend:** HTML5, Jinja2 Templates, Tailwind CSS, Vanilla JavaScript (ES6+), Server-Sent Events (SSE).
- **Database:** MySQL 8.0+ (PyMySQL driver).
- **AI Engine:** OpenAI API Integration (with automatic mock fallback).

---

## 🚀 Installation & Local Setup

Follow these steps to set up and run the application locally on your computer using your own installed MySQL server.

### Prerequisites
- Python 3.11 or higher
- MySQL Server 8.0+ running locally (e.g., via MySQL Workbench, XAMPP, or MySQL CLI)

---

### Step 1: Clone the Repository
```bash
git clone [https://github.com/your-username/hospital-management-system.git](https://github.com/your-username/hospital-management-system.git)
cd hospital-management-system
