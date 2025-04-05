import json
from flask import render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import app, db
from models import User, Subscription, SearchHistory, MedicineCache
from utils import get_medicine_info, init_admin_account
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Make sure admin account exists
# Using with_app_context instead of before_first_request (which is deprecated)
def setup_app():
    init_admin_account()

# Run setup when routes module is imported
with app.app_context():
    setup_app()

# Auth routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = 'remember' in request.form
        
        user = User.query.filter_by(username=username).first()
        
        if not user or not user.check_password(password):
            flash('Invalid username or password', 'danger')
            return redirect(url_for('login'))
            
        login_user(user, remember=remember)
        
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        return redirect(url_for('home'))
        
    return render_template('login.html', title='Login')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Username already taken.', 'danger')
            return redirect(url_for('register'))
            
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return redirect(url_for('register'))
            
        user = User(username=username, email=email)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        # Create a free subscription for the new user
        subscription = Subscription(
            user_id=user.id,
            plan_type='free',
            plan_search_limit=5,
            start_date=datetime.utcnow(),
            end_date=None  # Free plan doesn't expire
        )
        db.session.add(subscription)
        db.session.commit()
        
        flash('Account created! You can now log in.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html', title='Register')

# Main routes
@app.route('/')
def home():
    return render_template('home.html', title='Medicine AI')

@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        query = request.form.get('medicine_name', '').strip()
        
        if not query:
            flash('Please enter a medicine name', 'warning')
            return redirect(url_for('home'))
            
        # Check if user is logged in
        if current_user.is_authenticated:
            # Check if user has remaining searches
            remaining_searches = current_user.get_remaining_searches()
            if remaining_searches <= 0:
                flash('You have reached your search limit. Please upgrade your subscription.', 'warning')
                return redirect(url_for('subscription'))
                
            medicine_info = get_medicine_info(query, current_user)
        else:
            # Anonymous users get a limited experience
            medicine_info = get_medicine_info(query)
            flash('Create an account to save your search history and get more searches!', 'info')
            
        return render_template('search_results.html', 
                              medicine=medicine_info, 
                              title=f'Results for {query}')
                              
    # GET request or no query, redirect to home
    return redirect(url_for('home'))

@app.route('/api/search', methods=['POST'])
@login_required
def api_search():
    data = request.get_json()
    if not data or 'medicine_name' not in data:
        return jsonify({'error': 'Medicine name is required'}), 400
        
    query = data['medicine_name'].strip()
    
    # Check if user has remaining searches
    remaining_searches = current_user.get_remaining_searches()
    if remaining_searches <= 0:
        return jsonify({
            'error': 'Search limit reached',
            'message': 'You have reached your search limit. Please upgrade your subscription.'
        }), 403
        
    medicine_info = get_medicine_info(query, current_user)
    return jsonify(medicine_info)

@app.route('/user/dashboard')
@login_required
def user_dashboard():
    # Get user's search history
    search_history = SearchHistory.query.filter_by(user_id=current_user.id)\
                                 .order_by(SearchHistory.timestamp.desc())\
                                 .limit(20).all()
                                 
    # Get subscription info
    subscription = current_user.subscription
    remaining_searches = current_user.get_remaining_searches()
    
    return render_template('user_dashboard.html',
                          title='Your Dashboard',
                          search_history=search_history,
                          subscription=subscription,
                          remaining_searches=remaining_searches)

@app.route('/subscription')
@login_required
def subscription():
    return render_template('subscription.html', 
                          title='Subscription Plans',
                          current_plan=current_user.subscription.plan_type if current_user.subscription else 'none')

@app.route('/subscription/upgrade', methods=['POST'])
@login_required
def upgrade_subscription():
    plan_type = request.form.get('plan_type')
    
    if plan_type not in ['free', 'basic', 'premium']:
        flash('Invalid subscription plan', 'danger')
        return redirect(url_for('subscription'))
        
    # Set plan limits based on type
    if plan_type == 'free':
        search_limit = 5
        duration_days = None  # No expiration
    elif plan_type == 'basic':
        search_limit = 50
        duration_days = 30
    elif plan_type == 'premium':
        search_limit = 500
        duration_days = 30
    
    # Update or create subscription
    subscription = current_user.subscription
    if subscription:
        subscription.plan_type = plan_type
        subscription.plan_search_limit = search_limit
        subscription.start_date = datetime.utcnow()
        subscription.end_date = datetime.utcnow() + timedelta(days=duration_days) if duration_days else None
        subscription.is_active_flag = True
    else:
        subscription = Subscription(
            user_id=current_user.id,
            plan_type=plan_type,
            plan_search_limit=search_limit,
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=duration_days) if duration_days else None
        )
        db.session.add(subscription)
        
    db.session.commit()
    
    flash(f'Successfully upgraded to {plan_type.title()} plan!', 'success')
    return redirect(url_for('user_dashboard'))

# Admin routes
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        abort(403)
        
    # Get user and subscription stats
    users = User.query.filter(User.is_admin == False).all()
    total_users = len(users)
    
    free_users = sum(1 for u in users if u.subscription and u.subscription.plan_type == 'free')
    basic_users = sum(1 for u in users if u.subscription and u.subscription.plan_type == 'basic')
    premium_users = sum(1 for u in users if u.subscription and u.subscription.plan_type == 'premium')
    
    # Get search stats
    today = datetime.utcnow().date()
    searches_today = SearchHistory.query.filter(db.func.date(SearchHistory.timestamp) == today).count()
    
    this_month = datetime.utcnow().replace(day=1)
    searches_this_month = SearchHistory.query.filter(SearchHistory.timestamp >= this_month).count()
    
    return render_template('admin_dashboard.html',
                          title='Admin Dashboard',
                          total_users=total_users,
                          free_users=free_users,
                          basic_users=basic_users,
                          premium_users=premium_users,
                          searches_today=searches_today,
                          searches_this_month=searches_this_month,
                          users=users)

@app.route('/admin/user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def admin_user_detail(user_id):
    if not current_user.is_admin:
        abort(403)
        
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'update_subscription':
            plan_type = request.form.get('plan_type')
            search_limit = int(request.form.get('search_limit', 5))
            duration_days = int(request.form.get('duration_days', 30))
            is_active = 'is_active' in request.form
            
            subscription = user.subscription
            if subscription:
                subscription.plan_type = plan_type
                subscription.plan_search_limit = search_limit
                subscription.end_date = datetime.utcnow() + timedelta(days=duration_days) if duration_days > 0 else None
                subscription.is_active_flag = is_active
            else:
                subscription = Subscription(
                    user_id=user.id,
                    plan_type=plan_type,
                    plan_search_limit=search_limit,
                    start_date=datetime.utcnow(),
                    end_date=datetime.utcnow() + timedelta(days=duration_days) if duration_days > 0 else None,
                    is_active_flag=is_active
                )
                db.session.add(subscription)
                
            db.session.commit()
            flash(f'Subscription updated for {user.username}', 'success')
            
        elif action == 'reset_password':
            new_password = request.form.get('new_password')
            if new_password:
                user.set_password(new_password)
                db.session.commit()
                flash(f'Password reset for {user.username}', 'success')
                
        return redirect(url_for('admin_user_detail', user_id=user.id))
    
    # Get user's search history
    search_history = SearchHistory.query.filter_by(user_id=user.id)\
                                 .order_by(SearchHistory.timestamp.desc())\
                                 .limit(10).all()
                                 
    return render_template('admin_user_detail.html',
                          title=f'User: {user.username}',
                          user=user,
                          search_history=search_history)

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500
