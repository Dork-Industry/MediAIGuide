from app import db, login_manager
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import json
import sqlalchemy.sql.functions as db_func


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # User profile fields
    full_name = db.Column(db.String(100), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    gender = db.Column(db.String(10), nullable=True)
    phone_number = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)
    profile_image = db.Column(db.String(255), nullable=True)
    
    # User type
    is_doctor = db.Column(db.Boolean, default=False)
    
    # Relationships
    subscription = db.relationship('Subscription', backref='user', uselist=False)
    search_history = db.relationship('SearchHistory', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_subscribed(self):
        return self.subscription and self.subscription.is_active()
    
    def get_search_limit(self):
        if not self.subscription:
            return 5  # Free tier limit
        return self.subscription.plan_search_limit
    
    def get_remaining_searches(self):
        if not self.subscription:
            # For free tier, calculate remaining daily searches
            today = datetime.utcnow().date()
            searches_today = db.session.query(SearchHistory).filter(
                SearchHistory.user_id == self.id,
                db.func.date(SearchHistory.timestamp) == today
            ).count()
            return max(0, self.get_search_limit() - searches_today)
        
        # For paid subscriptions, calculate remaining monthly searches
        this_month = datetime.utcnow().replace(day=1)
        searches_this_month = db.session.query(SearchHistory).filter(
            SearchHistory.user_id == self.id,
            SearchHistory.timestamp >= this_month
        ).count()
        return max(0, self.get_search_limit() - searches_this_month)
        
    def get_display_name(self):
        """Get user's display name, preferring full name if available"""
        return self.full_name if self.full_name else self.username


class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    plan_type = db.Column(db.String(50), nullable=False, default='free')  # free, basic, premium
    plan_search_limit = db.Column(db.Integer, default=5)
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=True)
    is_active_flag = db.Column(db.Boolean, default=True)
    
    def is_active(self):
        if not self.is_active_flag:
            return False
        if self.end_date is None:
            return True
        return datetime.utcnow() <= self.end_date


class SearchHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    query = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class MedicineCache(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    medicine_name = db.Column(db.String(200), unique=True, nullable=False, index=True)
    data = db.Column(db.Text, nullable=False)  # JSON data containing medicine information
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    @staticmethod
    def get_cached_data(medicine_name):
        cache_entry = db.session.query(MedicineCache).filter_by(medicine_name=medicine_name).first()
        if cache_entry:
            # Check if cache is older than a week
            cache_age = datetime.utcnow() - cache_entry.last_updated
            if cache_age.days < 7:  # Cache valid for a week
                return cache_entry.data
        return None
    
    @staticmethod
    def update_cache(medicine_name, data):
        cache_entry = db.session.query(MedicineCache).filter_by(medicine_name=medicine_name).first()
        if cache_entry:
            cache_entry.data = data
            cache_entry.last_updated = datetime.utcnow()
        else:
            cache_entry = MedicineCache(medicine_name=medicine_name, data=data)
            db.session.add(cache_entry)
        db.session.commit()

class HealthScan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    scan_date = db.Column(db.DateTime, default=datetime.utcnow)
    scan_type = db.Column(db.String(20), default='face')  # face, tongue, eye, skin
    
    # Face scan metrics
    heart_rate = db.Column(db.Float, nullable=True)
    blood_pressure_systolic = db.Column(db.Float, nullable=True)
    blood_pressure_diastolic = db.Column(db.Float, nullable=True)
    breathing_rate = db.Column(db.Float, nullable=True)
    oxygen_saturation = db.Column(db.Float, nullable=True)
    sympathetic_stress = db.Column(db.Float, nullable=True)
    parasympathetic_activity = db.Column(db.Float, nullable=True)
    prq = db.Column(db.Float, nullable=True)  # Parasympathetic Recovery Quotient
    hemoglobin = db.Column(db.Float, nullable=True)
    hemoglobin_a1c = db.Column(db.Float, nullable=True)
    
    # Tongue analysis metrics
    tongue_color = db.Column(db.String(50), nullable=True)  # e.g., pale, red, purple, etc.
    tongue_coating = db.Column(db.String(50), nullable=True)  # e.g., thin-white, thick-yellow, etc.
    tongue_shape = db.Column(db.String(50), nullable=True)  # e.g., swollen, thin, cracked, etc.
    tcm_diagnosis = db.Column(db.String(100), nullable=True)  # Traditional Chinese Medicine diagnosis
    vitamin_deficiency = db.Column(db.String(100), nullable=True)  # e.g., B12, iron, etc.
    infection_indicator = db.Column(db.String(100), nullable=True)  # e.g., thrush, COVID-19 signs
    
    # Eye analysis metrics
    sclera_color = db.Column(db.String(50), nullable=True)  # normal, yellow (jaundice), etc.
    conjunctiva_color = db.Column(db.String(50), nullable=True)  # normal, pale (anemia), etc.
    eye_redness = db.Column(db.Float, nullable=True)  # 0-100% scale
    pupil_reactivity = db.Column(db.String(50), nullable=True)  # normal, sluggish, etc.
    eye_condition = db.Column(db.String(100), nullable=True)  # detected condition
    
    # Skin analysis metrics
    skin_condition = db.Column(db.String(100), nullable=True)  # detected condition
    skin_color = db.Column(db.String(50), nullable=True)
    skin_texture = db.Column(db.String(50), nullable=True)
    rash_detection = db.Column(db.Boolean, default=False)
    rash_pattern = db.Column(db.String(100), nullable=True)  # e.g., bullseye (Lyme), etc.
    
    # Risk assessments
    wellness_score = db.Column(db.Float, nullable=True)  # 0-100 overall wellness score
    ascvd_risk = db.Column(db.Float, nullable=True)  # Atherosclerotic Cardiovascular Disease risk
    hypertension_risk = db.Column(db.Float, nullable=True)  # high blood pressure risk
    glucose_risk = db.Column(db.Float, nullable=True)  # high fasting glucose risk
    cholesterol_risk = db.Column(db.Float, nullable=True)  # high total cholesterol risk
    tuberculosis_risk = db.Column(db.Float, nullable=True)  # TB risk
    heart_age = db.Column(db.Float, nullable=True)  # estimated heart age
    
    scan_image_path = db.Column(db.String(255), nullable=True)  # Path to saved image for analysis
    notes = db.Column(db.Text, nullable=True)  # Additional notes or detection details
    
    # Relationships
    user = db.relationship('User', backref=db.backref('health_scans', lazy='dynamic'))


class FoodScan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    scan_date = db.Column(db.DateTime, default=datetime.utcnow)
    food_name = db.Column(db.String(200), nullable=False)
    calories = db.Column(db.Float, nullable=True)
    protein = db.Column(db.Float, nullable=True)
    carbs = db.Column(db.Float, nullable=True)
    fat = db.Column(db.Float, nullable=True)
    fiber = db.Column(db.Float, nullable=True)
    sugar = db.Column(db.Float, nullable=True)
    sodium = db.Column(db.Float, nullable=True)
    cholesterol = db.Column(db.Float, nullable=True)
    food_image_url = db.Column(db.String(500), nullable=True)
    data = db.Column(db.Text, nullable=True)  # JSON data with additional nutrition info
    
    # Relationships
    user = db.relationship('User', backref=db.backref('food_scans', lazy='dynamic'))


class BMIRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    record_date = db.Column(db.DateTime, default=datetime.utcnow)
    height = db.Column(db.Float, nullable=False)  # in centimeters
    weight = db.Column(db.Float, nullable=False)  # in kilograms
    bmi_value = db.Column(db.Float, nullable=False)
    bmi_category = db.Column(db.String(50), nullable=False)  # Underweight, Normal, Overweight, Obese
    diet_plan = db.Column(db.Text, nullable=True)  # JSON data containing personalized diet plan
    
    # Relationships
    user = db.relationship('User', backref=db.backref('bmi_records', lazy='dynamic'))

class Reminder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    reminder_type = db.Column(db.String(50), nullable=False, default='medicine')  # medicine, water, custom
    schedule_time = db.Column(db.Time, nullable=False)
    repeat_type = db.Column(db.String(50), nullable=False, default='daily')  # daily, weekly, custom
    repeat_days = db.Column(db.String(50), nullable=True)  # comma-separated days for weekly (1-7)
    active = db.Column(db.Boolean, default=True)
    audio_path = db.Column(db.String(255), nullable=True)  # path to voice recording
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_triggered = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('reminders', lazy='dynamic'))


