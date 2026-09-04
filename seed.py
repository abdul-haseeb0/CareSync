import mysql.connector
import os
import json
import logging
from datetime import datetime, date, timedelta
from config import Config
from models import Base, Role, User, Patient, Appointment, Diagnosis, Prescription, Vital, ActivityLog, AIReport, get_engine
from sqlalchemy.orm import sessionmaker
from logger_service import log_application, log_security, log_audit, log_error
import security

# Suppress passlib bcrypt warning
logging.getLogger("passlib").setLevel(logging.ERROR)

def ensure_database():
    cfg = Config.DB_CONFIG
    host = cfg.get("host", "localhost")
    port = int(cfg.get("port", 3306))
    user = cfg.get("user", "root")
    password = cfg.get("password", "")
    database = cfg.get("database", "hospital_system")
    
    print(f"Connecting to MySQL server at {host}:{port} using user '{user}'...")
    conn = mysql.connector.connect(
        host=host,
        port=port,
        user=user,
        password=password
    )
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    cursor.close()
    conn.close()
    print(f"Database '{database}' is ready and verified.")

def seed_database():
    print("Initializing tables via SQLAlchemy schema...")
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    print("All database tables and constraints created successfully.")

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 1. Seed Roles
        roles_data = [
            ("Admin", "Full administrative access to users, system logs, and configuration."),
            ("Doctor", "Access to patient clinical files, diagnoses, prescriptions, and all AI tools."),
            ("Nurse", "Access to patient registry and recording/viewing vital signs."),
            ("Receptionist", "Access to patient registration, updating contact details, and appointments."),
            ("Radiologist", "Restricted access to AI Radiology Analyzer and AI Diagnostic History."),
            ("Lab Operator", "Restricted access to AI Lab Report Analyzer and AI Diagnostic History.")
        ]
        for r_name, r_desc in roles_data:
            existing_role = session.query(Role).filter_by(name=r_name).first()
            if not existing_role:
                session.add(Role(name=r_name, description=r_desc))
        session.commit()
        print("Roles table seeded.")

        # 2. Seed Default Test Accounts with verified passlib bcrypt hashing
        users_data = [
            ("admin", "Admin@123456", "System Administrator", "Admin"),
            ("doctor1", "Doctor@123456", "Dr. Sarah Jenkins", "Doctor"),
            ("nurse1", "Nurse@123456", "Nurse Maria Santos", "Nurse"),
            ("receptionist1", "Recep@123456", "Alex Rivera (Reception)", "Receptionist"),
            ("radiologist1", "Radio@123456", "Dr. Elena Vance (Radiologist)", "Radiologist"),
            ("labop1", "LabOp@123456", "Marcus Chen (Lab Tech)", "Lab Operator"),
            ("doctor", "Doctor@123456", "Dr. Ahmed Mansoor", "Doctor"),
            ("nurse", "Nurse@123456", "Nurse Sara Ali", "Nurse"),
            ("reception", "Recep@123456", "Ali Reception", "Receptionist")
        ]

        created_users = {}
        for username, password, fullname, role in users_data:
            u = session.query(User).filter_by(username=username).first()
            hashed = security.get_password_hash(password)
            if not u:
                u = User(username=username, password_hash=hashed, full_name=fullname, role=role, status=True)
                session.add(u)
                session.flush()
                print(f"  + Created User: {username} ({role})")
            else:
                u.password_hash = hashed
                u.status = True
                u.role = role
                u.full_name = fullname
                session.flush()
                print(f"  ~ Synchronized User: {username} ({role})")
            created_users[username] = u
        session.commit()

        # 3. Seed Demo Patients
        patient_samples = [
            {
                "id": "PAT-0001",
                "name": "David Miller",
                "dob": date(1985, 4, 12),
                "gender": "Male",
                "phone": "+1 (555) 234-5678",
                "email": "david.miller@example.com",
                "address": "452 Elm Street, Springfield, IL",
                "ec_name": "Claire Miller",
                "ec_phone": "+1 (555) 234-5679",
                "ec_rel": "Spouse"
            },
            {
                "id": "PAT-0002",
                "name": "Emily Watson",
                "dob": date(1992, 9, 28),
                "gender": "Female",
                "phone": "+1 (555) 345-6789",
                "email": "emily.w@example.com",
                "address": "1204 Pine Ridge Ave, Chicago, IL",
                "ec_name": "Robert Watson",
                "ec_phone": "+1 (555) 345-6780",
                "ec_rel": "Father"
            },
            {
                "id": "PAT-0003",
                "name": "James Henderson",
                "dob": date(1968, 11, 3),
                "gender": "Male",
                "phone": "+1 (555) 456-7890",
                "email": "j.henderson@example.com",
                "address": "88 Oakwood Lane, Evanston, IL",
                "ec_name": "Martha Henderson",
                "ec_phone": "+1 (555) 456-7891",
                "ec_rel": "Spouse"
            }
        ]

        for p_data in patient_samples:
            p = session.query(Patient).filter_by(patient_id=p_data["id"]).first()
            if not p:
                p = Patient(
                    patient_id=p_data["id"],
                    full_name=p_data["name"],
                    dob=p_data["dob"],
                    gender=p_data["gender"],
                    phone=p_data["phone"],
                    email=p_data["email"],
                    address=p_data["address"],
                    emergency_contact_name=p_data["ec_name"],
                    emergency_contact_phone=p_data["ec_phone"],
                    emergency_contact_relation=p_data["ec_rel"],
                    created_by=created_users["receptionist1"].id
                )
                session.add(p)
                print(f"  + Created Patient: {p_data['id']} - {p_data['name']}")
        session.commit()

        # 4. Seed Vitals
        vitals_samples = [
            {
                "patient_id": "PAT-0001",
                "recorded_by": created_users["nurse1"].id,
                "bp_sys": 128,
                "bp_dia": 82,
                "temp": 37.2,
                "pulse": 76,
                "weight": 78.5,
                "height": 180.0,
                "notes": "Patient presents with persistent dry cough and mild chest tightness."
            },
            {
                "patient_id": "PAT-0002",
                "recorded_by": created_users["nurse1"].id,
                "bp_sys": 115,
                "bp_dia": 74,
                "temp": 36.8,
                "pulse": 68,
                "weight": 58.0,
                "height": 165.0,
                "notes": "Routine prenatal wellness check. Vitals stable."
            }
        ]
        for v_data in vitals_samples:
            existing_v = session.query(Vital).filter_by(patient_id=v_data["patient_id"]).first()
            if not existing_v:
                v = Vital(
                    patient_id=v_data["patient_id"],
                    recorded_by=v_data["recorded_by"],
                    bp_systolic=v_data["bp_sys"],
                    bp_diastolic=v_data["bp_dia"],
                    temperature=v_data["temp"],
                    pulse_rate=v_data["pulse"],
                    weight=v_data["weight"],
                    height=v_data["height"],
                    nursing_notes=v_data["notes"]
                )
                session.add(v)
        session.commit()

        # 5. Seed Clinical Diagnoses and Prescriptions
        existing_diag = session.query(Diagnosis).filter_by(patient_id="PAT-0001").first()
        if not existing_diag:
            d = Diagnosis(
                patient_id="PAT-0001",
                doctor_id=created_users["doctor1"].id,
                diagnosis_text="Mild Community-Acquired Bronchitis",
                symptoms="Substernal chest soreness on deep inspiration, dry cough x 4 days.",
                notes="Lungs clear bilaterally with slight end-expiratory wheeze. Advised rest and bronchodilator."
            )
            session.add(d)

            p = Prescription(
                patient_id="PAT-0001",
                doctor_id=created_users["doctor1"].id,
                medication="Amoxicillin 500mg",
                dosage="1 Capsule",
                frequency="Three times daily",
                duration="7 Days",
                notes="Take with food. Complete the full course of antibiotics."
            )
            session.add(p)
            session.commit()

        # 6. Seed Sample AI Reports
        existing_ai = session.query(AIReport).first()
        if not existing_ai:
            mock_radio_output = {
                "modality": "Chest X-Ray (PA View)",
                "body_part": "Chest / Lungs",
                "key_findings": [
                    "Bilateral clear lung fields with subtle focal opacity in the right lower lobe.",
                    "Cardiothoracic ratio normal (< 0.50).",
                    "No pleural effusion or pneumothorax."
                ],
                "primary_diagnosis": "Right Lower Lobe Community-Acquired Pneumonia (Early Stage)",
                "confidence_score": 0.94,
                "differential_diagnoses": [
                    {"condition": "Viral Bronchopneumonia", "probability": "Moderate", "notes": "Correlate with viral panel."},
                    {"condition": "Localized Atelectasis", "probability": "Low", "notes": "No mediastinal shift noted."}
                ],
                "treatment_suggestions": [
                    "Empiric oral antimicrobial coverage (Amoxicillin-Clavulanate).",
                    "Hydration, rest, and antipyretics."
                ],
                "recommended_next_steps": [
                    "Complete Blood Count (CBC) and CRP testing.",
                    "Follow-up chest radiograph in 4-6 weeks."
                ],
                "safety_warning": "⚠️ AI-Generated Analysis. Human-in-the-Loop required. Must be reviewed by a licensed medical professional."
            }
            
            ai_rep1 = AIReport(
                patient_id="PAT-0001",
                user_id=created_users["radiologist1"].id,
                report_type="Radiology",
                input_summary="Chest X-Ray (PA) - Right lower lobe assessment",
                image_path=None,
                ai_output=json.dumps(mock_radio_output),
                status="Accepted",
                feedback_notes="Confirmed by Dr. Elena Vance. Matches clinical presentation.",
                created_at=datetime.utcnow() - timedelta(hours=3)
            )
            session.add(ai_rep1)

            mock_lab_output = {
                "test_type": "Comprehensive Metabolic & Lipid Panel",
                "parameters": [
                    {"name": "Fasting Blood Glucose", "value": "138", "unit": "mg/dL", "reference_range": "70 - 99", "status": "High", "critical": False},
                    {"name": "HbA1c", "value": "7.4", "unit": "%", "reference_range": "< 5.7", "status": "High", "critical": False},
                    {"name": "Total Cholesterol", "value": "224", "unit": "mg/dL", "reference_range": "< 200", "status": "High", "critical": False},
                    {"name": "Serum Creatinine", "value": "0.9", "unit": "mg/dL", "reference_range": "0.7 - 1.3", "status": "Normal", "critical": False}
                ],
                "abnormal_findings_summary": [
                    "Elevated fasting glucose (138 mg/dL) and elevated HbA1c (7.4%)",
                    "Elevated total serum cholesterol (224 mg/dL)"
                ],
                "primary_interpretation": "Laboratory profile consistent with Type 2 Diabetes Mellitus with hypercholesterolemia.",
                "potential_causes": ["Type 2 Diabetes Mellitus", "Metabolic Syndrome"],
                "clinical_action_items": [
                    "Initiate Metformin 500mg daily titration",
                    "Nutritional and lifestyle modification consultation",
                    "Repeat HbA1c in 90 days"
                ],
                "safety_warning": "⚠️ AI-Generated Analysis. Human-in-the-Loop required. Must be reviewed by a licensed medical professional."
            }

            ai_rep2 = AIReport(
                patient_id="PAT-0003",
                user_id=created_users["labop1"].id,
                report_type="Lab",
                input_summary="Fasting Blood Profile - Metabolic Screening",
                image_path=None,
                ai_output=json.dumps(mock_lab_output),
                status="Pending",
                feedback_notes=None,
                created_at=datetime.utcnow() - timedelta(hours=1)
            )
            session.add(ai_rep2)
            session.commit()
            print("Sample AI Reports seeded.")

        # 7. Seed Initial Activity Logs & Audit Logs
        session.add(ActivityLog(
            user_id=created_users["admin"].id,
            action="System Initialization",
            details="CareSync Hospital Management System initialized with AI Diagnostic Portal & RBAC extension."
        ))
        session.commit()

        # Write to external log files
        log_application("Database initialized and verified with seed data.")
        log_security("SYSTEM_INIT", user_id=created_users["admin"].id, username="admin", role="Admin", status="SUCCESS", details="Database seed execution completed.")
        log_audit(
            user_id=created_users["admin"].id,
            user_role="Admin",
            action="SEED_DATABASE",
            target_resource="system",
            status="SUCCESS",
            details={"roles_seeded": len(roles_data), "users_seeded": len(users_data), "patients_seeded": len(patient_samples)}
        )

        print("\n========================================================")
        print("CareSync Database Seed Completed Successfully!")
        print("Test Accounts Ready (Password hashing verified with passlib):")
        print(" - Admin:        admin / Admin@123456")
        print(" - Doctor:       doctor1 / Doctor@123456 (also doctor / Doctor@123456)")
        print(" - Nurse:        nurse1 / Nurse@123456 (also nurse / Nurse@123456)")
        print(" - Receptionist: receptionist1 / Recep@123456 (also reception / Recep@123456)")
        print(" - Radiologist:  radiologist1 / Radio@123456")
        print(" - Lab Operator: labop1 / LabOp@123456")
        print("========================================================")

    except Exception as e:
        session.rollback()
        log_error(f"Failed to seed database: {e}")
        print(f"Error during database seed: {e}")
        raise e
    finally:
        session.close()

if __name__ == "__main__":
    ensure_database()
    seed_database()
