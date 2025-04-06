"""
Direct database migration script to add document fields to Doctor model
"""
import os
import psycopg2
from psycopg2 import sql

def migrate_database():
    """Add document fields to Doctor model"""
    # Get connection details from environment variables
    db_url = os.environ.get('DATABASE_URL')
    
    if not db_url:
        print("Error: DATABASE_URL environment variable not found.")
        return
    
    # Connect to database
    print("Connecting to database...")
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    
    try:
        # Get table names to verify if doctor table exists
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        tables = [table[0] for table in cursor.fetchall()]
        
        if 'doctor' not in tables:
            print("Doctor table doesn't exist in the database.")
            return
        
        # Check if Doctor table has the new columns
        print("Checking Doctor table...")
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'doctor'")
        doctor_columns = [col[0] for col in cursor.fetchall()]
        
        doctor_cols_to_add = []
        if 'degree_document' not in doctor_columns:
            doctor_cols_to_add.append("ALTER TABLE doctor ADD COLUMN degree_document VARCHAR(255)")
        if 'license_document' not in doctor_columns:
            doctor_cols_to_add.append("ALTER TABLE doctor ADD COLUMN license_document VARCHAR(255)")
        if 'id_proof' not in doctor_columns:
            doctor_cols_to_add.append("ALTER TABLE doctor ADD COLUMN id_proof VARCHAR(255)")
        if 'additional_document' not in doctor_columns:
            doctor_cols_to_add.append("ALTER TABLE doctor ADD COLUMN additional_document VARCHAR(255)")
        
        if doctor_cols_to_add:
            print(f"Adding {len(doctor_cols_to_add)} columns to Doctor table")
            for statement in doctor_cols_to_add:
                print(f"Executing: {statement}")
                cursor.execute(statement)
            conn.commit()
            print("Doctor table updated successfully!")
        else:
            print("No new columns needed for Doctor table")
        
    except Exception as e:
        conn.rollback()
        print(f"Error during migration: {e}")
    
    finally:
        cursor.close()
        conn.close()
        print("Database connection closed.")

if __name__ == "__main__":
    migrate_database()