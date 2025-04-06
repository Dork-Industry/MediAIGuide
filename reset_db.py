import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.security import generate_password_hash

# Database setup
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create temporary Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "temp_secret_key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
db.init_app(app)

# Define the User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    
    # User profile fields
    full_name = db.Column(db.String(100), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    gender = db.Column(db.String(10), nullable=True)
    phone_number = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)
    profile_image = db.Column(db.String(255), nullable=True)
    
    # User type
    is_doctor = db.Column(db.Boolean, default=False)

# Drop all tables and recreate them
with app.app_context():
    print("Dropping all tables with CASCADE...")
    # Use raw SQL to drop all tables with CASCADE
    db.session.execute(db.text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
    print("Creating User table...")
    db.create_all()
    
    # Create admin account
    print("Creating admin account...")
    admin = User(
        username="admin",
        email="admin@example.com",
        password_hash=generate_password_hash("admin123"),
        is_admin=True
    )
    db.session.add(admin)
    db.session.commit()
    
    print("Database has been reset and admin account created")
    print("You can now run the application")