import os
import json
import logging
from datetime import datetime
from openai import OpenAI
from app import db
from models import MedicineCache, SearchHistory

# Configure OpenAI client 
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
# the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# do not change this unless explicitly requested by the user
MODEL_NAME = "gpt-4o"

# Initialize OpenAI client only if API key is available
openai = None
if OPENAI_API_KEY:
    openai = OpenAI(api_key=OPENAI_API_KEY)
logger = logging.getLogger(__name__)

def get_medicine_info(medicine_name, user=None):
    """
    Get information about a medicine using OpenAI API with caching
    """
    # Check cache first
    cached_data = MedicineCache.get_cached_data(medicine_name)
    if cached_data:
        # Record search if user is provided
        if user:
            record_search(user.id, medicine_name)
        return json.loads(cached_data)
    
    # Check if OpenAI client is available
    if not openai or not OPENAI_API_KEY:
        # Record search if user is provided
        if user:
            record_search(user.id, medicine_name)
            
        return {
            "name": medicine_name,
            "description": "OpenAI API key is not configured. Please contact the administrator to set up the API key.",
            "useCases": ["API key required for detailed information"],
            "pros": ["Contact administrator to enable this feature"],
            "cons": ["API key missing"],
            "dosage": {
                "timing": "Not available",
                "duration": "Not available",
                "breaks": "Not available"
            },
            "warnings": ["This feature requires an OpenAI API key to function properly."],
            "found": False,
            "error": "API key not configured"
        }
    
    # No cache hit, use OpenAI
    try:
        response = openai.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": """You are a pharmaceutical information assistant. 
                    Provide detailed, accurate information about medications. 
                    Your response should be well-structured, medically accurate, and include:
                    1. General description of the medication
                    2. Use cases and conditions it treats
                    3. Pros/benefits of the medication
                    4. Cons/side effects
                    5. Dosage guidelines (when to take, how long, breaks needed)
                    6. Important warnings and contraindications
                    7. Disclaimer about consulting healthcare professionals

                    If the medicine name is unknown or unclear, provide a clear message stating that you don't have information about it and suggest checking the spelling or consulting a healthcare professional.
                    
                    Return your response in JSON format with the following structure:
                    {
                        "name": "Full medication name",
                        "description": "General description",
                        "useCases": ["list", "of", "use cases"],
                        "pros": ["list", "of", "benefits"],
                        "cons": ["list", "of", "side effects"],
                        "dosage": {
                            "timing": "When to take",
                            "duration": "How long to take",
                            "breaks": "Any breaks needed"
                        },
                        "warnings": ["list", "of", "warnings"],
                        "found": true/false (whether the medicine was found)
                    }
                    """
                },
                {
                    "role": "user",
                    "content": f"Provide information about the medication: {medicine_name}"
                }
            ],
            response_format={"type": "json_object"},
            max_tokens=1000
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # Cache the result
        MedicineCache.update_cache(medicine_name, json.dumps(result))
        
        # Record search if user is provided
        if user:
            record_search(user.id, medicine_name)
            
        return result
        
    except Exception as e:
        logger.error(f"Error getting medicine info: {str(e)}")
        return {
            "name": medicine_name,
            "description": "Error retrieving medicine information",
            "useCases": [],
            "pros": [],
            "cons": [],
            "dosage": {
                "timing": "Unknown",
                "duration": "Unknown",
                "breaks": "Unknown"
            },
            "warnings": ["Information could not be retrieved."],
            "found": False,
            "error": str(e)
        }

def record_search(user_id, query):
    """Record a search in the user's search history"""
    search_entry = SearchHistory(user_id=user_id, query=query)
    db.session.add(search_entry)
    db.session.commit()

def init_admin_account():
    """Create an admin account if none exists"""
    from models import User, Subscription
    
    admin = User.query.filter_by(is_admin=True).first()
    if not admin:
        admin = User(
            username="admin",
            email="admin@medicineai.com",
            is_admin=True
        )
        admin.set_password("admin123")  # Default password, should be changed
        db.session.add(admin)
        # We need to commit here to get the admin.id
        db.session.commit()
        
        # Now create the subscription with the valid admin.id
        admin_sub = Subscription(
            user_id=admin.id,
            plan_type="admin",
            plan_search_limit=999999,
            end_date=None  # Never expires
        )
        db.session.add(admin_sub)
        db.session.commit()
