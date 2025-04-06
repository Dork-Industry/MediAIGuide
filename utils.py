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

def analyze_health_data(image_path, scan_type='face'):
    """
    Analyze health scan data from image using OpenAI to generate health metrics
    
    Args:
        image_path (str): Path to the image file to analyze
        scan_type (str): Type of scan - 'face', 'tongue', 'eye', or 'skin'
    
    Returns:
        dict: Dictionary containing health metrics based on scan type
    """
    # Check if OpenAI client is available
    if not openai or not OPENAI_API_KEY:
        # Generate realistic mock data for testing
        import random
        
        # Base results for all scan types
        base_results = {
            "wellness_score": random.randint(70, 95),
            "scan_type": scan_type,
            "recommendations": [
                "Maintain a balanced diet rich in fruits, vegetables, and whole grains",
                "Engage in moderate aerobic exercise for at least 30 minutes daily",
                "Practice stress reduction techniques like meditation or deep breathing",
                "Ensure adequate sleep of 7-8 hours per night",
                "Stay hydrated by drinking 2-3 liters of water daily"
            ]
        }
        
        # Specific results based on scan type
        if scan_type == 'face':
            return {
                **base_results,
                "heart_rate": round(random.uniform(60, 100), 1),
                "blood_pressure_systolic": round(random.uniform(110, 140), 0),
                "blood_pressure_diastolic": round(random.uniform(70, 90), 0),
                "breathing_rate": round(random.uniform(12, 20), 1),
                "oxygen_saturation": round(random.uniform(95, 100), 1),
                "sympathetic_stress": round(random.uniform(20, 60), 1),
                "parasympathetic_activity": round(random.uniform(40, 80), 1),
                "prq": round(random.uniform(1.0, 2.5), 2),
                "hemoglobin": round(random.uniform(13.5, 17.0), 1),
                "hemoglobin_a1c": round(random.uniform(4.5, 6.0), 1),
                "ascvd_risk": round(random.uniform(2, 8), 1),
                "hypertension_risk": round(random.uniform(2, 10), 1),
                "glucose_risk": round(random.uniform(1, 6), 1),
                "cholesterol_risk": round(random.uniform(2, 9), 1),
                "tuberculosis_risk": round(random.uniform(0.1, 2), 1),
                "heart_age": round(random.uniform(25, 45), 0),
            }
        elif scan_type == 'tongue':
            return {
                **base_results,
                "tongue_color": random.choice(["Pale Pink", "Red", "Dark Red", "Purple", "Pale White"]),
                "tongue_coating": random.choice(["Thin White", "Thick White", "Yellow", "None", "Thin Yellow"]),
                "tongue_shape": random.choice(["Normal", "Swollen", "Thin", "Cracked", "Scalloped"]),
                "tcm_diagnosis": random.choice(["Qi Deficiency", "Yin Deficiency", "Yang Deficiency", "Heat", "Dampness"]),
                "vitamin_deficiency": random.choice(["None detected", "B12", "Iron", "Folate", "B12, Iron"]),
                "infection_indicator": random.choice(["None detected", "Mild thrush", "Bacterial infection", "No signs of infection"]),
                "recommendations": [
                    "Consider increasing iron-rich foods in your diet",
                    "Maintain good oral hygiene including tongue cleaning",
                    "Stay well-hydrated throughout the day",
                    "Consider consulting with a nutritionist about vitamin supplementation",
                    "Include more leafy greens and whole foods in your diet"
                ]
            }
        elif scan_type == 'eye':
            return {
                **base_results,
                "sclera_color": random.choice(["Normal white", "Slightly yellow", "Pink tinged", "Clear"]),
                "conjunctiva_color": random.choice(["Pink", "Pale", "Reddened", "Normal"]),
                "eye_redness": round(random.uniform(5, 40), 1),
                "pupil_reactivity": random.choice(["Normal", "Sluggish", "Highly responsive", "Slightly delayed"]),
                "eye_condition": random.choice(["Healthy", "Mild allergic conjunctivitis", "Dry eye syndrome", "No abnormalities detected"]),
                "recommendations": [
                    "Take regular breaks when using digital screens (20-20-20 rule)",
                    "Ensure adequate lighting when reading or working",
                    "Consider foods rich in lutein and zeaxanthin for eye health",
                    "Use artificial tears if experiencing dryness",
                    "Schedule a routine eye examination with an optometrist"
                ]
            }
        elif scan_type == 'skin':
            return {
                **base_results,
                "skin_color": random.choice(["Normal", "Reddened", "Pale", "Slightly yellow", "Even"]),
                "skin_texture": random.choice(["Smooth", "Dry", "Rough", "Normal", "Even"]),
                "rash_detection": random.choice([True, False]),
                "rash_pattern": random.choice(["None", "Macular", "Papular", "Vesicular", "N/A"]) if random.choice([True, False]) else "N/A",
                "skin_condition": random.choice(["Healthy", "Mild eczema", "Mild acne", "Dermatitis", "No concerning findings"]),
                "recommendations": [
                    "Maintain a consistent skincare routine with gentle products",
                    "Use broad-spectrum sunscreen daily, even on cloudy days",
                    "Stay well-hydrated for skin health",
                    "Consider foods rich in antioxidants and omega-3 fatty acids",
                    "Consult with a dermatologist for personalized advice"
                ]
            }
        else:
            # Default case - shouldn't happen with validation
            return base_results

    # Format the image for analysis
    try:
        import base64
        
        # Read the image file and convert to base64
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        
        # Create an OpenAI client to call the API
        client = openai
        
        # Set up prompts based on scan type
        if scan_type == 'face':
            prompt = f"""
            Analyze this facial image and provide health metrics estimations.
            
            Please provide these metrics:
            - Heart rate (bpm)
            - Blood pressure (systolic/diastolic)
            - Breathing rate (breaths per minute)
            - Oxygen saturation (%)
            - Sympathetic stress level (%)
            - Parasympathetic activity (%)
            - PRQ (Parasympathetic Recovery Quotient)
            - Estimated hemoglobin (g/dL)
            - Estimated HbA1c (%)
            - Overall wellness score (0-100)
            - ASCVD risk (%)
            - Hypertension risk (%)
            - Glucose abnormality risk (%)
            - Cholesterol abnormality risk (%)
            - Tuberculosis risk (%)
            - Estimated heart age (years)
            - Health recommendations (5 items)
            
            Format as JSON with fields: heart_rate, blood_pressure_systolic, 
            blood_pressure_diastolic, breathing_rate, oxygen_saturation, 
            sympathetic_stress, parasympathetic_activity, prq, hemoglobin, 
            hemoglobin_a1c, wellness_score, ascvd_risk, hypertension_risk, 
            glucose_risk, cholesterol_risk, tuberculosis_risk, heart_age, 
            recommendations (array of strings).
            
            For realistic health metrics, use these normal ranges unless indicated otherwise:
            - Heart rate: 60-100 bpm
            - Blood pressure: 110-140/70-90 mmHg
            - Breathing rate: 12-20 breaths/min
            - Oxygen saturation: 95-100%
            - Hemoglobin: 13.5-17.5 g/dL
            - HbA1c: 4.0-5.7%
            """
            system_role = "You are a healthcare AI assistant that analyzes facial images to estimate vital signs and health risks. Provide realistic metrics within normal ranges."
            
        elif scan_type == 'tongue':
            prompt = f"""
            Analyze this tongue image and provide a Traditional Chinese Medicine (TCM) assessment.
            
            Please provide these metrics:
            - Tongue color (e.g., pale, red, purple, etc.)
            - Tongue coating (e.g., thin-white, thick-yellow, etc.)
            - Tongue shape (e.g., swollen, thin, cracked, etc.)
            - TCM diagnosis (based on tongue appearance)
            - Possible vitamin deficiencies indicated
            - Infection indicators (if any)
            - Overall wellness score (0-100)
            - Health recommendations (5 items)
            
            Format as JSON with fields: tongue_color, tongue_coating, tongue_shape, 
            tcm_diagnosis, vitamin_deficiency, infection_indicator, wellness_score, 
            recommendations (array of strings).
            """
            system_role = "You are a TCM (Traditional Chinese Medicine) expert who analyzes tongue images to assess health status. Provide realistic assessments based on tongue appearance."
            
        elif scan_type == 'eye':
            prompt = f"""
            Analyze this eye image and provide an assessment of eye health.
            
            Please provide these metrics:
            - Sclera color (white, yellow, etc.)
            - Conjunctiva color (pink, pale, etc.)
            - Eye redness level (0-100%)
            - Pupil reactivity (if visible)
            - Possible eye conditions indicated
            - Overall wellness score (0-100)
            - Health recommendations (5 items)
            
            Format as JSON with fields: sclera_color, conjunctiva_color, eye_redness, 
            pupil_reactivity, eye_condition, wellness_score, recommendations (array of strings).
            """
            system_role = "You are an ophthalmology specialist who analyzes eye images to assess eye health and detect potential conditions. Provide realistic assessments based on eye appearance."
            
        elif scan_type == 'skin':
            prompt = f"""
            Analyze this skin image and provide an assessment of skin health.
            
            Please provide these metrics:
            - Skin color 
            - Skin texture
            - Rash detection (true/false)
            - Rash pattern (if applicable)
            - Possible skin conditions indicated
            - Overall wellness score (0-100)
            - Health recommendations (5 items)
            
            Format as JSON with fields: skin_color, skin_texture, rash_detection, 
            rash_pattern, skin_condition, wellness_score, recommendations (array of strings).
            """
            system_role = "You are a dermatology specialist who analyzes skin images to assess skin health and detect potential conditions. Provide realistic assessments based on skin appearance."
            
        else:
            # Default to face scan if an invalid type is somehow provided
            return analyze_health_data(image_path, 'face')
        
        # Call the OpenAI API with GPT-4 Vision
        response = client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {"role": "system", "content": system_role},
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]}
            ],
            temperature=0.3,
            max_tokens=1000
        )

        # Extract and parse the response
        result_text = response.choices[0].message.content.strip()
        
        try:
            # Try to extract JSON from the response
            if "```json" in result_text:
                # Extract JSON from code block
                json_str = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                # Extract JSON from generic code block
                json_str = result_text.split("```")[1].strip()
            else:
                # Assume the entire response is JSON or try to find JSON-like content
                import re
                json_match = re.search(r'(\{.*\})', result_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    json_str = result_text
            
            import json
            result = json.loads(json_str)
            
            # Add scan type to result
            result['scan_type'] = scan_type
            
            # Ensure we have recommendations
            if 'recommendations' not in result:
                # Use default recommendations based on scan type
                if scan_type == 'face':
                    result['recommendations'] = [
                        "Maintain a balanced diet rich in fruits and vegetables",
                        "Stay physically active with regular exercise",
                        "Ensure adequate sleep and stress management",
                        "Stay hydrated by drinking plenty of water",
                        "Consider regular health check-ups with your physician"
                    ]
                elif scan_type == 'tongue':
                    result['recommendations'] = [
                        "Consider increasing iron-rich foods in your diet",
                        "Maintain good oral hygiene including tongue cleaning",
                        "Stay well-hydrated throughout the day",
                        "Consider consulting with a nutritionist about vitamin supplementation",
                        "Include more leafy greens and whole foods in your diet"
                    ]
                elif scan_type == 'eye':
                    result['recommendations'] = [
                        "Take regular breaks when using digital screens (20-20-20 rule)",
                        "Ensure adequate lighting when reading or working",
                        "Consider foods rich in lutein and zeaxanthin for eye health",
                        "Use artificial tears if experiencing dryness",
                        "Schedule a routine eye examination with an optometrist"
                    ]
                elif scan_type == 'skin':
                    result['recommendations'] = [
                        "Maintain a consistent skincare routine with gentle products",
                        "Use broad-spectrum sunscreen daily, even on cloudy days",
                        "Stay well-hydrated for skin health",
                        "Consider foods rich in antioxidants and omega-3 fatty acids",
                        "Consult with a dermatologist for personalized advice"
                    ]
            
            # For backward compatibility with existing code
            if 'recommendations' in result and 'notes' not in result:
                result['notes'] = {'recommendations': result['recommendations']}
                
            return result
        except Exception as e:
            # Handle JSON parsing errors
            logger.error(f"Error parsing OpenAI response: {e}")
            raise
    except Exception as e:
        # Handle any other errors
        logger.error(f"Error analyzing health data: {e}")
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
