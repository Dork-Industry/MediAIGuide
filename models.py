from app import db, login_manager
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash


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
