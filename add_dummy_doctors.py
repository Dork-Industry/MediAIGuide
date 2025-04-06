"""
Script to add dummy doctor profiles to the database
"""
import os
from datetime import datetime
from app import app, db
from models import User, Doctor
from werkzeug.security import generate_password_hash

def create_dummy_doctors():
    """Create dummy doctor profiles for testing"""
    with app.app_context():
        # Create doctor users and profiles if they don't exist
        doctors_data = [
            {
                "username": "dr_sharma",
                "email": "dr.sharma@example.com",
                "password": "doctor123",
                "full_name": "Dr. Amit Sharma",
                "specialty": "Cardiology",
                "qualification": "MBBS, MD (Cardiology)",
                "experience_years": 15,
                "license_number": "MCI-12345678",
                "bio": "Dr. Amit Sharma is a highly skilled cardiologist with expertise in diagnosing and treating heart conditions including coronary artery disease, heart failure, and cardiac arrhythmias. He specializes in non-invasive cardiology and has helped thousands of patients with heart health management.",
                "city": "Mumbai",
                "state": "Maharashtra",
                "country": "India",
                "consultation_fee": 1200,
                "available_days": "Mon,Tue,Wed,Thu,Fri",
                "available_hours": "10:00 AM - 1:00 PM, 5:00 PM - 8:00 PM",
                "profile_image": "/static/images/doctors/dr_sharma.jpg",
                "is_verified": True
            },
            {
                "username": "dr_patel",
                "email": "dr.patel@example.com",
                "password": "doctor123",
                "full_name": "Dr. Priya Patel",
                "specialty": "Dermatology",
                "qualification": "MBBS, MD (Dermatology)",
                "experience_years": 10,
                "license_number": "MCI-23456789",
                "bio": "Dr. Priya Patel is a board-certified dermatologist specializing in medical and cosmetic dermatology. She treats various skin conditions including acne, eczema, psoriasis, and skin cancer. Dr. Patel is known for her patient-centered approach and expertise in the latest dermatological treatments.",
                "city": "Bangalore",
                "state": "Karnataka",
                "country": "India",
                "consultation_fee": 1500,
                "available_days": "Mon,Wed,Fri",
                "available_hours": "9:00 AM - 2:00 PM",
                "profile_image": "/static/images/doctors/dr_patel.jpg",
                "is_verified": True
            },
            {
                "username": "dr_singh",
                "email": "dr.singh@example.com",
                "password": "doctor123",
                "full_name": "Dr. Rajinder Singh",
                "specialty": "Orthopedics",
                "qualification": "MBBS, MS (Orthopedics), Fellowship in Joint Replacement",
                "experience_years": 18,
                "license_number": "MCI-34567890",
                "bio": "Dr. Rajinder Singh is an accomplished orthopedic surgeon with expertise in joint replacement surgery, sports medicine, and trauma care. He has performed over 5,000 successful joint replacement surgeries and is dedicated to helping patients recover from bone and joint injuries.",
                "city": "Delhi",
                "state": "Delhi",
                "country": "India",
                "consultation_fee": 1800,
                "available_days": "Tue,Thu,Sat",
                "available_hours": "11:00 AM - 4:00 PM",
                "profile_image": "/static/images/doctors/dr_singh.jpg",
                "is_verified": True
            },
            {
                "username": "dr_gupta",
                "email": "dr.gupta@example.com",
                "password": "doctor123",
                "full_name": "Dr. Sanjana Gupta",
                "specialty": "Pediatrics",
                "qualification": "MBBS, DCH, MD (Pediatrics)",
                "experience_years": 12,
                "license_number": "MCI-45678901",
                "bio": "Dr. Sanjana Gupta is a compassionate pediatrician who provides comprehensive healthcare for infants, children, and adolescents. She specializes in childhood development, preventive care, and managing chronic pediatric conditions. Dr. Gupta is beloved by her young patients for her gentle and friendly approach.",
                "city": "Chennai",
                "state": "Tamil Nadu",
                "country": "India",
                "consultation_fee": 1000,
                "available_days": "Mon,Tue,Wed,Thu,Fri",
                "available_hours": "9:00 AM - 1:00 PM, 4:00 PM - 6:00 PM",
                "profile_image": "/static/images/doctors/dr_gupta.jpg",
                "is_verified": True
            }
        ]

        # Create directory for doctor images if it doesn't exist
        os.makedirs('static/images/doctors', exist_ok=True)

        for doctor_data in doctors_data:
            # Check if user already exists
            existing_user = db.session.query(User).filter_by(username=doctor_data["username"]).first()
            
            if not existing_user:
                # Create user
                user = User(
                    username=doctor_data["username"],
                    email=doctor_data["email"],
                    is_admin=False,
                    is_doctor=True,
                    full_name=doctor_data["full_name"]
                )
                user.set_password(doctor_data["password"])
                db.session.add(user)
                db.session.commit()
                
                # Create doctor profile
                doctor = Doctor(
                    user_id=user.id,
                    full_name=doctor_data["full_name"],
                    specialty=doctor_data["specialty"],
                    qualification=doctor_data["qualification"],
                    experience_years=doctor_data["experience_years"],
                    license_number=doctor_data["license_number"],
                    bio=doctor_data["bio"],
                    city=doctor_data["city"],
                    state=doctor_data["state"],
                    country=doctor_data["country"],
                    consultation_fee=doctor_data["consultation_fee"],
                    available_days=doctor_data["available_days"],
                    available_hours=doctor_data["available_hours"],
                    profile_image=doctor_data["profile_image"],
                    is_verified=doctor_data["is_verified"],
                    is_active=True,
                    created_at=datetime.utcnow()
                )
                db.session.add(doctor)
                db.session.commit()
                print(f"Created doctor profile: {doctor_data['full_name']}")
            else:
                print(f"Doctor {doctor_data['username']} already exists")

if __name__ == "__main__":
    create_dummy_doctors()
    print("Dummy doctor profiles added successfully!")