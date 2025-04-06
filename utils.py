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
    
    admin = db.session.query(User).filter_by(is_admin=True).first()
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

def analyze_health_data(scan_data):
    """
    Analyze health scan data using OpenAI to generate vital signs and risk assessments
    """
    # Check if OpenAI client is available
    if not openai or not OPENAI_API_KEY:
        return {
            "error": "OpenAI API key is not configured. Please contact the administrator to set up the API key."
        }
    
    try:
        # Simulate the process of analyzing facial scan data
        # In a real implementation, this would process actual facial scan data
        # through computer vision algorithms before sending to OpenAI
        
        response = openai.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": """You are a health analysis AI system that processes facial scan data to determine vital signs and health metrics.
                    Based on the provided scan data, generate realistic vital sign measurements and risk assessments.
                    Your analysis should include:
                    
                    1. Vital signs (heart rate, blood pressure, breathing rate, oxygen saturation)
                    2. Stress indicators (sympathetic stress, parasympathetic activity, PRQ)
                    3. Blood metrics (hemoglobin, hemoglobin A1c)
                    4. Overall wellness score (0-100)
                    5. Risk assessments (ASCVD, hypertension, glucose, cholesterol, tuberculosis)
                    6. Estimated heart age
                    7. Brief analysis and recommendations
                    
                    Provide realistic values for all metrics that would be consistent with each other.
                    Return your response in JSON format.
                    """
                },
                {
                    "role": "user",
                    "content": f"Analyze this facial scan data and provide health metrics: {json.dumps(scan_data)}"
                }
            ],
            response_format={"type": "json_object"},
            max_tokens=1000
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
        
    except Exception as e:
        logger.error(f"Error analyzing health data: {str(e)}")
        return {
            "error": f"Error analyzing health data: {str(e)}"
        }

def analyze_food_image(image_path, food_name):
    """
    Analyze food image to determine nutritional content
    """
    # Check if OpenAI client is available
    if not openai or not OPENAI_API_KEY:
        return {
            "error": "OpenAI API key is not configured. Please contact the administrator to set up the API key."
        }
    
    try:
        # Convert image to base64 for API submission
        import base64
        
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        
        response = openai.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": """You are a nutrition analysis AI. Analyze the provided food image and name to determine:
                    
                    1. Accurate nutritional content (calories, protein, carbs, fat, fiber, sugar, sodium, cholesterol)
                    2. Major ingredients
                    3. Health benefits
                    4. Potential allergens
                    5. Recommendations for healthy consumption
                    
                    If this is an Indian dish, provide detailed analysis specific to Indian cuisine.
                    Return your analysis in JSON format suitable for display in a nutrition app.
                    """
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Analyze this food image. The food is identified as: {food_name}"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            max_tokens=1000
        )
        
        # Parse the response to extract nutritional data
        # For vision models, the response is not JSON formatted by default
        content = response.choices[0].message.content
        
        # Try to extract JSON if present, otherwise use the whole content
        try:
            import re
            json_match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(1))
            else:
                # Try to find any JSON-like structure
                json_match = re.search(r'({.*})', content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group(1))
                else:
                    # If no JSON found, create structured data from the text
                    result = {
                        "food_name": food_name,
                        "analysis": content,
                        "calories": extract_number(content, r'calories:?\s*(\d+)'),
                        "protein": extract_number(content, r'protein:?\s*(\d+\.?\d*)'),
                        "carbs": extract_number(content, r'carbs:?\s*(\d+\.?\d*)'),
                        "fat": extract_number(content, r'fat:?\s*(\d+\.?\d*)'),
                    }
        except:
            # Fallback to structured response
            result = {
                "food_name": food_name,
                "analysis": content
            }
        
        return result
        
    except Exception as e:
        logger.error(f"Error analyzing food image: {str(e)}")
        return {
            "error": f"Error analyzing food image: {str(e)}"
        }

def extract_number(text, pattern):
    """Helper function to extract numbers from text using regex"""
    import re
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        try:
            return float(match.group(1))
        except:
            return None
    return None

def generate_diet_plan(bmi, category, age, gender, is_pregnant, activity_level):
    """
    Generate a personalized diet plan based on BMI and other factors
    """
    # Check if OpenAI client is available
    if not openai or not OPENAI_API_KEY:
        return {
            "error": "OpenAI API key is not configured. Please contact the administrator to set up the API key."
        }
    
    try:
        response = openai.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": """You are a nutrition expert AI that creates personalized diet plans.
                    Create a detailed, structured diet plan based on the provided health information.
                    Your diet plan should include:
                    
                    1. Daily caloric needs and macronutrient breakdown
                    2. Specific meal recommendations for breakfast, lunch, dinner, and snacks
                    3. Food to avoid and alternatives
                    4. Special considerations based on the person's health status
                    5. Weekly meal plan suggestions with Indian food options
                    
                    If the person is pregnant, provide appropriate prenatal nutrition guidelines.
                    If the person has obesity, include weight management strategies.
                    Be precise and provide specific portions and nutrition facts where relevant.
                    
                    Return your plan in JSON format that can be easily parsed and displayed.
                    """
                },
                {
                    "role": "user",
                    "content": f"Create a personalized diet plan for a person with the following characteristics: BMI {bmi} ({category}), Age {age}, Gender: {gender}, Pregnant: {is_pregnant}, Activity Level: {activity_level}"
                }
            ],
            response_format={"type": "json_object"},
            max_tokens=2000
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
        
    except Exception as e:
        logger.error(f"Error generating diet plan: {str(e)}")
        return {
            "error": f"Error generating diet plan: {str(e)}",
            "general_advice": "Please consult with a healthcare professional for personalized dietary advice."
        }
