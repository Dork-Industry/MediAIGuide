"""
Direct database migration script to add new drug interaction tables
"""

import os
from datetime import datetime
import json
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.sql import text

from app import app, db


def migrate_database():
    """Add drug interaction tables to the database"""
    # Connect directly to the database
    conn = db.engine.connect()
    
    # Check if tables exist
    inspector = sa.inspect(db.engine)
    existing_tables = inspector.get_table_names()
    
    # Create user_medication table if it doesn't exist
    if 'user_medication' not in existing_tables:
        print("Creating user_medication table...")
        conn.execute(text("""
        CREATE TABLE user_medication (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES "user"(id),
            medication_name VARCHAR(200) NOT NULL,
            dosage VARCHAR(100),
            frequency VARCHAR(100),
            start_date DATE,
            end_date DATE,
            reason VARCHAR(255),
            is_active BOOLEAN DEFAULT TRUE,
            notes TEXT,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX idx_user_medication_user_id ON user_medication(user_id);
        CREATE INDEX idx_user_medication_medication_name ON user_medication(medication_name);
        """))
        print("user_medication table created successfully.")
    else:
        print("user_medication table already exists.")
    
    # Create drug_interaction_cache table if it doesn't exist
    if 'drug_interaction_cache' not in existing_tables:
        print("Creating drug_interaction_cache table...")
        conn.execute(text("""
        CREATE TABLE drug_interaction_cache (
            id SERIAL PRIMARY KEY,
            drug_pair VARCHAR(400) NOT NULL UNIQUE,
            interaction_data TEXT NOT NULL,
            severity VARCHAR(20),
            description TEXT,
            last_updated TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX idx_drug_interaction_cache_drug_pair ON drug_interaction_cache(drug_pair);
        """))
        print("drug_interaction_cache table created successfully.")
    else:
        print("drug_interaction_cache table already exists.")
    
    # Create drug_interaction_check table if it doesn't exist
    if 'drug_interaction_check' not in existing_tables:
        print("Creating drug_interaction_check table...")
        conn.execute(text("""
        CREATE TABLE drug_interaction_check (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES "user"(id),
            medications TEXT NOT NULL,
            has_interactions BOOLEAN DEFAULT FALSE,
            highest_severity VARCHAR(20),
            check_date TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX idx_drug_interaction_check_user_id ON drug_interaction_check(user_id);
        """))
        print("drug_interaction_check table created successfully.")
    else:
        print("drug_interaction_check table already exists.")
    
    # Close connection
    conn.close()
    print("Migration completed successfully.")


if __name__ == "__main__":
    with app.app_context():
        migrate_database()