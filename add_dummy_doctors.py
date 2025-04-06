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
                "is_verified": True,
                "average_rating": 4.8,
                "total_ratings": 245
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
                "is_verified": True,
                "average_rating": 4.7,
                "total_ratings": 189
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
                "is_verified": True,
                "average_rating": 4.9,
                "total_ratings": 320
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
                "is_verified": True,
                "average_rating": 4.6,
                "total_ratings": 178
            },
            {
                "username": "dr_khan",
                "email": "dr.khan@example.com",
                "password": "doctor123",
                "full_name": "Dr. Farah Khan",
                "specialty": "Gynecology",
                "qualification": "MBBS, MS (Obstetrics & Gynecology)",
                "experience_years": 14,
                "license_number": "MCI-56789012",
                "bio": "Dr. Farah Khan is a highly respected gynecologist specializing in women's reproductive health. She provides comprehensive care for women of all ages, from adolescence through menopause. Dr. Khan is known for her expertise in minimally invasive gynecological procedures and her compassionate approach to patient care.",
                "city": "Hyderabad",
                "state": "Telangana",
                "country": "India",
                "consultation_fee": 1600,
                "available_days": "Mon,Tue,Thu,Fri",
                "available_hours": "10:00 AM - 2:00 PM, 4:00 PM - 7:00 PM",
                "profile_image": "/static/images/doctors/dr_khan.jpg",
                "is_verified": True,
                "average_rating": 4.8,
                "total_ratings": 213
            },
            {
                "username": "dr_kumar",
                "email": "dr.kumar@example.com",
                "password": "doctor123",
                "full_name": "Dr. Vikram Kumar",
                "specialty": "Neurology",
                "qualification": "MBBS, DM (Neurology), Fellowship in Epilepsy",
                "experience_years": 16,
                "license_number": "MCI-67890123",
                "bio": "Dr. Vikram Kumar is a distinguished neurologist with expertise in treating various neurological disorders including epilepsy, Parkinson's disease, and multiple sclerosis. His research contributions to the field of epilepsy management have been recognized internationally. Dr. Kumar's patient-centered approach focuses on comprehensive care and quality of life improvement.",
                "city": "Pune",
                "state": "Maharashtra",
                "country": "India",
                "consultation_fee": 2000,
                "available_days": "Wed,Thu,Fri,Sat",
                "available_hours": "9:00 AM - 3:00 PM",
                "profile_image": "/static/images/doctors/dr_kumar.jpg",
                "is_verified": True,
                "average_rating": 4.9,
                "total_ratings": 276
            },
            {
                "username": "dr_verma",
                "email": "dr.verma@example.com",
                "password": "doctor123",
                "full_name": "Dr. Anil Verma",
                "specialty": "Psychiatry",
                "qualification": "MBBS, MD (Psychiatry)",
                "experience_years": 11,
                "license_number": "MCI-78901234",
                "bio": "Dr. Anil Verma is a dedicated psychiatrist specializing in mood disorders, anxiety, and addiction treatment. He offers a blend of medication management and psychotherapy, tailored to each patient's needs. Dr. Verma's holistic approach encompasses lifestyle changes, stress management techniques, and family support to promote mental well-being.",
                "city": "Kolkata",
                "state": "West Bengal",
                "country": "India",
                "consultation_fee": 1400,
                "available_days": "Mon,Wed,Fri,Sat",
                "available_hours": "11:00 AM - 7:00 PM",
                "profile_image": "/static/images/doctors/dr_verma.jpg",
                "is_verified": True,
                "average_rating": 4.7,
                "total_ratings": 152
            },
            {
                "username": "dr_reddy",
                "email": "dr.reddy@example.com",
                "password": "doctor123",
                "full_name": "Dr. Kiran Reddy",
                "specialty": "Endocrinology",
                "qualification": "MBBS, MD (Internal Medicine), DM (Endocrinology)",
                "experience_years": 13,
                "license_number": "MCI-89012345",
                "bio": "Dr. Kiran Reddy is an endocrinologist with expertise in diabetes management, thyroid disorders, and hormonal imbalances. His evidence-based approach to complex endocrine conditions has helped thousands of patients achieve better metabolic health. Dr. Reddy is known for his thorough explanations and ability to simplify complex medical concepts for his patients.",
                "city": "Bangalore",
                "state": "Karnataka",
                "country": "India",
                "consultation_fee": 1700,
                "available_days": "Tue,Wed,Thu,Sat",
                "available_hours": "9:00 AM - 1:00 PM, 5:00 PM - 8:00 PM",
                "profile_image": "/static/images/doctors/dr_reddy.jpg",
                "is_verified": True,
                "average_rating": 4.8,
                "total_ratings": 198
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
                    profile_image=doctor_data["username"] + ".jpg",
                    is_verified=doctor_data["is_verified"],
                    is_active=True,
                    average_rating=doctor_data.get("average_rating", 4.5),
                    total_ratings=doctor_data.get("total_ratings", 100),
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