import os
import psycopg2
from werkzeug.security import generate_password_hash

# Get database URL from environment
database_url = os.environ.get("DATABASE_URL")

try:
    # Connect to the database
    print("Connecting to the database...")
    conn = psycopg2.connect(database_url)
    conn.autocommit = True
    
    # Create a cursor
    cursor = conn.cursor()
    
    # Drop and create schema
    print("Dropping all tables with CASCADE...")
    cursor.execute("DROP SCHEMA public CASCADE;")
    cursor.execute("CREATE SCHEMA public;")
    
    # Create the main tables
    print("Creating User table...")
    cursor.execute("""
    CREATE TABLE "user" (
        id SERIAL PRIMARY KEY,
        username VARCHAR(64) UNIQUE NOT NULL,
        email VARCHAR(120) UNIQUE NOT NULL,
        password_hash VARCHAR(256) NOT NULL,
        is_admin BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        full_name VARCHAR(100),
        date_of_birth DATE,
        gender VARCHAR(10),
        phone_number VARCHAR(20),
        address TEXT,
        profile_image VARCHAR(255),
        is_doctor BOOLEAN DEFAULT FALSE
    )
    """)
    
    # Create subscription table
    cursor.execute("""
    CREATE TABLE subscription (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES "user"(id) NOT NULL,
        plan_type VARCHAR(50) NOT NULL DEFAULT 'free',
        plan_search_limit INTEGER DEFAULT 5,
        start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        end_date TIMESTAMP,
        is_active_flag BOOLEAN DEFAULT TRUE
    )
    """)
    
    # Create search history table
    cursor.execute("""
    CREATE TABLE search_history (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES "user"(id) NOT NULL,
        query VARCHAR(200) NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Create medicine cache table
    cursor.execute("""
    CREATE TABLE medicine_cache (
        id SERIAL PRIMARY KEY,
        medicine_name VARCHAR(200) UNIQUE NOT NULL,
        data TEXT NOT NULL,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Create health scan table
    cursor.execute("""
    CREATE TABLE health_scan (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES "user"(id) NOT NULL,
        scan_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        heart_rate FLOAT,
        blood_pressure_systolic FLOAT,
        blood_pressure_diastolic FLOAT,
        breathing_rate FLOAT,
        oxygen_saturation FLOAT,
        sympathetic_stress FLOAT,
        parasympathetic_activity FLOAT,
        prq FLOAT,
        hemoglobin FLOAT,
        hemoglobin_a1c FLOAT,
        wellness_score FLOAT,
        ascvd_risk FLOAT,
        hypertension_risk FLOAT,
        glucose_risk FLOAT,
        cholesterol_risk FLOAT,
        tuberculosis_risk FLOAT,
        heart_age FLOAT,
        notes TEXT
    )
    """)
    
    # Create food scan table
    cursor.execute("""
    CREATE TABLE food_scan (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES "user"(id) NOT NULL,
        scan_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        food_name VARCHAR(200) NOT NULL,
        calories FLOAT,
        protein FLOAT,
        carbs FLOAT,
        fat FLOAT,
        fiber FLOAT,
        sugar FLOAT,
        sodium FLOAT,
        cholesterol FLOAT,
        food_image_url VARCHAR(500),
        data TEXT
    )
    """)
    
    # Create BMI record table
    cursor.execute("""
    CREATE TABLE bmi_record (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES "user"(id) NOT NULL,
        record_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        height FLOAT NOT NULL,
        weight FLOAT NOT NULL,
        bmi_value FLOAT NOT NULL,
        bmi_category VARCHAR(50) NOT NULL,
        diet_plan TEXT
    )
    """)
    
    # Create reminder table
    cursor.execute("""
    CREATE TABLE reminder (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES "user"(id) NOT NULL,
        title VARCHAR(100) NOT NULL,
        description TEXT,
        reminder_type VARCHAR(50) NOT NULL DEFAULT 'medicine',
        schedule_time TIME NOT NULL,
        repeat_type VARCHAR(50) NOT NULL DEFAULT 'daily',
        repeat_days VARCHAR(50),
        active BOOLEAN DEFAULT TRUE,
        audio_path VARCHAR(255),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_triggered TIMESTAMP
    )
    """)
    
    # Create doctor table
    cursor.execute("""
    CREATE TABLE doctor (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES "user"(id) NOT NULL UNIQUE,
        full_name VARCHAR(100) NOT NULL,
        specialty VARCHAR(100) NOT NULL,
        qualification VARCHAR(200) NOT NULL,
        experience_years INTEGER NOT NULL,
        license_number VARCHAR(50) NOT NULL UNIQUE,
        bio TEXT,
        address TEXT,
        city VARCHAR(50),
        state VARCHAR(50),
        country VARCHAR(50),
        postal_code VARCHAR(20),
        consultation_fee FLOAT,
        available_days VARCHAR(100),
        available_hours VARCHAR(100),
        profile_image VARCHAR(255),
        is_verified BOOLEAN DEFAULT FALSE,
        is_active BOOLEAN DEFAULT TRUE,
        average_rating FLOAT DEFAULT 0.0,
        total_ratings INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Create appointment table
    cursor.execute("""
    CREATE TABLE appointment (
        id SERIAL PRIMARY KEY,
        patient_id INTEGER REFERENCES "user"(id) NOT NULL,
        doctor_id INTEGER REFERENCES doctor(id) NOT NULL,
        appointment_date DATE NOT NULL,
        appointment_time TIME NOT NULL,
        status VARCHAR(20) DEFAULT 'pending',
        type VARCHAR(20) DEFAULT 'online',
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP
    )
    """)
    
    # Create doctor review table
    cursor.execute("""
    CREATE TABLE doctor_review (
        id SERIAL PRIMARY KEY,
        doctor_id INTEGER REFERENCES doctor(id) NOT NULL,
        user_id INTEGER REFERENCES "user"(id) NOT NULL,
        rating INTEGER NOT NULL,
        review TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(doctor_id, user_id)
    )
    """)
    
    # Create message table
    cursor.execute("""
    CREATE TABLE message (
        id SERIAL PRIMARY KEY,
        sender_id INTEGER REFERENCES "user"(id) NOT NULL,
        recipient_id INTEGER REFERENCES "user"(id) NOT NULL,
        message TEXT NOT NULL,
        is_read BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Create admin account
    print("Creating admin account...")
    password_hash = generate_password_hash("admin123")
    cursor.execute(
        """INSERT INTO "user" (username, email, password_hash, is_admin) 
           VALUES (%s, %s, %s, %s)""",
        ("admin", "admin@example.com", password_hash, True)
    )
    
    print("Database has been reset and admin account created")
    
    # Close the connection
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")