class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    full_name = db.Column(db.String(100), nullable=False)
    specialty = db.Column(db.String(100), nullable=False)
    qualification = db.Column(db.String(200), nullable=False)
    experience_years = db.Column(db.Integer, nullable=False)
    license_number = db.Column(db.String(50), nullable=False, unique=True)
    bio = db.Column(db.Text, nullable=True)
    address = db.Column(db.Text, nullable=True)
    city = db.Column(db.String(50), nullable=True)
    state = db.Column(db.String(50), nullable=True)
    country = db.Column(db.String(50), nullable=True)
    postal_code = db.Column(db.String(20), nullable=True)
    consultation_fee = db.Column(db.Float, nullable=True)
    available_days = db.Column(db.String(100), nullable=True)  # Comma-separated weekdays (Mon,Tue,etc.)
    available_hours = db.Column(db.String(100), nullable=True)  # JSON string of time slots
    profile_image = db.Column(db.String(255), nullable=True)
    is_verified = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    average_rating = db.Column(db.Float, default=0.0)
    total_ratings = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('doctor_profile', uselist=False))


class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    appointment_date = db.Column(db.Date, nullable=False)
    appointment_time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, confirmed, cancelled, completed
    type = db.Column(db.String(20), default='online')  # online, in-person
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    # Relationships
    patient = db.relationship('User', backref=db.backref('appointments', lazy='dynamic'))
    doctor = db.relationship('Doctor', backref=db.backref('appointments', lazy='dynamic'))


class DoctorReview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    review = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    doctor = db.relationship('Doctor', backref=db.backref('reviews', lazy='dynamic'))
    user = db.relationship('User', backref=db.backref('doctor_reviews', lazy='dynamic'))
    
    # Ensure one review per user per doctor
    __table_args__ = (db.UniqueConstraint('doctor_id', 'user_id', name='unique_doctor_review'),)


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    sender = db.relationship('User', foreign_keys=[sender_id], backref=db.backref('sent_messages', lazy='dynamic'))
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref=db.backref('received_messages', lazy='dynamic'))
