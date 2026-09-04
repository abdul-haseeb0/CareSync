import mysql.connector
from config import Config
import bcrypt

def hash_password(password):
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

def get_db_connection(include_db=True):
    cfg = Config.DB_CONFIG
    if include_db:
        return mysql.connector.connect(
            host=cfg["host"],
            user=cfg["user"],
            password=cfg["password"],
            database=cfg["database"]
        )
    else:
        return mysql.connector.connect(
            host=cfg["host"],
            user=cfg["user"],
            password=cfg["password"]
        )

def setup_database():
    print("Connecting to MySQL...")
    # First connect without database to ensure it exists
    conn = get_db_connection(include_db=False)
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {Config.DB_CONFIG['database']}")
    cursor.close()
    conn.close()
    print(f"Database '{Config.DB_CONFIG['database']}' ensured.")

    # Now connect to the database to create tables
    conn = get_db_connection(include_db=True)
    cursor = conn.cursor()

    # Create users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(50) NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        full_name VARCHAR(100) NOT NULL,
        role VARCHAR(30) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TINYINT(1) NOT NULL DEFAULT 1
    )
    """)
    print("Table 'users' ensured.")

    # Create patients table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS patients (
        patient_id VARCHAR(20) PRIMARY KEY,
        full_name VARCHAR(100) NOT NULL,
        dob DATE NOT NULL,
        gender VARCHAR(10) NOT NULL,
        phone VARCHAR(20) NOT NULL,
        email VARCHAR(100),
        address TEXT,
        emergency_contact_name VARCHAR(100) NOT NULL,
        emergency_contact_phone VARCHAR(20) NOT NULL,
        emergency_contact_relation VARCHAR(50) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        created_by INT UNSIGNED,
        FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
    )
    """)
    print("Table 'patients' ensured.")

    # Create diagnoses table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS diagnoses (
        id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        patient_id VARCHAR(20) NOT NULL,
        doctor_id INT UNSIGNED,
        diagnosis_text TEXT NOT NULL,
        symptoms TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE,
        FOREIGN KEY (doctor_id) REFERENCES users(id) ON DELETE SET NULL
    )
    """)
    print("Table 'diagnoses' ensured.")

    # Create prescriptions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS prescriptions (
        id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        patient_id VARCHAR(20) NOT NULL,
        doctor_id INT UNSIGNED,
        medication VARCHAR(150) NOT NULL,
        dosage VARCHAR(50) NOT NULL,
        frequency VARCHAR(50) NOT NULL,
        duration VARCHAR(50) NOT NULL,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE,
        FOREIGN KEY (doctor_id) REFERENCES users(id) ON DELETE SET NULL
    )
    """)
    print("Table 'prescriptions' ensured.")

    # Create vitals table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vitals (
        id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        patient_id VARCHAR(20) NOT NULL,
        recorded_by INT UNSIGNED,
        bp_systolic INT,
        bp_diastolic INT,
        temperature DECIMAL(4,1),
        pulse_rate INT,
        weight DECIMAL(5,2),
        height DECIMAL(5,2),
        nursing_notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE,
        FOREIGN KEY (recorded_by) REFERENCES users(id) ON DELETE SET NULL
    )
    """)
    print("Table 'vitals' ensured.")

    # Create activity_logs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS activity_logs (
        id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        user_id INT UNSIGNED,
        action VARCHAR(255) NOT NULL,
        details TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    )
    """)
    print("Table 'activity_logs' ensured.")

    # Seed default users if users table is empty
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    if count == 0:
        print("Seeding default users...")
        default_users = [
            ("admin", "admin123", "System Admin", "Admin"),
            ("doctor", "doctor123", "Dr. Ahmed", "Doctor"),
            ("nurse", "nurse123", "Nurse Sara", "Nurse"),
            ("reception", "reception123", "Ali Reception", "Receptionist")
        ]
        for username, password, fullname, role in default_users:
            hashed = hash_password(password)
            cursor.execute("""
                INSERT INTO users (username, password_hash, full_name, role)
                VALUES (%s, %s, %s, %s)
            """, (username, hashed, fullname, role))
        conn.commit()
        print("Default users seeded successfully.")
    else:
        print(f"Users table already has {count} records. Skipping seeding.")

    cursor.close()
    conn.close()
    print("Database setup complete!")

if __name__ == "__main__":
    setup_database()
