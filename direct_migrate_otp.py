"""
Direct database migration script to add OTP fields to User model
"""
import os
import sys
import sqlalchemy
from sqlalchemy import create_engine, Column, DateTime, String, Boolean
from sqlalchemy.sql import text
from sqlalchemy.dialects.postgresql import VARCHAR, TIMESTAMP, BOOLEAN

def migrate_database():
    """Add OTP fields to User model"""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL environment variable not set")
        sys.exit(1)
    
    engine = create_engine(database_url)
    conn = engine.connect()
    
    # Begin transaction
    trans = conn.begin()
    try:
        # Check if columns already exist
        result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'user' AND column_name = 'otp'"))
        if result.rowcount == 0:
            print("Adding OTP fields to User model...")
            conn.execute(text("ALTER TABLE \"user\" ADD COLUMN otp VARCHAR(6)"))
            conn.execute(text("ALTER TABLE \"user\" ADD COLUMN otp_generated_at TIMESTAMP"))
            conn.execute(text("ALTER TABLE \"user\" ADD COLUMN otp_verified BOOLEAN DEFAULT FALSE"))
            print("OTP fields added successfully")
        else:
            print("OTP fields already exist")
            
        # Commit the transaction
        trans.commit()
        print("Migration completed successfully")
    except Exception as e:
        # Rollback in case of error
        trans.rollback()
        print(f"Migration failed: {str(e)}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()
