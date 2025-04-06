"""
Database migration script to add new fields to User and Doctor models
"""
import os
import sys
from app import app, db
from models import User, Doctor

def migrate_database():
    """Add new fields to User and Doctor models"""
    with app.app_context():
        # Check if the new columns exist
        connection = db.engine.connect()
        inspector = db.inspect(db.engine)
        
        # For User model
        print("Checking User table...")
        user_columns = [col['name'] for col in inspector.get_columns('user')]
        
        user_cols_to_add = []
        if 'share_health_data' not in user_columns:
            user_cols_to_add.append("ALTER TABLE \"user\" ADD COLUMN share_health_data BOOLEAN DEFAULT TRUE")
        if 'receive_notifications' not in user_columns:
            user_cols_to_add.append("ALTER TABLE \"user\" ADD COLUMN receive_notifications BOOLEAN DEFAULT TRUE")
        
        if user_cols_to_add:
            print(f"Adding {len(user_cols_to_add)} columns to User table")
            for statement in user_cols_to_add:
                connection.execute(db.text(statement))
            connection.commit()
        else:
            print("No new columns needed for User table")
        
        # For Doctor model
        print("Checking Doctor table...")
        doctor_columns = [col['name'] for col in inspector.get_columns('doctor')]
        
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
                connection.execute(db.text(statement))
            connection.commit()
        else:
            print("No new columns needed for Doctor table")
        
        connection.close()
        print("Migration completed successfully!")

if __name__ == "__main__":
    migrate_database()