"""
Direct database migration script to add new fields to User and Doctor models
"""
import os
import psycopg2
from psycopg2 import sql

def migrate_database():
    """Add new fields to User and Doctor models"""
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
        # Check if User table has the new columns
        print("Checking User table...")
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'user'")
        user_columns = [col[0] for col in cursor.fetchall()]
        
        user_cols_to_add = []
        if 'share_health_data' not in user_columns:
            user_cols_to_add.append("ALTER TABLE \"user\" ADD COLUMN share_health_data BOOLEAN DEFAULT TRUE")
        if 'receive_notifications' not in user_columns:
            user_cols_to_add.append("ALTER TABLE \"user\" ADD COLUMN receive_notifications BOOLEAN DEFAULT TRUE")
        
        if user_cols_to_add:
            print(f"Adding {len(user_cols_to_add)} columns to User table")
            for statement in user_cols_to_add:
                cursor.execute(statement)
            conn.commit()
        else:
            print("No new columns needed for User table")
        
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
                cursor.execute(statement)
            conn.commit()
        else:
            print("No new columns needed for Doctor table")
        
        print("Migration completed successfully!")
    
    except Exception as e:
        conn.rollback()
        print(f"Error during migration: {e}")
    
    finally:
        cursor.close()
        conn.close()
        print("Database connection closed.")

if __name__ == "__main__":
    migrate_database()