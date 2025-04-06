import json
import os
import time
from flask import render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DateField, BooleanField, SelectField
from wtforms.validators import DataRequired, Length, Optional
from app import app, db
from models import User, Subscription, SearchHistory, MedicineCache, HealthScan, FoodScan, BMIRecord, Reminder, Doctor, Appointment, DoctorReview, Message, UserMedication, DrugInteractionCheck
from utils import get_medicine_info, init_admin_account, record_search, analyze_health_data, analyze_food_image, generate_diet_plan, check_drug_interaction, check_multiple_drug_interactions
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
        logger.debug(f"User already authenticated: {current_user.username}, id: {current_user.id}, is_admin: {current_user.is_admin}")
        return redirect(url_for('home'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = 'remember' in request.form
        
        logger.debug(f"Login attempt for username: {username}")
        
        user = db.session.query(User).filter_by(username=username).first()
        
        if not user:
            logger.warning(f"Login failed: username {username} not found")
            flash('Invalid username or password', 'danger')
            return redirect(url_for('login'))
            
        if not user.check_password(password):
            logger.warning(f"Login failed: incorrect password for username {username}")
            flash('Invalid username or password', 'danger')
            return redirect(url_for('login'))
            
        login_user(user, remember=remember)
        logger.info(f"User logged in successfully: {user.username}, id: {user.id}, is_admin: {user.is_admin}")
        
        next_page = request.args.get('next')
        if next_page:
            logger.debug(f"Redirecting to next page: {next_page}")
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
        
        if db.session.query(User).filter_by(username=username).first():
            flash('Username already taken.', 'danger')
            return redirect(url_for('register'))
            
        if db.session.query(User).filter_by(email=email).first():
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
    # Fetch featured doctors (verified and active) to display on home page
    doctors = db.session.query(Doctor).filter_by(is_verified=True, is_active=True).order_by(Doctor.average_rating.desc()).limit(8).all()
    return render_template('home.html', title='Medicine AI', doctors=doctors)

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
    search_history = db.session.query(SearchHistory).filter_by(user_id=current_user.id)\
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
    # Add debug logging to understand what's happening
    logger.debug(f"Admin dashboard accessed by user: {current_user.username}, id: {current_user.id}, is_admin: {current_user.is_admin}")
    
    if not current_user.is_admin:
        logger.warning(f"Non-admin user {current_user.username} attempted to access admin dashboard")
        flash("You don't have permission to access the admin dashboard.", "danger")
        abort(403)
        
    # Get user and subscription stats - Use SQL directly for better performance
    total_users = db.session.query(db.func.count(User.id)).filter(User.is_admin == False).scalar() or 0
    
    # Use a single query to get subscription counts
    subscription_counts = db.session.query(
        Subscription.plan_type, 
        db.func.count(Subscription.id)
    ).group_by(Subscription.plan_type).all()
    
    # Convert to dictionary for easy access
    subscription_dict = {plan: count for plan, count in subscription_counts}
    
    free_users = subscription_dict.get('free', 0)
    basic_users = subscription_dict.get('basic', 0) 
    premium_users = subscription_dict.get('premium', 0)
    
    # Get search stats - Use efficient SQL queries
    today = datetime.utcnow().date()
    searches_today = db.session.query(db.func.count(SearchHistory.id)).filter(
        db.func.date(SearchHistory.timestamp) == today
    ).scalar() or 0
    
    this_month = datetime.utcnow().replace(day=1)
    searches_this_month = db.session.query(db.func.count(SearchHistory.id)).filter(
        SearchHistory.timestamp >= this_month
    ).scalar() or 0
    
    # Get pending doctor verifications count
    pending_doctors = db.session.query(db.func.count(Doctor.id)).filter(
        Doctor.is_verified == False
    ).scalar() or 0
    
    # Get active appointments count
    active_appointments = db.session.query(db.func.count(Appointment.id)).filter(
        Appointment.status.in_(['pending', 'confirmed']),
        Appointment.appointment_date >= datetime.utcnow().date()
    ).scalar() or 0
    
    # Get recent users - limit to 10 for performance
    recent_users = db.session.query(User).filter(
        User.is_admin == False
    ).order_by(User.created_at.desc()).limit(10).all()
    
    logger.debug(f"Admin dashboard data loaded successfully for user: {current_user.username}")
    
    return render_template('admin_dashboard.html',
                          title='Admin Dashboard',
                          total_users=total_users,
                          free_users=free_users,
                          basic_users=basic_users,
                          premium_users=premium_users,
                          searches_today=searches_today,
                          searches_this_month=searches_this_month,
                          pending_doctors=pending_doctors,
                          active_appointments=active_appointments,
                          users=recent_users)

@app.route('/admin/user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def admin_user_detail(user_id):
    if not current_user.is_admin:
        abort(403)
        
    user = db.session.get(User, user_id) or abort(404)
    
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
    search_history = db.session.query(SearchHistory).filter_by(user_id=user.id)\
                                 .order_by(SearchHistory.timestamp.desc())\
                                 .limit(10).all()
                                 
    return render_template('admin_user_detail.html',
                          title=f'User: {user.username}',
                          user=user,
                          search_history=search_history)

# Admin Debug Page
@app.route('/admin/check')
@login_required
def admin_check():
    # Check if user is admin in the database directly
    user_id = current_user.id
    db_user = db.session.get(User, user_id)
    db_admin_status = db_user.is_admin if db_user else False
    
    # Option to fix admin privileges if there's a mismatch
    update_admin_privilege = db_admin_status != current_user.is_admin
    
    logger.debug(f"Admin check page: User {current_user.username}, session admin: {current_user.is_admin}, db admin: {db_admin_status}")
    
    return render_template('admin_check.html', 
                          title='Admin Check',
                          db_admin_status=db_admin_status,
                          update_admin_privilege=update_admin_privilege)

@app.route('/admin/fix-privilege')
@login_required
def fix_admin_privilege():
    user_id = current_user.id
    db_user = db.session.get(User, user_id)
    
    if db_user and db_user.is_admin:
        # Force refresh the session with correct admin status
        login_user(db_user)
        flash('Admin privileges have been refreshed.', 'success')
        logger.info(f"Fixed admin privileges for user: {current_user.username}")
    else:
        flash('You do not have admin privileges in the database.', 'danger')
        logger.warning(f"Attempted to fix admin privileges for non-admin user: {current_user.username}")
    
    return redirect(url_for('admin_check'))

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500


# Form classes for Drug Interaction Checker
class DrugInteractionForm(FlaskForm):
    medication1 = StringField('First Medication', validators=[DataRequired()])
    medication2 = StringField('Second Medication', validators=[DataRequired()])


class MedicationForm(FlaskForm):
    medication_name = StringField('Medication Name', validators=[DataRequired(), Length(max=200)])
    dosage = StringField('Dosage', validators=[Optional(), Length(max=100)])
    frequency = StringField('Frequency', validators=[Optional(), Length(max=100)])
    start_date = DateField('Start Date', validators=[Optional()])
    end_date = DateField('End Date', validators=[Optional()])
    reason = StringField('Reason', validators=[Optional(), Length(max=255)])
    is_active = BooleanField('Currently Taking', default=True)
    notes = TextAreaField('Notes', validators=[Optional()])


# Drug Interaction Routes
@app.route('/drug-interactions', methods=['GET', 'POST'])
@login_required
def drug_interactions():
    """Drug Interaction Checker Page"""
    form = DrugInteractionForm()
    medication_form = MedicationForm()
    results = None
    
    if request.method == 'POST':
        # Get all medication fields from the form
        medications = []
        for key in request.form:
            if key.startswith('medication') and request.form[key].strip():
                medications.append(request.form[key].strip())
        
        if len(medications) < 2:
            flash('Please enter at least two medications to check for interactions.', 'warning')
            return redirect(url_for('drug_interactions'))
            
        # Check for interactions between all medications
        results = check_multiple_drug_interactions(medications, current_user)
    
    return render_template('drug_interactions.html', 
                           title='Drug Interaction Checker',
                           form=form,
                           medication_form=medication_form,
                           results=results,
                           user=current_user)


@app.route('/check-saved-medications', methods=['POST'])
@login_required
def check_saved_medications():
    """Check interactions between saved medications"""
    form = DrugInteractionForm()
    
    # Get selected medications from the form
    medications = request.form.getlist('saved_medications')
    
    if len(medications) < 2:
        flash('Please select at least two medications to check for interactions.', 'warning')
        return redirect(url_for('drug_interactions'))
    
    # Check for interactions
    results = check_multiple_drug_interactions(medications, current_user)
    
    # Render the same template with results
    return render_template('drug_interactions.html',
                           title='Drug Interaction Checker',
                           form=form,
                           medication_form=MedicationForm(),
                           results=results,
                           user=current_user)


@app.route('/add-medication', methods=['POST'])
@login_required
def add_medication():
    """Add a medication to user's list"""
    form = MedicationForm()
    
    if form.validate_on_submit():
        # Convert form data
        start_date = form.start_date.data
        end_date = form.end_date.data
        
        # Create new medication record
        medication = UserMedication(
            user_id=current_user.id,
            medication_name=form.medication_name.data,
            dosage=form.dosage.data,
            frequency=form.frequency.data,
            start_date=start_date,
            end_date=end_date,
            reason=form.reason.data,
            is_active=form.is_active.data,
            notes=form.notes.data
        )
        
        db.session.add(medication)
        db.session.commit()
        
        flash(f'Medication "{form.medication_name.data}" added successfully.', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'Error in {getattr(form, field).label.text}: {error}', 'danger')
    
    return redirect(url_for('drug_interactions'))


@app.route('/edit-medication', methods=['POST'])
@login_required
def edit_medication():
    """Edit an existing medication"""
    medication_id = request.form.get('medication_id')
    if not medication_id:
        flash('Medication ID is required.', 'danger')
        return redirect(url_for('drug_interactions'))
    
    medication = db.session.query(UserMedication).filter_by(id=medication_id, user_id=current_user.id).first()
    if not medication:
        flash('Medication not found.', 'danger')
        return redirect(url_for('drug_interactions'))
    
    # Update medication fields
    medication.medication_name = request.form.get('medication_name')
    medication.dosage = request.form.get('dosage')
    medication.frequency = request.form.get('frequency')
    
    # Parse dates
    start_date = request.form.get('start_date')
    if start_date:
        medication.start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    else:
        medication.start_date = None
        
    end_date = request.form.get('end_date')
    if end_date:
        medication.end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    else:
        medication.end_date = None
    
    medication.reason = request.form.get('reason')
    medication.is_active = 'is_active' in request.form
    medication.notes = request.form.get('notes')
    medication.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    flash('Medication updated successfully.', 'success')
    return redirect(url_for('drug_interactions'))


@app.route('/delete-medication', methods=['POST'])
@login_required
def delete_medication():
    """Delete a medication"""
    medication_id = request.form.get('medication_id')
    if not medication_id:
        flash('Medication ID is required.', 'danger')
        return redirect(url_for('drug_interactions'))
    
    medication = db.session.query(UserMedication).filter_by(id=medication_id, user_id=current_user.id).first()
    if not medication:
        flash('Medication not found.', 'danger')
        return redirect(url_for('drug_interactions'))
    
    db.session.delete(medication)
    db.session.commit()
    
    flash('Medication deleted successfully.', 'success')
    return redirect(url_for('drug_interactions'))


@app.route('/api/drug-interaction', methods=['POST'])
@login_required
def api_drug_interaction():
    """API endpoint for drug interaction check"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    drug1 = data.get('drug1')
    drug2 = data.get('drug2')
    
    if not drug1 or not drug2:
        return jsonify({"error": "Two medications are required"}), 400
    
    # Check interaction
    interaction = check_drug_interaction(drug1, drug2, current_user)
    
    return jsonify(interaction)

# Health Scanner Routes
@app.route('/health-scanner')
@login_required
def health_scanner():
    """Health scanner page to analyze vital signs and health metrics"""
    return render_template('health_scanner.html')

@app.route('/realtime-heart-rate')
@login_required
def realtime_heart_rate():
    """Real-time heart rate monitoring using webcam data and ML"""
    return render_template('realtime_heart_rate.html')

@app.route('/api/save-health-scan', methods=['POST'])
@login_required
def api_save_health_scan():
    """API endpoint to save health scan data from real-time monitoring"""
    if not current_user.is_authenticated:
        return jsonify({"error": "Authentication required"}), 401
    
    data = request.get_json()
    
    try:
        # Create a new health scan record
        new_scan = HealthScan(
            user_id=current_user.id,
            scan_type=data.get('scan_type', 'face'),
            heart_rate=data.get('heart_rate'),
            blood_pressure_systolic=data.get('blood_pressure_systolic'),
            blood_pressure_diastolic=data.get('blood_pressure_diastolic'),
            oxygen_saturation=data.get('oxygen_saturation'),
            sympathetic_stress=data.get('stress_level'),
            scan_image_path=None,  # We don't store the actual image
            wellness_score=75 if data.get('heart_rate') and data.get('heart_rate') < 85 else 65  # Simple estimate
        )
        
        # Save to database
        db.session.add(new_scan)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "scan_id": new_scan.id,
            "message": "Health data saved successfully"
        })
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500
        
@app.route('/api/process-heart-rate-frame', methods=['POST'])
@login_required
def api_process_heart_rate_frame():
    """API endpoint to process a video frame for heart rate detection"""
    if not current_user.is_authenticated:
        return jsonify({"error": "Authentication required"}), 401
    
    try:
        # Get image data from request
        data = request.get_json()
        if not data or not data.get('image_data'):
            return jsonify({"error": "No image data provided"}), 400
            
        image_data = data.get('image_data')
        
        # Process image with ML heart rate detection
        import base64
        import numpy as np
        import cv2
        from ml_heart_rate import get_vital_signs_from_image
        
        # Decode base64 image
        if ',' in image_data:
            image_data = image_data.split(',', 1)[1]
        
        img_bytes = base64.b64decode(image_data)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        
        if img is None:
            return jsonify({"error": "Invalid image data"}), 400
            
        # Process image to get vital signs
        results = get_vital_signs_from_image(img)
        
        # Return results
        return jsonify({
            "success": True,
            "heart_rate": results["heart_rate"],
            "blood_pressure_systolic": results["blood_pressure_systolic"],
            "blood_pressure_diastolic": results["blood_pressure_diastolic"],
            "oxygen_saturation": results["oxygen_saturation"],
            "stress_level": results["stress_level"]
        })
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/health-scan', methods=['POST'])
@login_required
def api_health_scan():
    """API endpoint to process health scan data for multiple scan types"""
    if not current_user.is_authenticated:
        return jsonify({"error": "Authentication required"}), 401
    
    # Check if user has remaining searches
    if current_user.get_remaining_searches() <= 0:
        return jsonify({"error": "You have reached your search limit. Please upgrade your subscription."}), 403
    
    # Handle both JSON and form data requests
    if request.is_json:
        data = request.get_json()
        scan_type = data.get('scan_type', 'face')
        image_data = data.get('image_data') # Base64 encoded image
    else:
        scan_type = request.form.get('scan_type', 'face')
        image_data = request.form.get('image_data') # Base64 encoded image
    
    # Validate scan type
    valid_scan_types = ['face', 'tongue', 'eye', 'skin']
    if scan_type not in valid_scan_types:
        return jsonify({"error": "Invalid scan type"}), 400
    
    # Validate image data
    if not image_data:
        return jsonify({"error": "Image data is required"}), 400
    
    try:
        # Record the search
        record_search(current_user.id, f"Health Scan: {scan_type}")
        
        # Process scan with OpenAI API
        import json
        import base64
        import tempfile
        import os
        from utils import analyze_health_data
        
        # Save the image temporarily for analysis
        temp_dir = tempfile.mkdtemp()
        temp_image_path = os.path.join(temp_dir, f"scan_{current_user.id}.jpg")
        
        try:
            # Extract base64 data if it includes the data URL prefix
            if image_data and ',' in image_data:
                image_data = image_data.split(',', 1)[1]
                
            with open(temp_image_path, "wb") as f:
                f.write(base64.b64decode(image_data))
            
            # Process the image based on scan type
            result = analyze_health_data(temp_image_path, scan_type)
            
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_image_path):
                os.remove(temp_image_path)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
        
        # Save the scan to database
        if result:
            # Create a base health scan object with common fields
            new_scan = HealthScan(
                user_id=current_user.id,
                scan_type=scan_type,
                scan_image_path=None,  # We don't store the actual image
                wellness_score=result.get('wellness_score')
            )
            
            # Add fields specific to each scan type
            if scan_type == 'face':
                new_scan.heart_rate = result.get('heart_rate')
                new_scan.blood_pressure_systolic = result.get('blood_pressure_systolic')
                new_scan.blood_pressure_diastolic = result.get('blood_pressure_diastolic')
                new_scan.breathing_rate = result.get('breathing_rate')
                new_scan.oxygen_saturation = result.get('oxygen_saturation')
                new_scan.sympathetic_stress = result.get('sympathetic_stress')
                new_scan.parasympathetic_activity = result.get('parasympathetic_activity')
                new_scan.prq = result.get('prq')
                new_scan.hemoglobin = result.get('hemoglobin')
                new_scan.hemoglobin_a1c = result.get('hemoglobin_a1c')
                new_scan.ascvd_risk = result.get('ascvd_risk')
                new_scan.hypertension_risk = result.get('hypertension_risk')
                new_scan.glucose_risk = result.get('glucose_risk')
                new_scan.cholesterol_risk = result.get('cholesterol_risk')
                new_scan.tuberculosis_risk = result.get('tuberculosis_risk')
                new_scan.heart_age = result.get('heart_age')
            
            elif scan_type == 'tongue':
                new_scan.tongue_color = result.get('tongue_color')
                new_scan.tongue_coating = result.get('tongue_coating')
                new_scan.tongue_shape = result.get('tongue_shape')
                new_scan.tcm_diagnosis = result.get('tcm_diagnosis')
                new_scan.vitamin_deficiency = result.get('vitamin_deficiency')
                new_scan.infection_indicator = result.get('infection_indicator')
            
            elif scan_type == 'eye':
                new_scan.sclera_color = result.get('sclera_color')
                new_scan.conjunctiva_color = result.get('conjunctiva_color')
                new_scan.eye_redness = result.get('eye_redness')
                new_scan.pupil_reactivity = result.get('pupil_reactivity')
                new_scan.eye_condition = result.get('eye_condition')
            
            elif scan_type == 'skin':
                new_scan.skin_color = result.get('skin_color')
                new_scan.skin_texture = result.get('skin_texture')
                new_scan.rash_detection = result.get('rash_detection', False)
                new_scan.rash_pattern = result.get('rash_pattern')
                new_scan.skin_condition = result.get('skin_condition')
            
            # Add notes and recommendations
            if result.get('notes'):
                new_scan.notes = json.dumps(result.get('notes', {}))
            
            # Save to database
            db.session.add(new_scan)
            db.session.commit()
            
            # Add the scan ID to the result for reference
            result['scan_id'] = new_scan.id
        
        return jsonify(result)
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

# Food Scanner Routes
@app.route('/food-scanner')
@login_required
def food_scanner():
    """Food scanner page to analyze nutrition content of food"""
    return render_template('food_scanner.html')

@app.route('/api/food-scan', methods=['POST'])
@login_required
def api_food_scan():
    """API endpoint to process food scan data"""
    if not current_user.is_authenticated:
        return jsonify({"error": "Authentication required"}), 401
    
    # Check if user has remaining searches
    if current_user.get_remaining_searches() <= 0:
        return jsonify({"error": "You have reached your search limit. Please upgrade your subscription."}), 403
    
    try:
        # Get image data from request
        if 'food_image' not in request.files:
            return jsonify({"error": "No image provided"}), 400
        
        food_image = request.files['food_image']
        food_name = request.form.get('food_name', 'Unknown Food')
        
        # Record the search
        record_search(current_user.id, f"Food Scan: {food_name}")
        
        # Analyze food image with OpenAI API
        import json
        import os
        from utils import analyze_food_image
        
        # Save the uploaded image temporarily
        image_path = os.path.join('/tmp', food_image.filename)
        food_image.save(image_path)
        
        # Process the image
        result = analyze_food_image(image_path, food_name)
        
        # Save the food scan to database
        if result:
            new_scan = FoodScan(
                user_id=current_user.id,
                food_name=food_name,
                calories=result.get('calories'),
                protein=result.get('protein'),
                carbs=result.get('carbs'),
                fat=result.get('fat'),
                fiber=result.get('fiber'),
                sugar=result.get('sugar'),
                sodium=result.get('sodium'),
                cholesterol=result.get('cholesterol'),
                food_image_url=None,  # We don't store images for now
                data=json.dumps(result)
            )
            db.session.add(new_scan)
            db.session.commit()
        
        # Remove temporary file
        os.remove(image_path)
        
        return jsonify(result)
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

# BMI Calculator Routes
@app.route('/bmi-calculator')
@app.route('/bmi_calculator')  # Add this alternative route for the url_for function
def bmi_calculator():
    """BMI calculator page"""
    return render_template('bmi_calculator.html')

@app.route('/api/calculate-bmi', methods=['POST'])
@login_required
def api_calculate_bmi():
    """API endpoint to calculate BMI and generate diet plan if needed"""
    if not current_user.is_authenticated:
        return jsonify({"error": "Authentication required"}), 401
    
    data = request.get_json()
    
    try:
        height = float(data.get('height', 0))  # height in cm
        weight = float(data.get('weight', 0))  # weight in kg
        age = int(data.get('age', 25))
        gender = data.get('gender', 'male')
        is_pregnant = data.get('is_pregnant', False)
        activity_level = data.get('activity_level', 'moderate')
        
        if height <= 0 or weight <= 0:
            return jsonify({"error": "Invalid height or weight"}), 400
        
        # Calculate BMI
        height_m = height / 100  # convert cm to m
        bmi = weight / (height_m * height_m)
        
        # Determine BMI category
        if bmi < 18.5:
            category = "Underweight"
        elif bmi < 25:
            category = "Normal"
        elif bmi < 30:
            category = "Overweight"
        else:
            category = "Obese"
        
        # Generate diet plan if overweight or obese
        diet_plan = None
        if category in ["Overweight", "Obese"] or is_pregnant:
            # Record the search for diet plan
            record_search(current_user.id, f"BMI Calculator and Diet Plan")
            
            from utils import generate_diet_plan
            diet_plan = generate_diet_plan(bmi, category, age, gender, is_pregnant, activity_level)
        
        # Save BMI record to database
        if current_user.is_authenticated:
            new_record = BMIRecord(
                user_id=current_user.id,
                height=height,
                weight=weight,
                bmi_value=bmi,
                bmi_category=category,
                diet_plan=json.dumps(diet_plan) if diet_plan else None
            )
            db.session.add(new_record)
            db.session.commit()
        
        result = {
            "bmi": round(bmi, 1),
            "category": category,
            "diet_plan": diet_plan
        }
        
        return jsonify(result)
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

# Reminder Routes
@app.route('/reminders')
@login_required
def reminders():
    """Display user's reminders"""
    user_reminders = db.session.query(Reminder).filter_by(user_id=current_user.id).order_by(Reminder.schedule_time).all()
    return render_template('reminders.html', reminders=user_reminders)

@app.route('/reminders/add', methods=['GET', 'POST'])
@login_required
def add_reminder():
    """Add a new reminder"""
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description', '')
        reminder_type = request.form.get('reminder_type', 'medicine')
        time_str = request.form.get('schedule_time')
        repeat_type = request.form.get('repeat_type', 'daily')
        
        # Process repeat days for weekly reminders
        if repeat_type == 'weekly':
            repeat_days = request.form.getlist('repeat_days')
            if not repeat_days:
                flash('Please select at least one day for weekly reminders.', 'danger')
                return redirect(url_for('add_reminder'))
            repeat_days = ','.join(repeat_days)
        else:
            repeat_days = ''
        
        # Validate inputs
        if not title or not time_str:
            flash('Title and schedule time are required.', 'danger')
            return redirect(url_for('add_reminder'))
        
        # Parse time string
        try:
            schedule_time = datetime.strptime(time_str, '%H:%M').time()
        except ValueError:
            flash('Invalid time format. Please use HH:MM format.', 'danger')
            return redirect(url_for('add_reminder'))
        
        # Handle voice recording base64 data
        audio_path = None
        audio_blob = request.form.get('audio_blob')
        if audio_blob and audio_blob.startswith('data:audio'):
            try:
                # Extract the base64 data from the data URL
                import base64
                audio_data = audio_blob.split(',')[1]
                audio_binary = base64.b64decode(audio_data)
                
                # Save the audio file
                audio_filename = f"reminder_{current_user.id}_{int(datetime.utcnow().timestamp())}.wav"
                audio_path = os.path.join('static', 'uploads', 'reminders', audio_filename)
                os.makedirs(os.path.dirname(audio_path), exist_ok=True)
                
                with open(audio_path, 'wb') as f:
                    f.write(audio_binary)
                
                audio_path = f"/{audio_path}"
            except Exception as e:
                app.logger.error(f"Error saving audio recording: {str(e)}")
                flash('There was an error saving your voice recording.', 'danger')
        
        # Create new reminder
        new_reminder = Reminder(
            user_id=current_user.id,
            title=title,
            description=description,
            reminder_type=reminder_type,
            schedule_time=schedule_time,
            repeat_type=repeat_type,
            repeat_days=repeat_days,
            audio_path=audio_path,
            active=True
        )
        
        db.session.add(new_reminder)
        db.session.commit()
        
        flash('Reminder added successfully!', 'success')
        return redirect(url_for('reminders'))
        
    return render_template('add_reminder.html')

@app.route('/reminders/<int:reminder_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_reminder(reminder_id):
    """Edit an existing reminder"""
    reminder = db.session.query(Reminder).filter_by(id=reminder_id, user_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        reminder.title = request.form.get('title')
        reminder.description = request.form.get('description', '')
        reminder.reminder_type = request.form.get('reminder_type', 'medicine')
        time_str = request.form.get('schedule_time')
        reminder.repeat_type = request.form.get('repeat_type', 'daily')
        
        # Process repeat days for weekly reminders
        if reminder.repeat_type == 'weekly':
            repeat_days = request.form.getlist('repeat_days')
            if not repeat_days:
                flash('Please select at least one day for weekly reminders.', 'danger')
                return redirect(url_for('edit_reminder', reminder_id=reminder_id))
            reminder.repeat_days = ','.join(repeat_days)
        else:
            reminder.repeat_days = ''
            
        reminder.active = 'active' in request.form
        
        # Parse time string
        try:
            reminder.schedule_time = datetime.strptime(time_str, '%H:%M').time()
        except ValueError:
            flash('Invalid time format. Please use HH:MM format.', 'danger')
            return redirect(url_for('edit_reminder', reminder_id=reminder_id))
        
        # Handle voice recording base64 data
        audio_blob = request.form.get('audio_blob')
        if audio_blob and audio_blob.startswith('data:audio'):
            try:
                # Delete old audio file if exists
                if reminder.audio_path and os.path.exists(reminder.audio_path):
                    os.remove(reminder.audio_path)
                
                # Extract the base64 data from the data URL
                import base64
                audio_data = audio_blob.split(',')[1]
                audio_binary = base64.b64decode(audio_data)
                
                # Save the new audio file
                audio_filename = f"reminder_{current_user.id}_{reminder_id}_{int(datetime.utcnow().timestamp())}.wav"
                audio_path = os.path.join('static', 'uploads', 'reminders', audio_filename)
                os.makedirs(os.path.dirname(audio_path), exist_ok=True)
                
                with open(audio_path, 'wb') as f:
                    f.write(audio_binary)
                
                reminder.audio_path = f"/{audio_path}"
            except Exception as e:
                app.logger.error(f"Error saving audio recording: {str(e)}")
                flash('There was an error saving your voice recording.', 'danger')
        
        db.session.commit()
        flash('Reminder updated successfully!', 'success')
        return redirect(url_for('reminders'))
        
    return render_template('edit_reminder.html', reminder=reminder)

@app.route('/reminders/<int:reminder_id>/delete', methods=['POST'])
@login_required
def delete_reminder(reminder_id):
    """Delete a reminder"""
    reminder = db.session.query(Reminder).filter_by(id=reminder_id, user_id=current_user.id).first_or_404()
    
    # Delete audio file if exists
    if reminder.audio_path and os.path.exists(reminder.audio_path):
        os.remove(reminder.audio_path)
    
    db.session.delete(reminder)
    db.session.commit()
    
    flash('Reminder deleted successfully!', 'success')
    return redirect(url_for('reminders'))

@app.route('/reminders/<int:reminder_id>/toggle-active', methods=['POST'])
@login_required
def toggle_reminder_active(reminder_id):
    """Toggle the active status of a reminder"""
    reminder = db.session.query(Reminder).filter_by(id=reminder_id, user_id=current_user.id).first_or_404()
    
    try:
        data = request.get_json()
        active = data.get('active', not reminder.active)
        
        reminder.active = active
        db.session.commit()
        
        return jsonify({'success': True, 'active': reminder.active})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reminders/active')
@login_required
def get_active_reminders():
    """API endpoint to get active reminders for the current time"""
    now = datetime.utcnow()
    current_time = now.time()
    current_day = now.isoweekday()  # 1-7 (Monday-Sunday)
    
    # Get all active reminders for the user
    reminders = db.session.query(Reminder).filter(
        Reminder.user_id == current_user.id,
        Reminder.active == True
    ).all()
    
    # Manually filter for current time (±1 minute)
    current_minute = current_time.hour * 60 + current_time.minute
    filtered_reminders = []
    
    for reminder in reminders:
        reminder_minute = reminder.schedule_time.hour * 60 + reminder.schedule_time.minute
        diff = abs(current_minute - reminder_minute)
        if diff <= 1 or diff >= 1439:  # Within 1 minute or at day boundary
            filtered_reminders.append(reminder)
    
    reminders = filtered_reminders
    
    # Filter by repeat days if not daily
    active_reminders = []
    for reminder in reminders:
        if reminder.repeat_type == 'daily' or (
            reminder.repeat_type == 'weekly' and 
            str(current_day) in (reminder.repeat_days.split(',') if reminder.repeat_days else [])
        ):
            # Update last triggered time
            reminder.last_triggered = datetime.utcnow()
            db.session.commit()
            
            active_reminders.append({
                'id': reminder.id,
                'title': reminder.title,
                'description': reminder.description,
                'type': reminder.reminder_type,
                'audio_url': reminder.audio_path
            })
    
    return jsonify(active_reminders)

# Doctor Routes
@app.route('/doctors')
def doctors_listing():
    """Public listing of verified doctors"""
    doctors = db.session.query(Doctor).filter_by(is_verified=True, is_active=True).all()
    specialties = db.session.query(Doctor.specialty).distinct().all()
    unique_specialties = [s[0] for s in specialties]
    
    return render_template('doctors_listing.html', 
                          doctors=doctors, 
                          specialties=unique_specialties)

@app.route('/doctors/search')
def search_doctors():
    """Search for doctors by specialty or name"""
    query = request.args.get('query', '')
    specialty = request.args.get('specialty', '')
    
    if specialty:
        doctors = db.session.query(Doctor).filter(
            Doctor.is_verified == True,
            Doctor.is_active == True,
            Doctor.specialty == specialty
        ).all()
    elif query:
        doctors = db.session.query(Doctor).filter(
            Doctor.is_verified == True,
            Doctor.is_active == True,
            db.or_(
                Doctor.full_name.ilike(f'%{query}%'),
                Doctor.specialty.ilike(f'%{query}%'),
                Doctor.bio.ilike(f'%{query}%')
            )
        ).all()
    else:
        doctors = []
    
    return render_template('doctor_search_results.html', 
                          doctors=doctors, 
                          query=query,
                          specialty=specialty)

@app.route('/doctors/<int:doctor_id>')
def doctor_profile(doctor_id):
    """Public doctor profile page"""
    doctor = db.session.query(Doctor).filter_by(id=doctor_id, is_verified=True, is_active=True).first_or_404()
    reviews = db.session.query(DoctorReview).filter_by(doctor_id=doctor_id).order_by(DoctorReview.created_at.desc()).all()
    
    # Check if the current user has already reviewed this doctor
    user_has_reviewed = False
    if current_user.is_authenticated:
        user_review = db.session.query(DoctorReview).filter_by(
            doctor_id=doctor_id, 
            user_id=current_user.id
        ).first()
        user_has_reviewed = user_review is not None
    
    return render_template('doctor_profile.html', 
                          doctor=doctor, 
                          reviews=reviews,
                          user_has_reviewed=user_has_reviewed)

@app.route('/doctor/dashboard')
@login_required
def doctor_dashboard():
    """Dashboard for doctors"""
    # Check if user has a doctor profile
    doctor = db.session.query(Doctor).filter_by(user_id=current_user.id).first()
    
    if not doctor:
        flash('You need to create a doctor profile first.', 'warning')
        return redirect(url_for('create_doctor_profile'))
    
    # Use optimized queries to reduce database load - using scalar subqueries
    # Get appointments counts with a single query
    appointment_counts = db.session.query(
        Appointment.status,
        db.func.count(Appointment.id)
    ).filter(
        Appointment.doctor_id == doctor.id,
        Appointment.appointment_date >= datetime.utcnow().date()
    ).group_by(Appointment.status).all()
    
    # Convert to dictionary for easy lookup
    appointment_stats = {status: count for status, count in appointment_counts}
    
    # Get upcoming appointments efficiently
    upcoming_appointments = db.session.query(
        Appointment, User
    ).join(
        User, User.id == Appointment.patient_id
    ).filter(
        Appointment.doctor_id == doctor.id,
        Appointment.status.in_(['pending', 'confirmed']),
        Appointment.appointment_date >= datetime.utcnow().date()
    ).order_by(
        Appointment.appointment_date, 
        Appointment.appointment_time
    ).all()
    
    # Extract appointment objects for template
    appointments = [appt for appt, _ in upcoming_appointments]
    
    # Get reviews with prefetched user data
    recent_reviews = db.session.query(
        DoctorReview, User
    ).join(
        User, User.id == DoctorReview.user_id
    ).filter(
        DoctorReview.doctor_id == doctor.id
    ).order_by(
        DoctorReview.created_at.desc()
    ).limit(5).all()
    
    # Extract review objects for template
    reviews = [review for review, _ in recent_reviews]
    
    # Get unread message count
    unread_messages_count = db.session.query(
        db.func.count(Message.id)
    ).filter(
        Message.recipient_id == current_user.id,
        Message.is_read == False
    ).scalar() or 0
    
    return render_template('doctor_dashboard.html', 
                          doctor=doctor,
                          appointments=appointments,
                          reviews=reviews,
                          pending_appointments=appointment_stats.get('pending', 0),
                          confirmed_appointments=appointment_stats.get('confirmed', 0),
                          today_appointments=db.session.query(db.func.count(Appointment.id))
                                              .filter(Appointment.doctor_id == doctor.id,
                                                     Appointment.appointment_date == datetime.utcnow().date()).scalar() or 0,
                          unread_messages=unread_messages_count)

@app.route('/doctor/profile/create', methods=['GET', 'POST'])
@login_required
def create_doctor_profile():
    """Create a doctor profile"""
    # Check if the user already has a doctor profile
    existing_profile = db.session.query(Doctor).filter_by(user_id=current_user.id).first()
    if existing_profile:
        flash('You already have a doctor profile.', 'info')
        return redirect(url_for('edit_doctor_profile'))
    
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        specialty = request.form.get('specialty')
        qualification = request.form.get('qualification')
        experience_years = request.form.get('experience_years')
        license_number = request.form.get('license_number')
        bio = request.form.get('bio')
        address = request.form.get('address')
        city = request.form.get('city')
        state = request.form.get('state')
        country = request.form.get('country')
        postal_code = request.form.get('postal_code')
        consultation_fee = request.form.get('consultation_fee')
        available_days = ','.join(request.form.getlist('available_days'))
        available_hours = request.form.get('available_hours')
        
        # Validate required fields
        if not full_name or not specialty or not qualification or not license_number:
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('create_doctor_profile'))
        
        # Check if license number is already registered
        existing_license = db.session.query(Doctor).filter_by(license_number=license_number).first()
        if existing_license:
            flash('This license number is already registered.', 'danger')
            return redirect(url_for('create_doctor_profile'))
        
        # Handle profile image and document uploads
        profile_image = None
        degree_document = None
        license_document = None
        id_proof = None
        additional_document = None
        
        # Create upload directory if it doesn't exist
        upload_dir = os.path.join('static', 'uploads', 'doctors')
        docs_dir = os.path.join(upload_dir, 'documents')
        os.makedirs(upload_dir, exist_ok=True)
        os.makedirs(docs_dir, exist_ok=True)
        
        # Save profile image if provided
        if 'profile_image' in request.files:
            image_file = request.files['profile_image']
            if image_file and image_file.filename:
                image_filename = f"doctor_{current_user.id}_{int(datetime.utcnow().timestamp())}.jpg"
                image_path = os.path.join(upload_dir, image_filename)
                image_file.save(image_path)
                profile_image = '/' + image_path
        
        # Process degree document
        if 'degree_document' in request.files:
            doc_file = request.files['degree_document']
            if doc_file and doc_file.filename:
                file_ext = doc_file.filename.rsplit('.', 1)[1].lower() if '.' in doc_file.filename else ''
                if file_ext in ['pdf', 'jpg', 'jpeg', 'png']:
                    doc_filename = f"degree_{current_user.id}_{int(datetime.utcnow().timestamp())}.{file_ext}"
                    doc_path = os.path.join(docs_dir, doc_filename)
                    doc_file.save(doc_path)
                    degree_document = '/' + doc_path
        
        # Process license document
        if 'license_document' in request.files:
            doc_file = request.files['license_document']
            if doc_file and doc_file.filename:
                file_ext = doc_file.filename.rsplit('.', 1)[1].lower() if '.' in doc_file.filename else ''
                if file_ext in ['pdf', 'jpg', 'jpeg', 'png']:
                    doc_filename = f"license_{current_user.id}_{int(datetime.utcnow().timestamp())}.{file_ext}"
                    doc_path = os.path.join(docs_dir, doc_filename)
                    doc_file.save(doc_path)
                    license_document = '/' + doc_path
        
        # Process ID proof
        if 'id_proof' in request.files:
            doc_file = request.files['id_proof']
            if doc_file and doc_file.filename:
                file_ext = doc_file.filename.rsplit('.', 1)[1].lower() if '.' in doc_file.filename else ''
                if file_ext in ['pdf', 'jpg', 'jpeg', 'png']:
                    doc_filename = f"id_{current_user.id}_{int(datetime.utcnow().timestamp())}.{file_ext}"
                    doc_path = os.path.join(docs_dir, doc_filename)
                    doc_file.save(doc_path)
                    id_proof = '/' + doc_path
        
        # Process additional document
        if 'additional_document' in request.files:
            doc_file = request.files['additional_document']
            if doc_file and doc_file.filename:
                file_ext = doc_file.filename.rsplit('.', 1)[1].lower() if '.' in doc_file.filename else ''
                if file_ext in ['pdf', 'jpg', 'jpeg', 'png']:
                    doc_filename = f"additional_{current_user.id}_{int(datetime.utcnow().timestamp())}.{file_ext}"
                    doc_path = os.path.join(docs_dir, doc_filename)
                    doc_file.save(doc_path)
                    additional_document = '/' + doc_path
        
        # Create new doctor profile
        new_doctor = Doctor(
            user_id=current_user.id,
            full_name=full_name,
            specialty=specialty,
            qualification=qualification,
            experience_years=int(experience_years),
            license_number=license_number,
            bio=bio,
            address=address,
            city=city,
            state=state,
            country=country,
            postal_code=postal_code,
            consultation_fee=float(consultation_fee) if consultation_fee else None,
            available_days=available_days,
            available_hours=available_hours,
            profile_image=profile_image,
            degree_document=degree_document,
            license_document=license_document,
            id_proof=id_proof,
            additional_document=additional_document,
            is_verified=False  # Needs admin approval
        )
        
        db.session.add(new_doctor)
        db.session.commit()
        
        flash('Your doctor profile has been created and is pending verification by admin.', 'success')
        return redirect(url_for('home'))
    
    return render_template('create_doctor_profile.html')

@app.route('/doctor/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_doctor_profile():
    """Edit doctor profile"""
    doctor = db.session.query(Doctor).filter_by(user_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        doctor.full_name = request.form.get('full_name')
        doctor.specialty = request.form.get('specialty')
        doctor.qualification = request.form.get('qualification')
        doctor.experience_years = int(request.form.get('experience_years'))
        doctor.bio = request.form.get('bio')
        doctor.address = request.form.get('address')
        doctor.city = request.form.get('city')
        doctor.state = request.form.get('state')
        doctor.country = request.form.get('country')
        doctor.postal_code = request.form.get('postal_code')
        doctor.consultation_fee = float(request.form.get('consultation_fee')) if request.form.get('consultation_fee') else None
        doctor.available_days = ','.join(request.form.getlist('available_days'))
        doctor.available_hours = request.form.get('available_hours')
        
        # Handle profile image upload
        if 'profile_image' in request.files:
            image_file = request.files['profile_image']
            if image_file and image_file.filename:
                # Delete old image if exists
                if doctor.profile_image and os.path.exists(doctor.profile_image):
                    os.remove(doctor.profile_image)
                
                # Save the new image
                image_filename = f"doctor_{current_user.id}_{int(datetime.utcnow().timestamp())}.jpg"
                image_path = os.path.join('static', 'uploads', 'doctors', image_filename)
                os.makedirs(os.path.dirname(image_path), exist_ok=True)
                image_file.save(image_path)
                doctor.profile_image = image_path
        
        # Mark as needing verification again if certain fields changed
        if 'license_number' in request.form and request.form.get('license_number') != doctor.license_number:
            doctor.license_number = request.form.get('license_number')
            doctor.is_verified = False
            flash('Your profile will need to be re-verified due to license number change.', 'warning')
        
        db.session.commit()
        flash('Doctor profile updated successfully!', 'success')
        return redirect(url_for('doctor_dashboard'))
    
    return render_template('edit_doctor_profile.html', doctor=doctor)

@app.route('/doctor/appointment/<int:appointment_id>/update', methods=['POST'])
@login_required
def update_appointment(appointment_id):
    """Update appointment status"""
    # Get the doctor profile
    doctor = db.session.query(Doctor).filter_by(user_id=current_user.id).first()
    if not doctor:
        abort(403)
    
    # Get the appointment
    appointment = db.session.query(Appointment).filter_by(id=appointment_id, doctor_id=doctor.id).first_or_404()
    
    status = request.form.get('status')
    if status in ['confirmed', 'cancelled', 'completed']:
        appointment.status = status
        appointment.notes = request.form.get('notes', appointment.notes)
        db.session.commit()
        flash(f'Appointment status updated to {status}.', 'success')
    
    return redirect(url_for('doctor_dashboard'))

# Patient-Doctor interactions
@app.route('/appointments')
@login_required
def user_appointments():
    """View user's appointments with doctors"""
    appointments = db.session.query(Appointment).filter_by(patient_id=current_user.id).all()
    return render_template('user_appointments.html', appointments=appointments)

@app.route('/doctors/<int:doctor_id>/book', methods=['GET', 'POST'])
@login_required
def book_appointment(doctor_id):
    """Book an appointment with a doctor"""
    doctor = db.session.query(Doctor).filter_by(id=doctor_id, is_verified=True, is_active=True).first_or_404()
    
    # Add the current date for the form
    now = datetime.utcnow()
    
    if request.method == 'POST':
        date_str = request.form.get('appointment_date')
        time_str = request.form.get('appointment_time')
        appointment_type = request.form.get('appointment_type')
        notes = request.form.get('notes', '')
        
        try:
            appointment_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            appointment_time = datetime.strptime(time_str, '%H:%M').time()
        except ValueError:
            flash('Invalid date or time format.', 'danger')
            return redirect(url_for('book_appointment', doctor_id=doctor_id))
        
        # Check if the appointment slot is available
        existing_appointment = db.session.query(Appointment).filter(
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_date == appointment_date,
            Appointment.appointment_time == appointment_time,
            Appointment.status.in_(['pending', 'confirmed'])
        ).first()
        
        if existing_appointment:
            flash('This appointment slot is already booked. Please select another time.', 'danger')
            return redirect(url_for('book_appointment', doctor_id=doctor_id))
        
        # Create new appointment
        new_appointment = Appointment(
            patient_id=current_user.id,
            doctor_id=doctor_id,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            type=appointment_type,
            notes=notes
        )
        
        db.session.add(new_appointment)
        
        # Share patient's health data with doctor
        # For security, we would typically create a separate table for shared health records
        # but for simplicity, we'll add a note about sharing
        new_appointment.notes += "\n[System: Patient's health records have been shared with the doctor.]"
        
        db.session.commit()
        
        flash('Appointment booked successfully! The doctor will confirm your appointment.', 'success')
        return redirect(url_for('user_appointments'))
    
    available_days = doctor.available_days.split(',') if doctor.available_days else []
    available_hours = doctor.available_hours
    
    return render_template('book_appointment.html', 
                          doctor=doctor,
                          available_days=available_days,
                          available_hours=available_hours,
                          now=now)

@app.route('/doctors/<int:doctor_id>/review', methods=['POST'])
@login_required
def review_doctor(doctor_id):
    """Submit a review for a doctor"""
    doctor = db.session.query(Doctor).filter_by(id=doctor_id, is_verified=True, is_active=True).first_or_404()
    
    # Check if user has an appointment with this doctor
    has_appointment = db.session.query(Appointment).filter_by(
        patient_id=current_user.id,
        doctor_id=doctor_id,
        status='completed'
    ).first()
    
    if not has_appointment:
        flash('You can only review doctors after a completed appointment.', 'danger')
        return redirect(url_for('doctor_profile', doctor_id=doctor_id))
    
    # Check if user has already reviewed this doctor
    existing_review = db.session.query(DoctorReview).filter_by(
        doctor_id=doctor_id,
        user_id=current_user.id
    ).first()
    
    if existing_review:
        # Update existing review
        existing_review.rating = int(request.form.get('rating'))
        existing_review.review = request.form.get('review', '')
        db.session.commit()
        flash('Your review has been updated.', 'success')
    else:
        # Create new review
        new_review = DoctorReview(
            doctor_id=doctor_id,
            user_id=current_user.id,
            rating=int(request.form.get('rating')),
            review=request.form.get('review', '')
        )
        db.session.add(new_review)
        db.session.commit()
        
        # Update doctor's average rating
        update_doctor_rating(doctor_id)
        
        flash('Thank you for your review!', 'success')
    
    return redirect(url_for('doctor_profile', doctor_id=doctor_id))

# Messaging system
@app.route('/messages')
@login_required
def messages():
    """User's message inbox"""
    received_messages = db.session.query(Message).filter_by(recipient_id=current_user.id).order_by(Message.created_at.desc()).all()
    sent_messages = db.session.query(Message).filter_by(sender_id=current_user.id).order_by(Message.created_at.desc()).all()
    
    # Mark unread messages as read
    unread_messages = db.session.query(Message).filter_by(recipient_id=current_user.id, is_read=False).all()
    for message in unread_messages:
        message.is_read = True
    db.session.commit()
    
    # Get unique conversation partners
    conversation_partners = set()
    for message in received_messages:
        conversation_partners.add(message.sender_id)
    for message in sent_messages:
        conversation_partners.add(message.recipient_id)
    
    # Get user info for conversation partners
    users = db.session.query(User).filter(User.id.in_(conversation_partners)).all()
    user_map = {user.id: user.username for user in users}
    
    # Check which users are doctors
    doctors = db.session.query(Doctor).filter(Doctor.user_id.in_(conversation_partners)).all()
    doctor_user_ids = [doctor.user_id for doctor in doctors]
    
    return render_template('messages.html', 
                          received_messages=received_messages,
                          sent_messages=sent_messages,
                          user_map=user_map,
                          doctor_user_ids=doctor_user_ids)

@app.route('/messages/send/<int:recipient_id>', methods=['GET', 'POST'])
@login_required
def send_message(recipient_id):
    """Send a message to a user with optional file attachment"""
    recipient = db.session.query(User).filter_by(id=recipient_id).first_or_404()
    
    if request.method == 'POST':
        message_text = request.form.get('message')
        
        if not message_text:
            flash('Message cannot be empty.', 'danger')
            return redirect(url_for('send_message', recipient_id=recipient_id))
        
        # Initialize attachment variables
        attachment_path = None
        attachment_type = None
        attachment_filename = None
        
        # Check if there's a file attachment
        if 'attachment' in request.files and request.files['attachment'].filename:
            attachment = request.files['attachment']
            
            # Make sure the file has a valid extension
            allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'txt'}
            file_ext = attachment.filename.rsplit('.', 1)[1].lower() if '.' in attachment.filename else ''
            
            if file_ext in allowed_extensions:
                # Create a directory for message attachments if it doesn't exist
                attachment_dir = os.path.join('static', 'uploads', 'messages')
                if not os.path.exists(attachment_dir):
                    os.makedirs(attachment_dir)
                
                # Generate a secure filename to prevent path traversal attacks
                timestamp = int(time.time())
                secure_filename = f"message_{current_user.id}_{recipient_id}_{timestamp}.{file_ext}"
                filepath = os.path.join(attachment_dir, secure_filename)
                
                # Save the file
                attachment.save(filepath)
                
                # Determine the general attachment type
                if file_ext in {'png', 'jpg', 'jpeg', 'gif'}:
                    attachment_type = 'image'
                elif file_ext in {'pdf', 'doc', 'docx'}:
                    attachment_type = 'document'
                else:
                    attachment_type = 'file'
                
                # Save the path and original filename
                attachment_path = '/' + filepath  # Store as a URL path
                attachment_filename = attachment.filename
                
                # Add a note about the attachment to the message text
                message_text += f'\n\n[Attachment: {attachment.filename}]'
            else:
                flash('Invalid file type. Please upload a valid file.', 'warning')
        
        # Create the message
        new_message = Message(
            sender_id=current_user.id,
            recipient_id=recipient_id,
            message=message_text,
            attachment_path=attachment_path,
            attachment_type=attachment_type,
            attachment_filename=attachment_filename
        )
        
        db.session.add(new_message)
        db.session.commit()
        
        flash('Message sent successfully!', 'success')
        return redirect(url_for('messages'))
    
    # Get previous conversation with this user
    conversation = db.session.query(Message).filter(
        db.or_(
            db.and_(Message.sender_id == current_user.id, Message.recipient_id == recipient_id),
            db.and_(Message.sender_id == recipient_id, Message.recipient_id == current_user.id)
        )
    ).order_by(Message.created_at).all()
    
    # Check if recipient is a doctor
    is_doctor = db.session.query(Doctor).filter_by(user_id=recipient_id).first() is not None
    
    return render_template('send_message.html', 
                          recipient=recipient,
                          conversation=conversation,
                          is_doctor=is_doctor)

# Admin doctor verification
@app.route('/admin/doctors')
@login_required
def admin_doctors():
    """Admin page for doctor verification"""
    if not current_user.is_admin:
        abort(403)
    
    pending_doctors = db.session.query(Doctor).filter_by(is_verified=False).all()
    verified_doctors = db.session.query(Doctor).filter_by(is_verified=True).all()
    
    return render_template('admin_doctors.html', 
                          pending_doctors=pending_doctors,
                          verified_doctors=verified_doctors)

@app.route('/admin/doctors/<int:doctor_id>/verify', methods=['POST'])
@login_required
def verify_doctor(doctor_id):
    """Verify a doctor's profile"""
    if not current_user.is_admin:
        abort(403)
    
    doctor = db.session.query(Doctor).filter_by(id=doctor_id).first_or_404()
    doctor.is_verified = True
    db.session.commit()
    
    flash(f'Doctor {doctor.full_name} has been verified.', 'success')
    return redirect(url_for('admin_doctors'))

@app.route('/admin/doctors/<int:doctor_id>/reject', methods=['POST'])
@login_required
def reject_doctor(doctor_id):
    """Reject a doctor's verification request"""
    if not current_user.is_admin:
        abort(403)
    
    doctor = db.session.query(Doctor).filter_by(id=doctor_id).first_or_404()
    doctor.is_active = False
    doctor.is_verified = False
    db.session.commit()
    
    flash(f'Doctor {doctor.full_name} has been rejected.', 'warning')
    return redirect(url_for('admin_doctors'))

# Helper function for doctor ratings
def update_doctor_rating(doctor_id):
    """Update a doctor's average rating"""
    doctor = db.session.query(Doctor).filter_by(id=doctor_id).first()
    if not doctor:
        return
    
    reviews = db.session.query(DoctorReview).filter_by(doctor_id=doctor_id).all()
    if not reviews:
        doctor.average_rating = 0.0
        doctor.total_ratings = 0
    else:
        doctor.average_rating = sum(review.rating for review in reviews) / len(reviews)
        doctor.total_ratings = len(reviews)
    
    db.session.commit()


# User Settings and Account Management
@app.route('/user/settings', methods=['GET'])
@login_required
def user_settings():
    """User settings page"""
    return render_template('user_settings.html')


@app.route('/user/update-profile', methods=['POST'])
@login_required
def update_profile():
    """Update user profile information"""
    if request.method == 'POST':
        email = request.form.get('email')
        full_name = request.form.get('full_name')
        date_of_birth_str = request.form.get('date_of_birth')
        gender = request.form.get('gender')
        phone_number = request.form.get('phone_number')
        address = request.form.get('address')
        
        # Validate email
        if email and email != current_user.email:
            existing_user = db.session.query(User).filter_by(email=email).first()
            if existing_user:
                flash('Email already in use.', 'danger')
                return redirect(url_for('user_settings'))
            current_user.email = email
        
        # Update other fields
        current_user.full_name = full_name
        
        # Parse date of birth if provided
        try:
            if date_of_birth_str:
                current_user.date_of_birth = datetime.strptime(date_of_birth_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format for date of birth.', 'warning')
        
        current_user.gender = gender
        current_user.phone_number = phone_number
        current_user.address = address
        
        # Handle profile image upload
        if 'profile_image' in request.files:
            profile_image = request.files['profile_image']
            if profile_image and profile_image.filename:
                # Delete previous image if exists
                if current_user.profile_image and os.path.exists(current_user.profile_image[1:]):  # Remove leading '/'
                    try:
                        os.remove(current_user.profile_image[1:])
                    except:
                        pass  # Ignore errors in file deletion
                
                # Save new image
                image_filename = f"user_{current_user.id}_{int(datetime.utcnow().timestamp())}.jpg"
                image_path = os.path.join('static', 'uploads', 'profiles', image_filename)
                os.makedirs(os.path.dirname(image_path), exist_ok=True)
                profile_image.save(image_path)
                current_user.profile_image = '/' + image_path
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('user_settings'))


@app.route('/user/update-password', methods=['POST'])
@login_required
def update_password():
    """Update user password"""
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate inputs
        if not current_password or not new_password or not confirm_password:
            flash('All fields are required.', 'danger')
            return redirect(url_for('user_settings'))
        
        if new_password != confirm_password:
            flash('New password and confirmation do not match.', 'danger')
            return redirect(url_for('user_settings'))
        
        # Check current password
        if not current_user.check_password(current_password):
            flash('Current password is incorrect.', 'danger')
            return redirect(url_for('user_settings'))
        
        # Set new password
        current_user.set_password(new_password)
        db.session.commit()
        
        flash('Password updated successfully!', 'success')
        return redirect(url_for('user_settings'))


@app.route('/user/update-privacy', methods=['POST'])
@login_required
def update_privacy_settings():
    """Update user privacy settings"""
    if request.method == 'POST':
        # Update privacy settings
        current_user.share_health_data = 'share_health_data' in request.form
        current_user.receive_notifications = 'receive_notifications' in request.form
        
        db.session.commit()
        flash('Privacy settings updated successfully!', 'success')
        return redirect(url_for('user_settings'))


@app.route('/user/download-data', methods=['POST'])
@login_required
def download_user_data():
    """Download all user data as JSON"""
    # Collect user data
    user_data = {
        'user_info': {
            'username': current_user.username,
            'email': current_user.email,
            'full_name': current_user.full_name,
            'date_of_birth': str(current_user.date_of_birth) if current_user.date_of_birth else None,
            'gender': current_user.gender,
            'phone_number': current_user.phone_number,
            'address': current_user.address,
            'created_at': str(current_user.created_at)
        },
        'subscription': None,
        'health_scans': [],
        'food_scans': [],
        'bmi_records': [],
        'reminders': [],
        'appointments': [],
        'messages': {
            'sent': [],
            'received': []
        }
    }
    
    # Add subscription data if exists
    if current_user.subscription:
        user_data['subscription'] = {
            'plan_type': current_user.subscription.plan_type,
            'plan_search_limit': current_user.subscription.plan_search_limit,
            'start_date': str(current_user.subscription.start_date),
            'end_date': str(current_user.subscription.end_date) if current_user.subscription.end_date else None,
            'is_active': current_user.subscription.is_active()
        }
    
    # Add health scans
    for scan in current_user.health_scans:
        scan_data = {
            'scan_type': scan.scan_type,
            'scan_date': str(scan.scan_date),
            'wellness_score': scan.wellness_score
        }
        user_data['health_scans'].append(scan_data)
    
    # Add food scans
    for scan in current_user.food_scans:
        scan_data = {
            'food_name': scan.food_name,
            'scan_date': str(scan.scan_date),
            'calories': scan.calories,
            'protein': scan.protein,
            'carbs': scan.carbs,
            'fat': scan.fat
        }
        user_data['food_scans'].append(scan_data)
    
    # Add BMI records
    for record in current_user.bmi_records:
        record_data = {
            'record_date': str(record.record_date),
            'height': record.height,
            'weight': record.weight,
            'bmi_value': record.bmi_value,
            'bmi_category': record.bmi_category
        }
        user_data['bmi_records'].append(record_data)
    
    # Add reminders
    for reminder in current_user.reminders:
        reminder_data = {
            'title': reminder.title,
            'description': reminder.description,
            'reminder_type': reminder.reminder_type,
            'schedule_time': str(reminder.schedule_time),
            'repeat_type': reminder.repeat_type,
            'repeat_days': reminder.repeat_days,
            'active': reminder.active,
            'created_at': str(reminder.created_at)
        }
        user_data['reminders'].append(reminder_data)
    
    # Add appointments
    for appointment in current_user.appointments:
        appointment_data = {
            'doctor_id': appointment.doctor_id,
            'appointment_date': str(appointment.appointment_date),
            'appointment_time': str(appointment.appointment_time),
            'status': appointment.status,
            'type': appointment.type,
            'created_at': str(appointment.created_at)
        }
        user_data['appointments'].append(appointment_data)
    
    # Add messages
    for message in current_user.sent_messages:
        message_data = {
            'recipient_id': message.recipient_id,
            'message': message.message,
            'created_at': str(message.created_at),
            'has_attachment': message.attachment_path is not None
        }
        user_data['messages']['sent'].append(message_data)
    
    for message in current_user.received_messages:
        message_data = {
            'sender_id': message.sender_id,
            'message': message.message,
            'created_at': str(message.created_at),
            'has_attachment': message.attachment_path is not None
        }
        user_data['messages']['received'].append(message_data)
    
    # Create a response with JSON data
    response = make_response(json.dumps(user_data, indent=2))
    response.headers["Content-Disposition"] = f"attachment; filename=user_data_{current_user.username}.json"
    response.headers["Content-Type"] = "application/json"
    
    return response


@app.route('/user/delete-account', methods=['POST'])
@login_required
def delete_account():
    """Delete user account and all associated data"""
    if request.method == 'POST':
        password = request.form.get('password_confirm')
        confirm_deletion = 'confirm_deletion' in request.form
        
        # Validate password and confirmation
        if not password or not confirm_deletion:
            flash('Please provide your password and confirm account deletion.', 'danger')
            return redirect(url_for('user_settings'))
        
        # Verify password
        if not current_user.check_password(password):
            flash('Password is incorrect.', 'danger')
            return redirect(url_for('user_settings'))
        
        # Get user ID for logging purposes
        user_id = current_user.id
        username = current_user.username
        
        # Delete all associated data in the correct order to maintain referential integrity
        try:
            # Delete reminders
            db.session.query(Reminder).filter_by(user_id=user_id).delete()
            
            # Delete BMI records
            db.session.query(BMIRecord).filter_by(user_id=user_id).delete()
            
            # Delete food scans
            db.session.query(FoodScan).filter_by(user_id=user_id).delete()
            
            # Delete health scans
            db.session.query(HealthScan).filter_by(user_id=user_id).delete()
            
            # Delete search history
            db.session.query(SearchHistory).filter_by(user_id=user_id).delete()
            
            # Delete subscription
            db.session.query(Subscription).filter_by(user_id=user_id).delete()
            
            # Delete doctor reviews
            db.session.query(DoctorReview).filter_by(user_id=user_id).delete()
            
            # Delete appointments
            db.session.query(Appointment).filter_by(patient_id=user_id).delete()
            
            # Delete doctor profile if exists
            doctor = db.session.query(Doctor).filter_by(user_id=user_id).first()
            if doctor:
                # Delete doctor appointments
                db.session.query(Appointment).filter_by(doctor_id=doctor.id).delete()
                
                # Delete doctor reviews
                db.session.query(DoctorReview).filter_by(doctor_id=doctor.id).delete()
                
                # Delete doctor
                db.session.delete(doctor)
            
            # Delete messages
            db.session.query(Message).filter(db.or_(
                Message.sender_id == user_id,
                Message.recipient_id == user_id
            )).delete(synchronize_session='fetch')
            
            # Finally, delete the user account
            db.session.delete(current_user)
            db.session.commit()
            
            # Log out the user
            logout_user()
            
            flash('Your account has been successfully deleted.', 'success')
            return redirect(url_for('home'))
        
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error deleting account for user {username} (ID: {user_id}): {str(e)}")
            flash('An error occurred while deleting your account. Please try again later.', 'danger')
            return redirect(url_for('user_settings'))
