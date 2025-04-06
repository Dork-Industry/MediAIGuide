// Health Scanner JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const captureBtn = document.getElementById('captureBtn');
    const resetBtn = document.getElementById('resetBtn');
    const scanStatus = document.getElementById('scanStatus');
    const resultsSection = document.getElementById('resultsSection');
    const saveResultsBtn = document.getElementById('saveResultsBtn');
    const findDoctorBtn = document.getElementById('findDoctorBtn');
    
    // Global variables
    let stream = null;
    let capturedImage = null;
    let scanType = 'face';
    let scanResults = null;
    
    // Initialize the camera
    async function initCamera() {
        try {
            // Get user media with video only
            stream = await navigator.mediaDevices.getUserMedia({
                video: { 
                    width: { ideal: 640 },
                    height: { ideal: 480 },
                    facingMode: 'user'
                },
                audio: false
            });
            
            // Set the video source to the camera stream
            video.srcObject = stream;
            
            // Enable capture button once camera is ready
            video.onloadedmetadata = function() {
                captureBtn.disabled = false;
            };
        } catch (err) {
            console.error('Error accessing camera:', err);
            alert('Could not access your camera. Please ensure you have granted camera permissions and try again.');
        }
    }
    
    // Start the camera when the page loads
    initCamera();
    
    // Capture image from video
    captureBtn.addEventListener('click', function() {
        if (!stream) {
            alert('Camera not available. Please refresh the page and try again.');
            return;
        }
        
        // Get scan type
        scanType = document.querySelector('input[name="scanType"]:checked').value;
        
        // Setup canvas to match video dimensions
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        
        // Draw current video frame to canvas
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        // Get image data
        capturedImage = canvas.toDataURL('image/jpeg');
        
        // Show processing status
        scanStatus.style.display = 'block';
        
        // Stop the camera stream
        stopCamera();
        
        // Enable reset button
        resetBtn.disabled = false;
        captureBtn.disabled = true;
        
        // Process the image
        processHealthScan();
    });
    
    // Reset the scanner
    resetBtn.addEventListener('click', function() {
        // Clear results
        resultsSection.style.display = 'none';
        scanStatus.style.display = 'none';
        capturedImage = null;
        scanResults = null;
        
        // Restart camera
        initCamera();
        
        // Disable reset button
        resetBtn.disabled = true;
        captureBtn.disabled = false;
    });
    
    // Stop the camera stream
    function stopCamera() {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            stream = null;
            video.srcObject = null;
        }
    }
    
    // Process the health scan
    async function processHealthScan() {
        try {
            // Prepare the data
            const formData = new FormData();
            formData.append('scan_type', scanType);
            formData.append('image_data', capturedImage);
            
            // Send the request to the server
            const response = await fetch('/api/health-scan', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`Server responded with ${response.status}: ${response.statusText}`);
            }
            
            // Parse the response
            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            // Save the results
            scanResults = data;
            
            // Display the results
            displayResults(data);
            
        } catch (err) {
            console.error('Error processing health scan:', err);
            alert('Failed to process health scan. Please try again.');
            resetBtn.click(); // Reset the scanner
        } finally {
            // Hide the scanning status
            scanStatus.style.display = 'none';
        }
    }
    
    // Display the results
    function displayResults(data) {
        // Show the results section
        resultsSection.style.display = 'block';
        
        // Display wellness score with animation
        const wellnessScore = Math.round(data.wellness_score || 0);
        animateNumber('wellnessScoreValue', 0, wellnessScore, 1500);
        
        // Set wellness summary
        document.getElementById('wellnessSummary').textContent = data.summary || 'No summary available.';
        
        // Hide all result containers first
        document.getElementById('faceResultsContainer').style.display = 'none';
        document.getElementById('tongueResultsContainer').style.display = 'none';
        document.getElementById('eyeResultsContainer').style.display = 'none';
        document.getElementById('skinResultsContainer').style.display = 'none';
        
        // Show specific scan type results
        if (scanType === 'face') {
            document.getElementById('faceResultsContainer').style.display = 'block';
            document.getElementById('heartRateValue').textContent = data.heart_rate ? `${data.heart_rate} bpm` : '--';
            document.getElementById('bloodPressureValue').textContent = (data.blood_pressure_systolic && data.blood_pressure_diastolic) ? 
                `${Math.round(data.blood_pressure_systolic)}/${Math.round(data.blood_pressure_diastolic)} mmHg` : '--/--';
            document.getElementById('oxygenValue').textContent = data.oxygen_saturation ? `${Math.round(data.oxygen_saturation)}%` : '--%';
            document.getElementById('breathingRateValue').textContent = data.breathing_rate ? `${Math.round(data.breathing_rate)} bpm` : '--';
            document.getElementById('stressLevelValue').textContent = data.sympathetic_stress ? `${getStressLevel(data.sympathetic_stress)}` : '--';
        } else if (scanType === 'tongue') {
            document.getElementById('tongueResultsContainer').style.display = 'block';
            document.getElementById('tongueColorValue').textContent = data.tongue_color || '--';
            document.getElementById('tongueCoatingValue').textContent = data.tongue_coating || '--';
            document.getElementById('tcmDiagnosisValue').textContent = data.tcm_diagnosis || '--';
            document.getElementById('vitaminDeficiencyValue').textContent = data.vitamin_deficiency || '--';
            document.getElementById('infectionIndicatorValue').textContent = data.infection_indicator || '--';
        } else if (scanType === 'eye') {
            document.getElementById('eyeResultsContainer').style.display = 'block';
            document.getElementById('scleraColorValue').textContent = data.sclera_color || '--';
            document.getElementById('conjunctivaColorValue').textContent = data.conjunctiva_color || '--';
            document.getElementById('eyeRednessValue').textContent = data.eye_redness ? `${Math.round(data.eye_redness)}%` : '--%';
            document.getElementById('pupilReactivityValue').textContent = data.pupil_reactivity || '--';
            document.getElementById('eyeConditionValue').textContent = data.eye_condition || '--';
        } else if (scanType === 'skin') {
            document.getElementById('skinResultsContainer').style.display = 'block';
            document.getElementById('skinConditionValue').textContent = data.skin_condition || '--';
            document.getElementById('skinColorValue').textContent = data.skin_color || '--';
            document.getElementById('skinTextureValue').textContent = data.skin_texture || '--';
            document.getElementById('rashDetectionValue').textContent = data.rash_detection ? 'Detected' : 'None detected';
            document.getElementById('rashPatternValue').textContent = data.rash_pattern || '--';
        }
        
        // Set health risks with animated progress bars
        const ascvdRisk = data.ascvd_risk ? Math.round(data.ascvd_risk * 100) : 0;
        const hyperRisk = data.hypertension_risk ? Math.round(data.hypertension_risk * 100) : 0;
        const glucoseRisk = data.glucose_risk ? Math.round(data.glucose_risk * 100) : 0;
        const cholesterolRisk = data.cholesterol_risk ? Math.round(data.cholesterol_risk * 100) : 0;
        
        document.getElementById('ascvdRiskValue').textContent = `${ascvdRisk}%`;
        document.getElementById('hypertensionRiskValue').textContent = `${hyperRisk}%`;
        document.getElementById('glucoseRiskValue').textContent = `${glucoseRisk}%`;
        document.getElementById('cholesterolRiskValue').textContent = `${cholesterolRisk}%`;
        
        // Color code risk levels
        setRiskBarColor('ascvdRiskBar', ascvdRisk);
        setRiskBarColor('hypertensionRiskBar', hyperRisk);
        setRiskBarColor('glucoseRiskBar', glucoseRisk);
        setRiskBarColor('cholesterolRiskBar', cholesterolRisk);
        
        // Animate progress bars
        setTimeout(() => {
            document.getElementById('ascvdRiskBar').style.width = `${ascvdRisk}%`;
            document.getElementById('hypertensionRiskBar').style.width = `${hyperRisk}%`;
            document.getElementById('glucoseRiskBar').style.width = `${glucoseRisk}%`;
            document.getElementById('cholesterolRiskBar').style.width = `${cholesterolRisk}%`;
        }, 200);
        
        // Set biological and heart age
        const chronologicalAge = 30; // Default value, should come from user profile
        document.getElementById('biologicalAgeValue').textContent = chronologicalAge ? `${chronologicalAge} years` : '--';
        document.getElementById('heartAgeValue').textContent = data.heart_age ? `${Math.round(data.heart_age)} years` : '--';
        
        // Set health notes
        document.getElementById('healthNotes').textContent = data.notes || 'No additional notes for this scan.';
        
        // Scroll to results
        resultsSection.scrollIntoView({behavior: 'smooth'});
    }
    
    // Save results button
    saveResultsBtn.addEventListener('click', function() {
        if (!scanResults) {
            alert('No scan results to save.');
            return;
        }
        
        // We already have the results saved server-side from the scan request
        alert('Your scan results have been saved to your profile.');
    });
    
    // Find doctor button
    findDoctorBtn.addEventListener('click', function() {
        // Redirect to doctors listing page
        window.location.href = '/doctors';
    });
    
    // Helper functions
    
    // Animate a number from start to end over duration ms
    function animateNumber(elementId, start, end, duration) {
        const element = document.getElementById(elementId);
        const range = end - start;
        const startTime = performance.now();
        
        function updateValue(currentTime) {
            const elapsedTime = currentTime - startTime;
            
            if (elapsedTime > duration) {
                element.textContent = end;
                return;
            }
            
            const progress = elapsedTime / duration;
            const currentValue = Math.round(start + range * progress);
            element.textContent = currentValue;
            
            requestAnimationFrame(updateValue);
        }
        
        requestAnimationFrame(updateValue);
    }
    
    // Set risk bar color based on risk level
    function setRiskBarColor(barId, riskValue) {
        const bar = document.getElementById(barId);
        
        if (riskValue < 25) {
            bar.style.backgroundColor = '#4CAF50'; // Green
        } else if (riskValue < 50) {
            bar.style.backgroundColor = '#FFC107'; // Yellow
        } else if (riskValue < 75) {
            bar.style.backgroundColor = '#FF9800'; // Orange
        } else {
            bar.style.backgroundColor = '#F44336'; // Red
        }
    }
    
    // Get stress level text based on numeric value
    function getStressLevel(value) {
        if (!value) return 'Unknown';
        
        const stressValue = parseFloat(value);
        if (stressValue < 0.3) return 'Low';
        if (stressValue < 0.6) return 'Moderate';
        return 'High';
    }
    
    // Clean up when leaving the page
    window.addEventListener('beforeunload', function() {
        stopCamera();
    });
    
    // Handle scan type changes
    document.querySelectorAll('input[name="scanType"]').forEach(radio => {
        radio.addEventListener('change', function() {
            scanType = this.value;
        });
    });
});
