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
            // Show loading state
            const scanArea = document.querySelector('.scan-area');
            if (scanArea) {
                scanArea.innerHTML = '<div class="camera-loading text-center p-4"><div class="spinner-border text-primary mb-3" role="status"><span class="visually-hidden">Loading...</span></div><h5>Starting camera...</h5><p>Please grant camera permissions when prompted.</p></div>';
            }
            
            // Make sure the video element exists and is visible
            if (!video) {
                video = document.createElement('video');
                video.id = 'video';
                video.autoplay = true;
                video.playsInline = true; // Ensures better mobile compatibility
                video.style.display = 'block';
                video.style.width = '100%';
                video.style.maxWidth = '640px';
                video.style.margin = '0 auto';
                
                if (scanArea) {
                    scanArea.appendChild(video);
                }
            }
            
            // Check if MediaDevices API is supported
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                throw new Error('Your browser does not support camera access. Please try another browser like Chrome or Firefox.');
            }
            
            // Try to get available devices, but continue anyway if it fails
            try {
                const devices = await navigator.mediaDevices.enumerateDevices();
                const videoDevices = devices.filter(device => device.kind === 'videoinput');
                console.log('Available video devices:', videoDevices.length);
                
                if (videoDevices.length === 0) {
                    console.warn('No video devices detected, but will still attempt to access camera');
                }
            } catch (devicesError) {
                console.warn('Could not enumerate devices, continuing anyway:', devicesError);
            }
            
            // Set up progressive fallback for getUserMedia
            const constraints = [
                // Try first with ideal settings
                {
                    video: { 
                        width: { ideal: 640 },
                        height: { ideal: 480 },
                        facingMode: 'user'
                    },
                    audio: false
                },
                // Then with minimal settings
                {
                    video: true,
                    audio: false
                },
                // Finally try with explicit low resolution
                {
                    video: { 
                        width: { exact: 320 },
                        height: { exact: 240 }
                    },
                    audio: false
                }
            ];
            
            // Try each constraint set in sequence
            for (let i = 0; i < constraints.length; i++) {
                try {
                    console.log(`Attempting camera access with constraints set ${i+1}:`, constraints[i]);
                    stream = await navigator.mediaDevices.getUserMedia(constraints[i]);
                    console.log('Camera access successful with constraints set', i+1);
                    break; // Exit the loop if successful
                } catch (err) {
                    console.warn(`Failed with constraints set ${i+1}:`, err);
                    // If this is the last attempt and it failed, re-throw the error
                    if (i === constraints.length - 1) {
                        throw err;
                    }
                }
            }
            
            // If we get here, we have a stream
            console.log('Camera stream obtained successfully');
            
            // Reset the scan area to show the video element
            if (scanArea) {
                scanArea.innerHTML = '';
                scanArea.appendChild(video);
            }
            
            // Set the video source to the camera stream
            video.srcObject = stream;
            video.style.display = 'block';
            
            // Play the video
            try {
                await video.play();
                console.log('Video playback started');
            } catch (playErr) {
                console.error('Error playing video:', playErr);
                // Continue anyway, as some browsers auto-play the video
            }
            
            // Enable capture button once camera is ready
            video.onloadedmetadata = function() {
                captureBtn.disabled = false;
                console.log('Video metadata loaded, capture enabled');
            };
            
            console.log('Camera initialized successfully');
        } catch (err) {
            console.error('Error accessing camera:', err);
            
            // Show error on interface with more detailed troubleshooting steps
            const scanArea = document.querySelector('.scan-area');
            if (scanArea) {
                scanArea.innerHTML = `
                    <div class="camera-error text-center p-4">
                        <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-camera-off mb-3">
                            <line x1="1" y1="1" x2="23" y2="23"></line>
                            <path d="M21 21H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h3m3-3h6l2 3h4a2 2 0 0 1 2 2v9.34m-7.72-2.06a4 4 0 1 1-5.56-5.56"></path>
                        </svg>
                        <h5>Camera access issue</h5>
                        <p>${err.message || 'Could not access your camera.'}</p>
                        <div class="alert alert-info text-start mt-3">
                            <h6>Troubleshooting steps:</h6>
                            <ol class="mb-0">
                                <li>Make sure camera permissions are allowed for this site</li>
                                <li>Try using Chrome or Firefox browsers</li>
                                <li>On mobile, ensure the site has camera permissions in your phone settings</li>
                                <li>Try switching to a different network (some networks block camera access)</li>
                            </ol>
                        </div>
                        <button onclick="location.reload()" class="btn btn-primary mt-3">Try Again</button>
                        <button id="uploadImageBtn" class="btn btn-secondary mt-3 ms-2">Upload Image Instead</button>
                    </div>
                `;
                
                // Add event listener for the upload button
                document.getElementById('uploadImageBtn').addEventListener('click', function() {
                    const fileInput = document.createElement('input');
                    fileInput.type = 'file';
                    fileInput.accept = 'image/*';
                    fileInput.style.display = 'none';
                    document.body.appendChild(fileInput);
                    
                    fileInput.addEventListener('change', function(e) {
                        if (e.target.files && e.target.files[0]) {
                            const reader = new FileReader();
                            reader.onload = function(event) {
                                capturedImage = event.target.result;
                                // Show processing status
                                scanStatus.style.display = 'block';
                                // Reset button states
                                resetBtn.disabled = false;
                                captureBtn.disabled = true;
                                // Process the image
                                processHealthScan();
                            };
                            reader.readAsDataURL(e.target.files[0]);
                        }
                        document.body.removeChild(fileInput);
                    });
                    
                    fileInput.click();
                });
            }
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
            const data = {
                scan_type: scanType,
                image_data: capturedImage
            };
            
            // Send the request to the server
            const response = await fetch('/api/health-scan', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
            
            if (!response.ok) {
                throw new Error(`Server responded with ${response.status}: ${response.statusText}`);
            }
            
            // Parse the response
            const responseData = await response.json();
            
            if (responseData.error) {
                throw new Error(responseData.error);
            }
            
            // Save the results
            scanResults = responseData;
            
            // Display the results
            displayResults(responseData);
            
        } catch (err) {
            console.error('Error processing health scan:', err);
            alert('Failed to process health scan: ' + err.message);
            resetBtn.click(); // Reset the scanner
        } finally {
            // Hide the scanning status
            scanStatus.style.display = 'none';
        }
    }
    
    // Display the results
    function displayResults(data) {
        // Show the results section
        resultsSection.style.display = "block";
        
        // Check if API key is missing
        if (data.api_key_missing) {
            document.getElementById("wellnessScoreValue").textContent = "--";
            document.getElementById("wellnessSummary").textContent = data.message || "OpenAI API key is not configured. Please contact the administrator.";
            
            // Hide all result containers
            document.getElementById("faceResultsContainer").style.display = "none";
            document.getElementById("tongueResultsContainer").style.display = "none";
            document.getElementById("eyeResultsContainer").style.display = "none";
            document.getElementById("skinResultsContainer").style.display = "none";
            document.getElementById("healthRisksContainer").style.display = "none";
            document.getElementById("ageComparisonContainer").style.display = "none";
            document.getElementById("healthNotesContainer").style.display = "none";
            return;
        }
        
        // Display wellness score with animation
        const wellnessScore = Math.round(data.wellness_score || 0);
        animateNumber("wellnessScoreValue", 0, wellnessScore, 1500);
        
        // Set wellness summary
        document.getElementById("wellnessSummary").textContent = data.summary || "No summary available.";
        
        // Hide all result containers first
        document.getElementById("faceResultsContainer").style.display = "none";
        document.getElementById("tongueResultsContainer").style.display = "none";
        document.getElementById("eyeResultsContainer").style.display = "none";
        document.getElementById("skinResultsContainer").style.display = "none";
        
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
        
        // Save scan results as a health report to the server
        fetch('/api/save-health-scan', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                scan_type: scanType,
                scan_data: scanResults
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Health scan saved successfully!');
            } else {
                throw new Error(data.error || 'Failed to save health scan.');
            }
        })
        .catch(error => {
            console.error('Error saving health scan:', error);
            alert('Failed to save health scan: ' + error.message);
        });
    });
    
    // Find a doctor button
    findDoctorBtn.addEventListener('click', function() {
        window.location.href = '/doctors-listing?from=health-scan';
    });
    
    // Helper function to get stress level description
    function getStressLevel(value) {
        if (typeof value !== 'number') return 'Unknown';
        
        if (value < 0.3) return 'Low';
        if (value < 0.6) return 'Moderate';
        return 'High';
    }
    
    // Helper function to set risk bar color
    function setRiskBarColor(elementId, riskValue) {
        const element = document.getElementById(elementId);
        if (!element) return;
        
        element.classList.remove('bg-success', 'bg-warning', 'bg-danger');
        
        if (riskValue < 30) {
            element.classList.add('bg-success');
        } else if (riskValue < 60) {
            element.classList.add('bg-warning');
        } else {
            element.classList.add('bg-danger');
        }
    }
    
    // Helper function to animate numbers
    function animateNumber(elementId, start, end, duration) {
        const element = document.getElementById(elementId);
        if (!element) return;
        
        const range = end - start;
        const startTime = performance.now();
        
        function updateNumber(timestamp) {
            const elapsed = timestamp - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            // Use easeOutQuad easing function
            const easedProgress = 1 - Math.pow(1 - progress, 2);
            const current = Math.floor(start + (range * easedProgress));
            
            element.textContent = current;
            
            if (progress < 1) {
                requestAnimationFrame(updateNumber);
            } else {
                element.textContent = end;
            }
        }
        
        requestAnimationFrame(updateNumber);
    }
});
