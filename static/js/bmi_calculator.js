document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const bmiForm = document.getElementById('bmiForm');
    const heightInput = document.getElementById('height');
    const weightInput = document.getElementById('weight');
    const genderRadios = document.querySelectorAll('input[name="gender"]');
    const pregnancyOption = document.getElementById('pregnancyOption');
    const bmiResult = document.getElementById('bmiResult');
    const bmiValue = document.getElementById('bmiValue');
    const bmiCategory = document.getElementById('bmiCategory');
    const bmiDescription = document.getElementById('bmiDescription');
    const dietPlanSection = document.getElementById('dietPlanSection');
    const noDietPlan = document.getElementById('noDietPlan');
    
    // Show pregnancy option only for female
    genderRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            if (this.value === 'female') {
                pregnancyOption.style.display = 'block';
            } else {
                pregnancyOption.style.display = 'none';
                document.getElementById('isPregnant').checked = false;
            }
        });
    });
    
    // Handle form submission
    bmiForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const height = parseFloat(heightInput.value);
        const weight = parseFloat(weightInput.value);
        
        if (isNaN(height) || isNaN(weight) || height <= 0 || weight <= 0) {
            alert('Please enter valid height and weight values');
            return;
        }
        
        // Calculate BMI
        const bmi = weight / ((height / 100) * (height / 100));
        
        // Show BMI result
        displayBMIResult(bmi);
        
        // Prepare data for API
        const formData = {
            height: height,
            weight: weight,
            age: document.getElementById('age').value,
            gender: document.querySelector('input[name="gender"]:checked').value,
            is_pregnant: document.getElementById('isPregnant').checked,
            activity_level: document.getElementById('activityLevel').value
        };
        
        // Need diet plan for overweight, obese, or pregnant
        const needsDietPlan = bmi >= 25 || formData.is_pregnant;
        
        if (needsDietPlan) {
            // Call API to get diet plan
            fetch('/api/calculate-bmi', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                // Display diet plan
                displayDietPlan(data);
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error generating diet plan. Please try again.');
            });
        } else {
            // Hide diet plan section
            dietPlanSection.style.display = 'none';
            noDietPlan.style.display = 'block';
        }
    });
    
    // Display BMI result
    function displayBMIResult(bmi) {
        // Show result section
        bmiResult.style.display = 'block';
        
        // Update BMI value
        bmiValue.textContent = bmi.toFixed(1);
        
        // Update BMI category and description
        let category = '';
        let description = '';
        let categoryClass = '';
        
        if (bmi < 18.5) {
            category = 'Underweight';
            description = 'You are underweight. Consider consulting with a healthcare provider about healthy ways to gain weight.';
            categoryClass = 'category-underweight';
        } else if (bmi < 25) {
            category = 'Normal Weight';
            description = 'Your BMI is within the normal range. Maintain a balanced diet and regular exercise routine.';
            categoryClass = 'category-normal';
        } else if (bmi < 30) {
            category = 'Overweight';
            description = 'You are overweight. Consider making dietary changes and increasing physical activity.';
            categoryClass = 'category-overweight';
        } else {
            category = 'Obese';
            description = 'You are in the obese category. It is recommended to consult with a healthcare provider for a personalized weight management plan.';
            categoryClass = 'category-obese';
        }
        
        bmiCategory.textContent = category;
        bmiDescription.textContent = description;
        
        // Reset classes and add the appropriate one
        bmiCategory.className = 'bmi-category mb-3';
        bmiCategory.classList.add(categoryClass);
    }
    
    // Display diet plan
    function displayDietPlan(data) {
        if (data.error) {
            alert(`Error: ${data.error}`);
            return;
        }
        
        // Show diet plan section
        dietPlanSection.style.display = 'block';
        noDietPlan.style.display = 'none';
        
        // Check if we have a diet plan
        if (!data.diet_plan) {
            document.getElementById('mealPlanContainer').innerHTML = '<p class="text-center text-muted">No specific diet plan available for your profile.</p>';
            return;
        }
        
        const plan = data.diet_plan;
        
        // Update daily calories and macros
        document.getElementById('dailyCalories').textContent = plan.daily_calories || "N/A";
        
        // Update macronutrient breakdown
        if (plan.macronutrient_breakdown) {
            const macros = plan.macronutrient_breakdown;
            updateMacros('protein', macros.protein_percent);
            updateMacros('carbs', macros.carbs_percent);
            updateMacros('fats', macros.fat_percent);
        }
        
        // Update meal plan
        if (plan.meals) {
            const mealPlanContainer = document.getElementById('mealPlanContainer');
            let mealPlanHTML = '';
            
            // Handle both array and object formats
            if (Array.isArray(plan.meals)) {
                plan.meals.forEach(meal => {
                    mealPlanHTML += createMealCard(meal);
                });
            } else {
                for (const [mealName, mealDetails] of Object.entries(plan.meals)) {
                    const meal = {
                        name: mealName,
                        ...mealDetails
                    };
                    mealPlanHTML += createMealCard(meal);
                }
            }
            
            mealPlanContainer.innerHTML = mealPlanHTML;
        }
        
        // Update foods to avoid
        if (plan.foods_to_avoid) {
            const foodsToAvoid = document.getElementById('foodsToAvoid');
            if (Array.isArray(plan.foods_to_avoid)) {
                foodsToAvoid.innerHTML = '<ul>';
                plan.foods_to_avoid.forEach(food => {
                    foodsToAvoid.innerHTML += `<li>${food}</li>`;
                });
                foodsToAvoid.innerHTML += '</ul>';
            } else {
                foodsToAvoid.innerHTML = plan.foods_to_avoid;
            }
        }
        
        // Update special considerations
        if (plan.special_considerations) {
            const specialConsiderations = document.getElementById('specialConsiderations');
            if (Array.isArray(plan.special_considerations)) {
                specialConsiderations.innerHTML = '<ul>';
                plan.special_considerations.forEach(consideration => {
                    specialConsiderations.innerHTML += `<li>${consideration}</li>`;
                });
                specialConsiderations.innerHTML += '</ul>';
            } else {
                specialConsiderations.innerHTML = plan.special_considerations;
            }
        }
    }
    
    // Helper function to update macronutrient bars
    function updateMacros(nutrient, percent) {
        const percentElement = document.getElementById(`${nutrient}Percent`);
        const barElement = document.getElementById(`${nutrient}Bar`);
        
        if (percentElement && barElement && percent !== undefined) {
            percentElement.textContent = `${percent}%`;
            barElement.style.width = `${percent}%`;
        }
    }
    
    // Helper function to create meal card
    function createMealCard(meal) {
        // Define icon based on meal name
        let icon = 'coffee';
        if (/breakfast/i.test(meal.name)) icon = 'coffee';
        else if (/lunch/i.test(meal.name)) icon = 'sun';
        else if (/dinner/i.test(meal.name)) icon = 'moon';
        else if (/snack/i.test(meal.name)) icon = 'package';
        
        let foodItems = '';
        if (meal.foods && Array.isArray(meal.foods)) {
            foodItems = '<ul class="mb-0">';
            meal.foods.forEach(food => {
                foodItems += `<li>${food}</li>`;
            });
            foodItems += '</ul>';
        } else if (meal.foods) {
            foodItems = meal.foods;
        } else if (meal.items && Array.isArray(meal.items)) {
            foodItems = '<ul class="mb-0">';
            meal.items.forEach(food => {
                foodItems += `<li>${food}</li>`;
            });
            foodItems += '</ul>';
        } else if (meal.items) {
            foodItems = meal.items;
        } else if (typeof meal.description === 'string') {
            foodItems = meal.description;
        } else {
            foodItems = 'No specific foods listed.';
        }
        
        return `
            <div class="diet-plan-card mb-3">
                <div class="card-body">
                    <div class="meal-title">
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-${icon}"><path d="M18 8h1a4 4 0 0 1 0 8h-1"></path><path d="M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4V8z"></path><line x1="6" y1="1" x2="6" y2="4"></line><line x1="10" y1="1" x2="10" y2="4"></line><line x1="14" y1="1" x2="14" y2="4"></line></svg>
                        ${formatMealName(meal.name)}
                    </div>
                    <div class="meal-items">
                        ${foodItems}
                    </div>
                    
                    ${meal.calories ? `
                    <div class="nutrition-info">
                        <div class="nutrition-item">
                            <div class="nutrition-value">${meal.calories}</div>
                            <div class="nutrition-label">Calories</div>
                        </div>
                        ${meal.protein ? `
                        <div class="nutrition-item">
                            <div class="nutrition-value">${meal.protein}g</div>
                            <div class="nutrition-label">Protein</div>
                        </div>
                        ` : ''}
                        ${meal.carbs ? `
                        <div class="nutrition-item">
                            <div class="nutrition-value">${meal.carbs}g</div>
                            <div class="nutrition-label">Carbs</div>
                        </div>
                        ` : ''}
                        ${meal.fat ? `
                        <div class="nutrition-item">
                            <div class="nutrition-value">${meal.fat}g</div>
                            <div class="nutrition-label">Fat</div>
                        </div>
                        ` : ''}
                    </div>
                    ` : ''}
                </div>
            </div>
        `;
    }
    
    // Helper function to format meal name
    function formatMealName(name) {
        // Capitalize first letter of each word
        return name.replace(/\w\S*/g, function(txt) {
            return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();
        });
    }
});
