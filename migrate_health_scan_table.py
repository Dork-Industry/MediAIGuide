"""
Direct database migration script to add missing fields to the health_scan table
"""
import os
import sys
from sqlalchemy import create_engine, MetaData, Table, Column, String, Boolean, Text, Float
from sqlalchemy.dialects.postgresql import ARRAY

# Database connection
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("Error: DATABASE_URL environment variable not set.")
    sys.exit(1)

def migrate_database():
    """Add missing fields to health_scan table"""
    
    print("Starting migration...")
    
    # Create engine and connect to database
    engine = create_engine(DATABASE_URL)
    conn = engine.connect()
    
    # Load existing metadata
    metadata = MetaData()
    metadata.reflect(bind=engine)
    
    # Add new columns to health_scan table if it exists
    if 'health_scan' in metadata.tables:
        health_scan = metadata.tables['health_scan']
        
        # List of column definitions
        columns_to_add = [
            Column('scan_type', String(20), default='face'),
            Column('tongue_color', String(50), nullable=True),
            Column('tongue_coating', String(50), nullable=True),
            Column('tongue_shape', String(50), nullable=True),
            Column('tcm_diagnosis', String(100), nullable=True),
            Column('vitamin_deficiency', String(100), nullable=True),
            Column('infection_indicator', String(100), nullable=True),
            Column('sclera_color', String(50), nullable=True),
            Column('conjunctiva_color', String(50), nullable=True),
            Column('eye_redness', Float, nullable=True),
            Column('pupil_reactivity', String(50), nullable=True),
            Column('eye_condition', String(100), nullable=True),
            Column('skin_condition', String(100), nullable=True),
            Column('skin_color', String(50), nullable=True),
            Column('skin_texture', String(50), nullable=True),
            Column('rash_detection', Boolean, default=False),
            Column('rash_pattern', String(100), nullable=True),
            Column('scan_image_path', String(255), nullable=True)
        ]
        
        # Add each column if it doesn't exist
        with conn.begin() as transaction:
            for column in columns_to_add:
                column_name = column.name
                if column_name not in health_scan.columns:
                    print(f"Adding column: {column_name}")
                    conn.execute(f'ALTER TABLE health_scan ADD COLUMN IF NOT EXISTS {column_name} {column.type}')
                    if column.default is not None:
                        if isinstance(column.type, Boolean):
                            default_value = 'true' if column.default.arg else 'false'
                            conn.execute(f"ALTER TABLE health_scan ALTER COLUMN {column_name} SET DEFAULT {default_value}")
                        else:
                            if isinstance(column.default.arg, str):
                                default_value = f"'{column.default.arg}'"
                            else:
                                default_value = column.default.arg
                            conn.execute(f"ALTER TABLE health_scan ALTER COLUMN {column_name} SET DEFAULT {default_value}")
        
        print("Migration completed successfully!")
    else:
        print("Error: health_scan table does not exist!")
    
    # Close connection
    conn.close()

if __name__ == "__main__":
    migrate_database()