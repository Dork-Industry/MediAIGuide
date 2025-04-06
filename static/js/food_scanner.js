document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const videoElement = document.getElementById('videoElement');
    const overlayCanvas = document.getElementById('overlay');
    const loadingElement = document.getElementById('loading');
    const startCameraBtn = document.getElementById('startCamera');
    const captureImageBtn = document.getElementById('captureImage');
    const uploadForm = document.getElementById('uploadForm');
    const foodNameInput = document.getElementById('foodName');
    const foodImageInput = document.getElementById('foodImage');
    const resultsSection = document.getElementById('results');
    const noResultsSection = document.getElementById('noResults');
    const resultImage = document.getElementById('resultImage');
    const analyzedFoodName = document.getElementById('analyzedFoodName');

    let stream = null;
    let capturedImage = null;
    
    // Start camera
    startCameraBtn.addEventListener('click', async () => {
        try {
            stream = await navigator.mediaDevices.getUserMedia({ 
                video: { facingMode: 'environment' },
                audio: false
            });
            videoElement.srcObject = stream;
            startCameraBtn.disabled = true;
            captureImageBtn.disabled = false;
            
            // Setup canvas for capturing
            setupCanvas();
        } catch (error) {
            console.error('Error accessing camera:', error);
            alert('Could not access camera. Please check permissions and try again.');
        }
    });
    
    // Setup canvas for capturing
    function setupCanvas() {
        const ctx = overlayCanvas.getContext('2d');
        overlayCanvas.width = videoElement.videoWidth;
        overlayCanvas.height = videoElement.videoHeight;
        overlayCanvas.style.display = 'block';
        
        // Draw focus area
        function drawFocusArea() {
            if (!stream) return;
            
            ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
            
            // Get current dimensions
            overlayCanvas.width = videoElement.videoWidth || videoElement.clientWidth;
            overlayCanvas.height = videoElement.videoHeight || videoElement.clientHeight;
            
            // Draw focus box
            const centerX = overlayCanvas.width / 2;
            const centerY = overlayCanvas.height / 2;
            const boxWidth = overlayCanvas.width * 0.7;
            const boxHeight = overlayCanvas.height * 0.7;
            
            ctx.strokeStyle = '#20c997';
            ctx.lineWidth = 2;
            ctx.setLineDash([5, 5]);
            ctx.strokeRect(
                centerX - boxWidth/2,
                centerY - boxHeight/2,
                boxWidth,
                boxHeight
            );
            
            requestAnimationFrame(drawFocusArea);
        }
        
        drawFocusArea();
    }
    
    // Capture image for analysis
    captureImageBtn.addEventListener('click', () => {
        if (!stream) return;
        
        const canvas = document.createElement('canvas');
        canvas.width = videoElement.videoWidth;
        canvas.height = videoElement.videoHeight;
        const ctx = canvas.getContext('2d');
        
        // Draw video frame to canvas
        ctx.drawImage(videoElement, 0, 0, canvas.width, canvas.height);
        
        // Convert to blob
        canvas.toBlob(blob => {
            capturedImage = blob;
            
            // Show the captured image
            const capturedImageUrl = URL.createObjectURL(blob);
            resultImage.src = capturedImageUrl;
            
            // Prompt for food name if not already entered
            if (!foodNameInput.value) {
                const foodName = prompt('What food is in the image?', '');
                if (foodName) {
                    foodNameInput.value = foodName;
                } else {
                    return; // Cancel if no name provided
                }
            }
            
            // Show loading state
            loadingElement.style.display = 'flex';
            
            // Process the image
            submitFoodImage(capturedImage, foodNameInput.value);
        }, 'image/jpeg', 0.9);
    });
    
    // Handle upload form submission
    uploadForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        if (!foodImageInput.files.length) {
            alert('Please select an image to upload');
            return;
        }
        
        if (!foodNameInput.value) {
            alert('Please enter the food name');
            return;
        }
        
        // Show loading state
        loadingElement.style.display = 'flex';
        
        // Display the selected image
        const fileUrl = URL.createObjectURL(foodImageInput.files[0]);
        resultImage.src = fileUrl;
        
        // Create form data
        const formData = new FormData();
        formData.append('food_image', foodImageInput.files[0]);
        formData.append('food_name', foodNameInput.value);
        
        // Submit the form
        fetch('/api/food-scan', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            displayResults(data, foodNameInput.value);
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error analyzing food image. Please try again.');
        })
        .finally(() => {
            loadingElement.style.display = 'none';
        });
    });
    
    // Submit captured image
    function submitFoodImage(imageBlob, foodName) {
        const formData = new FormData();
        formData.append('food_image', imageBlob, 'captured_food.jpg');
        formData.append('food_name', foodName);
        
        fetch('/api/food-scan', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            displayResults(data, foodName);
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error analyzing food image. Please try again.');
        })
        .finally(() => {
            loadingElement.style.display = 'none';
        });
    }
    
    // Display results
    function displayResults(data, foodName) {
        // Check for explicit error messages first
        if (data.error) {
            alert(`Error: ${data.error}`);
            noResultsSection.style.display = "block";
            resultsSection.style.display = "none";
            document.getElementById("errorMessage").textContent = data.error;
            return;
        }
        resultsSection.style.display = 'block';
        noResultsSection.style.display = 'none';
        
        // Set food name
        analyzedFoodName.textContent = data.food_name || foodName;
        
        // Update nutrition values
        updateNutritionValue('caloriesValue', data.calories, '', 0);
        updateNutritionValue('proteinValue', data.protein, 'g');
        updateNutritionValue('carbsValue', data.carbs, 'g');
        updateNutritionValue('fatValue', data.fat, 'g');
        updateNutritionValue('fiberValue', data.fiber, 'g');
        updateNutritionValue('sugarValue', data.sugar, 'g');
        updateNutritionValue('sodiumValue', data.sodium, 'mg');
        updateNutritionValue('cholesterolValue', data.cholesterol, 'mg');
        
        // Ingredients list
        const ingredientsList = document.getElementById('ingredientsList');
        if (data.ingredients && Array.isArray(data.ingredients)) {
            ingredientsList.innerHTML = `<ul class="mb-0">`;
            data.ingredients.forEach(ingredient => {
                ingredientsList.innerHTML += `<li>${ingredient}</li>`;
            });
            ingredientsList.innerHTML += `</ul>`;
        } else if (data.ingredients) {
            ingredientsList.innerHTML = data.ingredients;
        } else {
            ingredientsList.innerHTML = '<p class="text-muted">No detailed ingredients information available.</p>';
        }
        
        // Benefits
        const benefitsList = document.getElementById('benefitsList');
        if (data.benefits && Array.isArray(data.benefits)) {
            benefitsList.innerHTML = `<ul class="mb-0">`;
            data.benefits.forEach(benefit => {
                benefitsList.innerHTML += `<li>${benefit}</li>`;
            });
            benefitsList.innerHTML += `</ul>`;
        } else if (data.benefits) {
            benefitsList.innerHTML = data.benefits;
        } else if (data.health_benefits) {
            benefitsList.innerHTML = data.health_benefits;
        } else {
            benefitsList.innerHTML = '<p class="text-muted">No specific health benefits information available.</p>';
        }
        
        // Concerns
        const concernsList = document.getElementById('concernsList');
        if (data.concerns && Array.isArray(data.concerns)) {
            concernsList.innerHTML = `<ul class="mb-0">`;
            data.concerns.forEach(concern => {
                concernsList.innerHTML += `<li>${concern}</li>`;
            });
            concernsList.innerHTML += `</ul>`;
        } else if (data.concerns) {
            concernsList.innerHTML = data.concerns;
        } else if (data.allergens) {
            concernsList.innerHTML = `<p>Potential allergens: ${data.allergens}</p>`;
        } else {
            concernsList.innerHTML = '<p class="text-muted">No specific concerns information available.</p>';
        }
        
        // Recommendations
        const recommendationsList = document.getElementById('recommendationsList');
        if (data.recommendations && Array.isArray(data.recommendations)) {
            recommendationsList.innerHTML = `<ul class="mb-0">`;
            data.recommendations.forEach(rec => {
                recommendationsList.innerHTML += `<li>${rec}</li>`;
            });
            recommendationsList.innerHTML += `</ul>`;
        } else if (data.recommendations) {
            recommendationsList.innerHTML = data.recommendations;
        } else if (data.dietary_recommendations) {
            recommendationsList.innerHTML = data.dietary_recommendations;
        } else {
            recommendationsList.innerHTML = '<p class="text-muted">No specific dietary recommendations available.</p>';
        }
    }
    
    // Helper function to update nutrition values
    function updateNutritionValue(elementId, value, unit, decimals = 1) {
        const element = document.getElementById(elementId);
        if (!element) return;
        
        if (value !== undefined && value !== null) {
            // Format the number with appropriate decimal places
            const formattedValue = Number.isInteger(value) ? 
                value : parseFloat(value).toFixed(decimals);
            element.textContent = `${formattedValue}${unit}`;
        } else {
            element.textContent = `--${unit}`;
        }
    }
});
