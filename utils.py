import os
import json
import logging
from datetime import datetime
from openai import OpenAI
from app import db
from models import MedicineCache, SearchHistory, DrugInteractionCache, DrugInteractionCheck, UserMedication

# Configure OpenAI client 
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
# the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# do not change this unless explicitly requested by the user
MODEL_NAME = "gpt-4o"

# Initialize OpenAI client only if API key is available
openai = None
if OPENAI_API_KEY:
    openai = OpenAI(api_key=OPENAI_API_KEY)
else:
    logger = logging.getLogger(__name__)
    logger.warning("OPENAI_API_KEY is not configured. AI features will be limited.")
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


def check_drug_interaction(drug1, drug2, user=None):
    """
    Check for potential interactions between two drugs using OpenAI API with caching
    
    Args:
        drug1 (str): First medication name
        drug2 (str): Second medication name
        user (User, optional): User requesting the interaction check
        
    Returns:
        dict: Dictionary containing interaction details
    """
    # Check cache first
    cached_data = DrugInteractionCache.get_cached_interaction(drug1, drug2)
    if cached_data:
        return json.loads(cached_data)
    
    # Check if OpenAI client is available
    if not openai or not OPENAI_API_KEY:
        logger.warning(f"OPENAI_API_KEY is not configured. Drug interaction check is limited.")
        
        return {
            "drug1": drug1,
            "drug2": drug2,
            "has_interaction": None,
            "severity": None,
            "mechanism": None,
            "effects": None,
            "recommendations": None,
            "error": "OpenAI API key is not configured. Please contact the administrator to enable drug interaction features."
        }
    
    # No cache hit, use OpenAI
    try:
        response = openai.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": """You are a pharmaceutical expert specializing in drug interactions.
                    Analyze potential interactions between the two drugs provided.
                    
                    Your response should be comprehensive and include:
                    1. Whether the drugs have a known interaction
                    2. The severity of the interaction (none, mild, moderate, severe)
                    3. The mechanism of interaction
                    4. Potential effects of the interaction
                    5. Recommendations for patients
                    6. A disclaimer about consulting healthcare professionals
                    
                    If you don't have sufficient information about one or both drugs, clearly state this.
                    
                    Return your response in JSON format with the following structure:
                    {
                        "drug1": "First drug name",
                        "drug2": "Second drug name",
                        "has_interaction": true/false/null (null if unknown),
                        "severity": "none/mild/moderate/severe/unknown",
                        "mechanism": "Description of interaction mechanism",
                        "effects": ["list", "of", "potential", "effects"],
                        "recommendations": ["list", "of", "recommendations"],
                        "disclaimer": "Standard medical disclaimer"
                    }
                    """
                },
                {
                    "role": "user",
                    "content": f"Check for interactions between {drug1} and {drug2}"
                }
            ],
            response_format={"type": "json_object"},
            max_tokens=1000
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # Determine severity for database storage
        severity = result.get("severity", "unknown").lower()
        if severity not in ["none", "mild", "moderate", "severe"]:
            severity = "unknown"
            
        # Create a description for database storage
        description = None
        if result.get("effects") and isinstance(result["effects"], list):
            description = "; ".join(result["effects"])
        
        # Cache the result
        DrugInteractionCache.update_cache(
            drug1, 
            drug2, 
            json.dumps(result),
            severity,
            description
        )
        
        # Record interaction check if user is provided
        if user:
            check_record = DrugInteractionCheck(
                user_id=user.id,
                medications=json.dumps([drug1, drug2]),
                has_interactions=result.get("has_interaction", False),
                highest_severity=severity
            )
            db.session.add(check_record)
            db.session.commit()
            
        return result
        
    except Exception as e:
        logger.error(f"Error checking drug interaction: {str(e)}")
        return {
            "drug1": drug1,
            "drug2": drug2,
            "has_interaction": None,
            "severity": "unknown",
            "mechanism": "Error retrieving interaction information",
            "effects": ["Information could not be retrieved"],
            "recommendations": ["Consult your healthcare provider for accurate information"],
            "disclaimer": "Always consult healthcare professionals for medical advice",
            "error": str(e)
        }


def check_multiple_drug_interactions(medications, user=None):
    """
    Check for interactions between multiple medications
    
    Args:
        medications (list): List of medication names
        user (User, optional): User requesting the interaction check
        
    Returns:
        dict: Dictionary containing all interaction details
    """
    if not medications or len(medications) < 2:
        return {
            "message": "At least two medications are required to check for interactions",
            "interactions": [],
            "highest_severity": "none",
            "has_interactions": False
        }
    
    interactions = []
    highest_severity_rank = 0  # 0=none, 1=mild, 2=moderate, 3=severe
    severity_map = {"none": 0, "mild": 1, "moderate": 2, "severe": 3}
    has_interactions = False
    
    # Check interactions between each pair of medications
    for i in range(len(medications)):
        for j in range(i+1, len(medications)):
            drug1 = medications[i]
            drug2 = medications[j]
            
            interaction = check_drug_interaction(drug1, drug2)
            interactions.append(interaction)
            
            # Update highest severity and interaction flag
            # Check if interaction is None before accessing its attributes
            if interaction is None:
                continue
                
            severity = interaction.get("severity", "unknown").lower()
            severity_rank = severity_map.get(severity, 0)
            
            if interaction.get("has_interaction", False):
                has_interactions = True
                highest_severity_rank = max(highest_severity_rank, severity_rank)
    
    # Map severity rank back to string
    highest_severity = "none"
    for sev, rank in severity_map.items():
        if rank == highest_severity_rank:
            highest_severity = sev
            break
    
    # Record interaction check if user is provided
    if user:
        check_record = DrugInteractionCheck(
            user_id=user.id,
            medications=json.dumps(medications),
            has_interactions=has_interactions,
            highest_severity=highest_severity
        )
        db.session.add(check_record)
        db.session.commit()
    
    return {
        "medications": medications,
        "interactions": interactions,
        "highest_severity": highest_severity,
        "has_interactions": has_interactions
    }


def analyze_health_data(image_path, scan_type='face'):
    """
    Analyze health scan data from image using ML and OpenAI to generate health metrics
    
    Args:
        image_path (str): Path to the image file to analyze
        scan_type (str): Type of scan - 'face', 'tongue', 'eye', or 'skin'
    
    Returns:
        dict: Dictionary containing health metrics based on scan type
    """
    # First, try to use our ML-based heart rate detection for improved accuracy
    try:
        import cv2
        import numpy as np
        from ml_heart_rate import get_vital_signs_from_image
        
        # Read the image for ML processing
        image = cv2.imread(image_path)
        if image is not None:
            # Use ML to get vital signs
            ml_results = get_vital_signs_from_image(image)
            logger.info(f"ML processing results: {ml_results}")
            
            # If we got valid results, use them
            if ml_results and ml_results["heart_rate"]:
                # If OpenAI is not available, return ML results directly
                if not openai or not OPENAI_API_KEY:
                    # Create a complete result with the ML data
                    result = {
                        "scan_type": scan_type,
                        "heart_rate": ml_results["heart_rate"],
                        "blood_pressure_systolic": ml_results["blood_pressure_systolic"],
                        "blood_pressure_diastolic": ml_results["blood_pressure_diastolic"],
                        "oxygen_saturation": ml_results["oxygen_saturation"],
                        "sympathetic_stress": ml_results["stress_level"],
                        "wellness_score": 75, # Default estimate based on vital signs
                        "recommendations": [
                            "Maintain a balanced diet with plenty of fruits and vegetables",
                            "Stay physically active with regular exercise",
                            "Ensure you're getting adequate sleep (7-8 hours)",
                            "Stay hydrated by drinking plenty of water",
                            "Practice stress management techniques like meditation"
                        ],
                        "summary": "Your vital signs have been analyzed using advanced computer vision. This provides a reasonable estimate of your health metrics."
                    }
                    
                    # Add risk estimates based on the ML results
                    if ml_results["blood_pressure_systolic"] > 130:
                        result["hypertension_risk"] = min(60 + (ml_results["blood_pressure_systolic"] - 130) * 2, 90)
                    else:
                        result["hypertension_risk"] = max(20, 40 - (130 - ml_results["blood_pressure_systolic"]) * 1.5)
                    
                    # Heart age estimate based on heart rate and blood pressure
                    avg_hr_resting = 70  # Average resting heart rate
                    hr_factor = (ml_results["heart_rate"] - avg_hr_resting) * 0.5
                    bp_factor = (ml_results["blood_pressure_systolic"] - 120) * 0.2
                    estimated_diff = hr_factor + bp_factor
                    
                    # Get user age if available, or use a default of 35
                    if hasattr(current_user, 'date_of_birth') and current_user.date_of_birth:
                        from datetime import datetime
                        user_age = (datetime.utcnow().date() - current_user.date_of_birth).days // 365
                    else:
                        user_age = 35
                        
                    result["heart_age"] = max(18, user_age + estimated_diff)
                    
                    return result
    except Exception as e:
        logger.error(f"Error in ML processing: {str(e)}")
    
    # Fall back to OpenAI if ML processing failed or is incomplete
    # Check if OpenAI client is available
    if not openai or not OPENAI_API_KEY:
        logger.warning(f"OPENAI_API_KEY is not available. Health scan feature is limited.")
        
        # Return a clear message that API key is needed
        return {
            "api_key_missing": True,
            "scan_type": scan_type,
            "message": "OpenAI API key is not configured. Please contact the administrator to enable health scanning features.",
            "error": "API key not configured"
        }

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
