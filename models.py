from sqlalchemy import create_engine, Column, Integer, String, Text, Date, DateTime, Boolean, ForeignKey, Numeric
from sqlalchemy.dialects.mysql import INTEGER
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime
from config import Config

Base = declarative_base()

class Role(Base):
    __tablename__ = 'roles'
    id = Column(INTEGER(unsigned=True), primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(255), nullable=True)

class User(Base):
    __tablename__ = 'users'
    id = Column(INTEGER(unsigned=True), primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(String(30), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(Boolean, default=True, nullable=False)

class Patient(Base):
    __tablename__ = 'patients'
    patient_id = Column(String(20), primary_key=True)
    full_name = Column(String(100), nullable=False)
    dob = Column(Date, nullable=False)
    gender = Column(String(10), nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(100), nullable=True)
    address = Column(Text, nullable=True)
    emergency_contact_name = Column(String(100), nullable=False)
    emergency_contact_phone = Column(String(20), nullable=False)
    emergency_contact_relation = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(INTEGER(unsigned=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

class Appointment(Base):
    __tablename__ = 'appointments'
    id = Column(INTEGER(unsigned=True), primary_key=True, autoincrement=True)
    patient_id = Column(String(20), ForeignKey('patients.patient_id', ondelete='CASCADE'), nullable=False)
    doctor_id = Column(INTEGER(unsigned=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    appointment_date = Column(DateTime, nullable=False)
    department = Column(String(100), default='General Medicine')
    status = Column(String(30), default='Scheduled') # Scheduled, Completed, Cancelled
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Diagnosis(Base):
    __tablename__ = 'diagnoses'
    id = Column(INTEGER(unsigned=True), primary_key=True, autoincrement=True)
    patient_id = Column(String(20), ForeignKey('patients.patient_id', ondelete='CASCADE'), nullable=False)
    doctor_id = Column(INTEGER(unsigned=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    diagnosis_text = Column(Text, nullable=False)
    symptoms = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Prescription(Base):
    __tablename__ = 'prescriptions'
    id = Column(INTEGER(unsigned=True), primary_key=True, autoincrement=True)
    patient_id = Column(String(20), ForeignKey('patients.patient_id', ondelete='CASCADE'), nullable=False)
    doctor_id = Column(INTEGER(unsigned=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    medication = Column(String(150), nullable=False)
    dosage = Column(String(50), nullable=False)
    frequency = Column(String(50), nullable=False)
    duration = Column(String(50), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Vital(Base):
    __tablename__ = 'vitals'
    id = Column(INTEGER(unsigned=True), primary_key=True, autoincrement=True)
    patient_id = Column(String(20), ForeignKey('patients.patient_id', ondelete='CASCADE'), nullable=False)
    recorded_by = Column(INTEGER(unsigned=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    bp_systolic = Column(Integer, nullable=True)
    bp_diastolic = Column(Integer, nullable=True)
    temperature = Column(Numeric(4, 1), nullable=True)
    pulse_rate = Column(Integer, nullable=True)
    weight = Column(Numeric(5, 2), nullable=True)
    height = Column(Numeric(5, 2), nullable=True)
    nursing_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class ActivityLog(Base):
    __tablename__ = 'activity_logs'
    id = Column(INTEGER(unsigned=True), primary_key=True, autoincrement=True)
    user_id = Column(INTEGER(unsigned=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    action = Column(String(255), nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class AIReport(Base):
    __tablename__ = 'ai_reports'
    id = Column(INTEGER(unsigned=True), primary_key=True, autoincrement=True)
    patient_id = Column(String(20), ForeignKey('patients.patient_id', ondelete='CASCADE'), nullable=True)
    user_id = Column(INTEGER(unsigned=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    report_type = Column(String(50), nullable=False) # 'Radiology', 'Lab', 'Clinical_Assistant'
    input_summary = Column(Text, nullable=True)
    image_path = Column(String(255), nullable=True)
    ai_output = Column(Text, nullable=False) # Structured JSON string
    status = Column(String(30), default='Pending', nullable=False) # 'Pending', 'Accepted', 'Flagged_Incorrect'
    feedback_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

def get_engine():
    cfg = Config.DB_CONFIG
    uri = f"mysql+mysqlconnector://{cfg['user']}:{cfg['password']}@{cfg['host']}:{cfg['port'] if 'port' in cfg else 3306}/{cfg['database']}"
    return create_engine(uri, echo=False)
