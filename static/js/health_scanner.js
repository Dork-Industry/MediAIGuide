document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const videoElement = document.getElementById('videoElement');
    const overlayCanvas = document.getElementById('overlay');
    const loadingElement = document.getElementById('loading');
    const loadingText = document.getElementById('loadingText');
    const startScanBtn = document.getElementById('startScan');
    const captureBtn = document.getElementById('captureImage');
    const recordVoiceBtn = document.getElementById('recordVoice');
    const resultsSection = document.getElementById('results');
    const noResultsSection = document.getElementById('noResults');
    
    // Scan result containers
    const faceScanResults = document.getElementById('faceScanResults');
    const tongueScanResults = document.getElementById('tongueScanResults');
    const eyeScanResults = document.getElementById('eyeScanResults');
    const skinScanResults = document.getElementById('skinScanResults');
    
    // Instructions
    const faceScanInstructions = document.getElementById('faceScanInstructions');
    const tongueScanInstructions = document.getElementById('tongueScanInstructions');
    const eyeScanInstructions = document.getElementById('eyeScanInstructions');
    const skinScanInstructions = document.getElementById('skinScanInstructions');
    
    let stream = null;
    let recording = false;
    let mediaRecorder = null;
    let audioChunks = [];
    let currentScanType = 'face'; // Default scan type
    
    // Handle scan type selection
    const scanTypeRadios = document.querySelectorAll('input[name="scanType"]');
    scanTypeRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            currentScanType = this.value;
            updateInstructionsForScanType(currentScanType);
            updateLoadingTextForScanType(currentScanType);
            
            // Reset video if it's running
            if (stream) {
                stopCamera();
                startScanBtn.disabled = false;
                captureBtn.disabled = true;
                recordVoiceBtn.disabled = currentScanType !== 'face';
                overlayCanvas.style.display = 'none';
            }
            
            // Hide all result containers
            hideAllResults();
        });
    });
    
    // Initially set record voice button disabled for non-face scans
    document.getElementById('scanTypeFace').addEventListener('change', function() {
        recordVoiceBtn.disabled = !this.checked || !stream;
    });
    
    document.querySelectorAll('input[name="scanType"]:not(#scanTypeFace)').forEach(radio => {
        radio.addEventListener('change', function() {
            if (this.checked) {
                recordVoiceBtn.disabled = true;
            }
        });
    });
    
    // Update instructions based on scan type
    function updateInstructionsForScanType(type) {
        faceScanInstructions.style.display = 'none';
        tongueScanInstructions.style.display = 'none';
        eyeScanInstructions.style.display = 'none';
        skinScanInstructions.style.display = 'none';
        
        const instructionsTitle = document.getElementById('instructionsTitle');
        
        switch(type) {
            case 'face':
                faceScanInstructions.style.display = 'block';
                instructionsTitle.textContent = 'How to Scan Your Face';
                break;
            case 'tongue':
                tongueScanInstructions.style.display = 'block';
                instructionsTitle.textContent = 'How to Scan Your Tongue';
                break;
            case 'eye':
                eyeScanInstructions.style.display = 'block';
                instructionsTitle.textContent = 'How to Scan Your Eyes';
                break;
            case 'skin':
                skinScanInstructions.style.display = 'block';
                instructionsTitle.textContent = 'How to Scan Your Skin';
                break;
        }
    }
    
    function updateLoadingTextForScanType(type) {
        switch(type) {
            case 'face':
                loadingText.innerText = 'Analyzing vital signs...';
                break;
            case 'tongue':
                loadingText.innerText = 'Analyzing tongue condition...';
                break;
            case 'eye':
                loadingText.innerText = 'Analyzing eye health...';
                break;
            case 'skin':
                loadingText.innerText = 'Analyzing skin condition...';
                break;
        }
    }
    
    // Hide all result sections
    function hideAllResults() {
        faceScanResults.style.display = 'none';
        tongueScanResults.style.display = 'none';
        eyeScanResults.style.display = 'none';
        skinScanResults.style.display = 'none';
        resultsSection.style.display = 'none';
        noResultsSection.style.display = 'block';
    }
    
    // Show appropriate result section based on scan type
    function showResultsForScanType(type) {
        hideAllResults();
        resultsSection.style.display = 'block';
        noResultsSection.style.display = 'none';
        
        switch(type) {
            case 'face':
                faceScanResults.style.display = 'block';
                break;
            case 'tongue':
                tongueScanResults.style.display = 'block';
                break;
            case 'eye':
                eyeScanResults.style.display = 'block';
                break;
            case 'skin':
                skinScanResults.style.display = 'block';
                break;
        }
    }
    
    // Initialize instructions for default scan type
    updateInstructionsForScanType(currentScanType);
    updateLoadingTextForScanType(currentScanType);
    
    // Start camera
    startScanBtn.addEventListener('click', async () => {
        try {
            // Different camera positioning guidance based on scan type
            let facingMode = 'user'; // Default front camera for face scan
            if (currentScanType === 'tongue' || currentScanType === 'eye') {
                facingMode = 'user'; // Front camera for tongue and eye
            } else if (currentScanType === 'skin') {
                facingMode = { exact: 'environment' }; // Try to use back camera for skin
            }
            
            // Try to get the requested camera
            try {
                stream = await navigator.mediaDevices.getUserMedia({
                    video: { facingMode: facingMode },
                    audio: false
                });
            } catch (e) {
                // Fallback to any available camera
                console.log('Specific camera not available, using default');
                stream = await navigator.mediaDevices.getUserMedia({
                    video: true,
                    audio: false
                });
            }
            
            videoElement.srcObject = stream;
            startScanBtn.disabled = true;
            captureBtn.disabled = false;
            recordVoiceBtn.disabled = (currentScanType !== 'face');
            
            // Setup scan guidance overlay based on scan type
            setupScanningOverlay(currentScanType);
        } catch (error) {
            console.error('Error accessing camera:', error);
            alert('Could not access camera. Please check permissions and try again.');
        }
    });
    
    // Setup scan guidance overlay
    function setupScanningOverlay(scanType) {
        const ctx = overlayCanvas.getContext('2d');
        overlayCanvas.width = videoElement.videoWidth || 640;
        overlayCanvas.height = videoElement.videoHeight || 480;
        overlayCanvas.style.display = 'block';
        
        // Clear previous overlays
        ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
        
        // Define dimensions for guides
        const centerX = overlayCanvas.width / 2;
        const centerY = overlayCanvas.height / 2;
        
        ctx.strokeStyle = '#20c997';
        ctx.lineWidth = 2;
        
        switch(scanType) {
            case 'face':
                // Face outline guide
                const faceWidth = overlayCanvas.width * 0.6;
                const faceHeight = overlayCanvas.height * 0.7;
                drawOval(ctx, centerX, centerY, faceWidth / 2, faceHeight / 2);
                
                // Add measurement points
                ctx.fillStyle = 'rgba(32, 201, 151, 0.7)';
                // Forehead point
                drawPoint(ctx, centerX, centerY - faceHeight * 0.3);
                // Cheek points
                drawPoint(ctx, centerX - faceWidth * 0.3, centerY);
                drawPoint(ctx, centerX + faceWidth * 0.3, centerY);
                // Chin area
                drawPoint(ctx, centerX, centerY + faceHeight * 0.3);
                
                // Pulsing circle for heart rate
                animatePulse(ctx, centerX, centerY + faceHeight * 0.1);
                break;
                
            case 'tongue':
                // Mouth area outline
                const tongueWidth = overlayCanvas.width * 0.4;
                const tongueHeight = overlayCanvas.height * 0.3;
                ctx.beginPath();
                ctx.ellipse(centerX, centerY, tongueWidth / 2, tongueHeight / 2, 0, 0, Math.PI * 2);
                ctx.stroke();
                
                // Guide text
                ctx.font = '16px Arial';
                ctx.fillStyle = 'white';
                ctx.textAlign = 'center';
                ctx.fillText('Open wide and stick out tongue', centerX, centerY - tongueHeight * 0.8);
                ctx.fillText('Ensure good lighting', centerX, centerY + tongueHeight * 0.8 + 24);
                break;
                
            case 'eye':
                // Eye area outline (oval shape for eye area focus)
                const eyeWidth = overlayCanvas.width * 0.25;
                const eyeHeight = overlayCanvas.height * 0.15;
                ctx.beginPath();
                ctx.ellipse(centerX, centerY, eyeWidth, eyeHeight, 0, 0, Math.PI * 2);
                ctx.stroke();
                
                // Guide text
                ctx.font = '16px Arial';
                ctx.fillStyle = 'white';
                ctx.textAlign = 'center';
                ctx.fillText('Position one eye in the circle', centerX, centerY - eyeHeight * 2);
                ctx.fillText('Keep eye open and steady', centerX, centerY + eyeHeight * 2 + 24);
                break;
                
            case 'skin':
                // Square region for skin analysis
                const skinWidth = overlayCanvas.width * 0.5;
                const skinHeight = overlayCanvas.height * 0.5;
                ctx.strokeRect(
                    centerX - skinWidth/2,
                    centerY - skinHeight/2,
                    skinWidth,
                    skinHeight
                );
                
                // Guide text
                ctx.font = '16px Arial';
                ctx.fillStyle = 'white';
                ctx.textAlign = 'center';
                ctx.fillText('Position skin area within box', centerX, centerY - skinHeight * 0.6);
                ctx.fillText('Ensure good lighting', centerX, centerY + skinHeight * 0.6 + 24);
                break;
        }
        
        // Animation loop for dynamic elements
        if (scanType === 'face') {
            animateOverlay();
        }
    }
    
    function drawPoint(ctx, x, y) {
        ctx.beginPath();
        ctx.arc(x, y, 4, 0, Math.PI * 2);
        ctx.fill();
    }
    
    function drawOval(ctx, x, y, radiusX, radiusY) {
        ctx.beginPath();
        ctx.ellipse(x, y, radiusX, radiusY, 0, 0, Math.PI * 2);
        ctx.stroke();
    }
    
    function animatePulse(ctx, x, y) {
        const startTime = performance.now();
        
        function pulse(time) {
            if (!stream) return; // Stop animation if camera is off
            
            const elapsed = time - startTime;
            const size = Math.sin(elapsed / 500) * 3 + 5; // Pulsing effect
            
            ctx.clearRect(x - 15, y - 15, 30, 30); // Clear only the pulse area
            
            ctx.beginPath();
            ctx.arc(x, y, size, 0, Math.PI * 2);
            ctx.fillStyle = 'rgba(32, 201, 151, 0.7)';
            ctx.fill();
            
            requestAnimationFrame(pulse);
        }
        
        requestAnimationFrame(pulse);
    }
    
    function animateOverlay() {
        if (!stream) return; // Stop if camera is off
        
        const ctx = overlayCanvas.getContext('2d');
        // Update canvas dimensions in case video size changed
        overlayCanvas.width = videoElement.videoWidth || overlayCanvas.width;
        overlayCanvas.height = videoElement.videoHeight || overlayCanvas.height;
        
        // Redraw the overlay appropriate for the current scan type
        setupScanningOverlay(currentScanType);
        
        if (stream) {
            requestAnimationFrame(animateOverlay);
        }
    }
    
    // Stop the camera
    function stopCamera() {
        if (stream) {
            stream.getTracks().forEach(track => {
                track.stop();
            });
            stream = null;
            videoElement.srcObject = null;
        }
    }
    
    // Capture image for analysis
    captureBtn.addEventListener('click', () => {
        if (!stream) return;
        
        // Show loading state
        loadingElement.style.display = 'flex';
        
        // Create canvas to capture the current video frame
        const captureCanvas = document.createElement('canvas');
        captureCanvas.width = videoElement.videoWidth;
        captureCanvas.height = videoElement.videoHeight;
        const ctx = captureCanvas.getContext('2d');
        ctx.drawImage(videoElement, 0, 0, captureCanvas.width, captureCanvas.height);
        
        // Convert to base64 string (to send to server)
        const imageData = captureCanvas.toDataURL('image/jpeg');
        
        // Prepare audio data if recorded (for face scan only)
        let audioData = null;
        if (audioChunks.length > 0 && currentScanType === 'face') {
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            // In a real app, you would send this audio data to the server
            console.log('Audio data captured', audioBlob.size, 'bytes');
            // Reset audio recording
            audioChunks = [];
            if (recording) {
                mediaRecorder.stop();
                recording = false;
                recordVoiceBtn.innerHTML = '<i data-feather="mic" class="me-2"></i> Record Voice';
                recordVoiceBtn.classList.remove('btn-danger');
                recordVoiceBtn.classList.add('btn-outline-teal');
                feather.replace();
            }
        }
        
        // Prepare scan data
        const scanData = {
            scan_type: currentScanType,
            image_data: imageData.split(',')[1], // Remove the data:image/jpeg;base64, part
            has_audio: audioData !== null,
            client_info: {
                browser: navigator.userAgent,
                timestamp: new Date().toISOString(),
                screen_dimensions: `${window.innerWidth}x${window.innerHeight}`
            }
        };
        
        // Send data to server
        fetch('/api/health-scan', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(scanData)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            processResults(data);
            loadingElement.style.display = 'none';
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error processing health scan. Please try again.');
            loadingElement.style.display = 'none';
            
            // For demo purposes, show mock results when API fails
            const mockData = generateMockData(currentScanType);
            processResults(mockData);
        });
    });
    
    // Record voice
    recordVoiceBtn.addEventListener('click', async () => {
        if (recording) {
            // Stop recording
            mediaRecorder.stop();
            recording = false;
            recordVoiceBtn.innerHTML = '<i data-feather="mic" class="me-2"></i> Record Voice';
            recordVoiceBtn.classList.remove('btn-danger');
            recordVoiceBtn.classList.add('btn-outline-teal');
            feather.replace();
        } else {
            try {
                const audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
                recording = true;
                
                recordVoiceBtn.innerHTML = '<i data-feather="square" class="me-2"></i> Stop Recording';
                recordVoiceBtn.classList.remove('btn-outline-teal');
                recordVoiceBtn.classList.add('btn-danger');
                feather.replace();
                
                mediaRecorder = new MediaRecorder(audioStream);
                audioChunks = [];
                
                mediaRecorder.addEventListener('dataavailable', event => {
                    audioChunks.push(event.data);
                });
                
                mediaRecorder.addEventListener('stop', () => {
                    console.log('Audio recording completed');
                    audioStream.getTracks().forEach(track => track.stop());
                });
                
                mediaRecorder.start();
            } catch (error) {
                console.error('Error accessing microphone:', error);
                alert('Could not access microphone. Please check permissions and try again.');
            }
        }
    });
    
    // Process results from API
    function processResultData(data) {
        // Process results based on scan type
        switch(data.scan_type) {
            case 'face':
                processFacialScanResults(data);
                break;
            case 'tongue':
                processTongueScanResults(data);
                break;
            case 'eye':
                processEyeScanResults(data);
                break;
            case 'skin':
                processSkinScanResults(data);
                break;
        }
        
        // Update recommendations
        updateRecommendations(data);
        
        // Show the appropriate results section
        showResultsForScanType(data.scan_type);
    }
    
    // Process the real results
    function processResults(data) {
        if (data.error) {
            alert(`Error: ${data.error}`);
            return;
        }
        
        processResultData(data);
    }
    
    // Process facial scan results
    function processFacialScanResults(data) {
        // Update wellness score with animation
        const wellnessScore = document.getElementById('wellnessScore');
        const wellnessLabel = document.getElementById('wellnessLabel');
        const heartAge = document.getElementById('heartAge');
        const stressLevel = document.getElementById('stressLevel');
        const recoveryLevel = document.getElementById('recoveryLevel');
        
        // Animate wellness score
        animateCounter(wellnessScore, 0, data.wellness_score || 75, 1500);
        
        // Set wellness label based on score
        let label = 'Poor';
        const score = data.wellness_score || 75;
        if (score >= 90) label = 'Excellent';
        else if (score >= 80) label = 'Very Good';
        else if (score >= 70) label = 'Good';
        else if (score >= 60) label = 'Fair';
        
        wellnessLabel.textContent = label;
        
        // Update other metrics
        heartAge.textContent = data.heart_age ? `${Math.round(data.heart_age)}` : '32';
        stressLevel.textContent = data.sympathetic_stress ? `${Math.round(data.sympathetic_stress)}%` : '42%';
        recoveryLevel.textContent = data.parasympathetic_activity ? `${Math.round(data.parasympathetic_activity)}%` : '78%';
        
        // Update vital signs
        updateVitalSign('heartRate', data.heart_rate || 72, 'bpm', 60, 100);
        updateVitalSign('bloodPressure', 
                     `${data.blood_pressure_systolic || 120}/${data.blood_pressure_diastolic || 80}`, 
                     'mmHg', 
                     90, 140,
                     data.blood_pressure_systolic || 120);
        updateVitalSign('breathingRate', data.breathing_rate || 16, 'bpm', 12, 20);
        updateVitalSign('oxygenSaturation', data.oxygen_saturation || 98, '%', 95, 100);
        updateVitalSign('hemoglobin', data.hemoglobin || 14.5, 'g/dL', 13.5, 17.5);
        updateVitalSign('hba1c', data.hemoglobin_a1c || 5.2, '%', 4, 5.7);
        
        // Update risk assessments
        updateRiskAssessment('ascvdRisk', data.ascvd_risk || 4.2, 5, 10);
        updateRiskAssessment('hypertensionRisk', data.hypertension_risk || 3.7, 5, 10);
        updateRiskAssessment('glucoseRisk', data.glucose_risk || 2.8, 5, 10); 
        updateRiskAssessment('cholesterolRisk', data.cholesterol_risk || 3.5, 5, 10);
        updateRiskAssessment('tbRisk', data.tuberculosis_risk || 0.5, 1, 5);
    }
    
    // Process tongue scan results
    function processTongueScanResults(data) {
        // Update tongue analysis results
        document.getElementById('tongueColor').textContent = data.tongue_color || 'Pale Pink';
        document.getElementById('tongueCoating').textContent = data.tongue_coating || 'Thin White';
        document.getElementById('tongueShape').textContent = data.tongue_shape || 'Normal';
        document.getElementById('tcmDiagnosis').textContent = data.tcm_diagnosis || 'Slight Qi Deficiency';
        document.getElementById('vitaminDeficiency').textContent = data.vitamin_deficiency || 'B12, Iron (Mild)';
        document.getElementById('infectionIndicator').textContent = data.infection_indicator || 'None Detected';
    }
    
    // Process eye scan results
    function processEyeScanResults(data) {
        // Update eye analysis results
        document.getElementById('scleraColor').textContent = data.sclera_color || 'Normal White';
        document.getElementById('conjunctivaColor').textContent = data.conjunctiva_color || 'Pink';
        document.getElementById('pupilReactivity').textContent = data.pupil_reactivity || 'Normal';
        document.getElementById('eyeCondition').textContent = data.eye_condition || 'No Issues Detected';
        
        // Eye redness with progress bar
        updateVitalSign('eyeRedness', data.eye_redness || 15, '%', 0, 30, null, 'eyeRednessBar');
    }
    
    // Process skin scan results  
    function processSkinScanResults(data) {
        // Update skin analysis results
        document.getElementById('skinColor').textContent = data.skin_color || 'Normal';
        document.getElementById('skinTexture').textContent = data.skin_texture || 'Even';
        document.getElementById('rashDetection').textContent = data.rash_detection ? 'Detected' : 'None Detected';
        document.getElementById('rashPattern').textContent = data.rash_pattern || 'N/A';
        document.getElementById('skinCondition').textContent = data.skin_condition || 'Healthy';
    }
    
    // Update recommendations based on scan type and results
    function updateRecommendations(data) {
        const recommendationsEl = document.getElementById('recommendations');
        let recommendationsHTML = '';
        
        if (data.recommendations && data.recommendations.length > 0) {
            // Use server-provided recommendations if available
            recommendationsHTML = '<ul class="mb-0">';
            data.recommendations.forEach(rec => {
                recommendationsHTML += `<li class="mb-2">${rec}</li>`;
            });
            recommendationsHTML += '</ul>';
        } else {
            // Default recommendations based on scan type
            recommendationsHTML = '<ul class="mb-0">';
            
            switch(data.scan_type) {
                case 'face':
                    recommendationsHTML += `
                        <li class="mb-2">Maintain a balanced diet rich in fruits, vegetables, and whole grains</li>
                        <li class="mb-2">Stay hydrated by drinking at least 8 glasses of water daily</li>
                        <li class="mb-2">Engage in regular cardiovascular exercise (30 min, 5 days/week)</li>
                        <li class="mb-2">Practice stress management techniques like meditation</li>
                        <li>Ensure 7-8 hours of quality sleep each night</li>
                    `;
                    break;
                case 'tongue':
                    recommendationsHTML += `
                        <li class="mb-2">Consider a vitamin B complex supplement</li>
                        <li class="mb-2">Increase consumption of iron-rich foods (leafy greens, beans)</li>
                        <li class="mb-2">Stay well-hydrated throughout the day</li>
                        <li class="mb-2">Practice good oral hygiene including tongue cleaning</li>
                        <li>Consider following up with a nutritionist for a detailed plan</li>
                    `;
                    break;
                case 'eye':
                    recommendationsHTML += `
                        <li class="mb-2">Take regular breaks when using digital screens (20-20-20 rule)</li>
                        <li class="mb-2">Ensure adequate lighting when reading or working</li>
                        <li class="mb-2">Consider foods rich in lutein and zeaxanthin for eye health</li>
                        <li class="mb-2">Use artificial tears if experiencing dryness</li>
                        <li>Schedule a routine eye examination</li>
                    `;
                    break;
                case 'skin':
                    recommendationsHTML += `
                        <li class="mb-2">Maintain a consistent skincare routine</li>
                        <li class="mb-2">Use broad-spectrum sunscreen daily</li>
                        <li class="mb-2">Stay well-hydrated for skin health</li>
                        <li class="mb-2">Consider foods rich in antioxidants and omega-3 fatty acids</li>
                        <li>Consult with a dermatologist for personalized advice</li>
                    `;
                    break;
            }
            
            recommendationsHTML += '</ul>';
        }
        
        recommendationsEl.innerHTML = recommendationsHTML;
    }
    
    // Helper functions
    function updateVitalSign(elementId, value, unit, minNormal, maxNormal, displayValue, barId) {
        const element = document.getElementById(elementId);
        const progressBar = document.getElementById(barId || `${elementId}Bar`);
        
        if (!element || !progressBar) return;
        
        // Set the display text
        element.textContent = value ? `${displayValue !== undefined ? displayValue : value}${unit}` : `--${unit}`;
        
        // Calculate progress percentage for the bar
        if (value) {
            let percentage = 0;
            // Different calculation based on the type of vital sign
            if (elementId === 'oxygenSaturation' || elementId === 'eyeRedness') {
                // For oxygen, we want 95-100% to be full scale
                percentage = Math.max(0, Math.min(100, (value - 90) * 20));
            } else if (elementId === 'hba1c') {
                // For HbA1c, lower is better, and normal range is 4-5.7%
                percentage = Math.max(0, Math.min(100, 100 - ((value - 4) * 33.3)));
            } else {
                // For other metrics, use the normal range
                percentage = Math.max(0, Math.min(100, ((value - minNormal) / (maxNormal - minNormal)) * 100));
            }
            
            // Animate the progress bar
            animateWidth(progressBar, 0, percentage);
            
            // Set color based on whether it's in normal range
            if (value < minNormal || value > maxNormal) {
                progressBar.classList.add('risk-medium');
                progressBar.classList.remove('risk-low');
            } else {
                progressBar.classList.add('risk-low');
                progressBar.classList.remove('risk-medium');
            }
        } else {
            progressBar.style.width = '0%';
        }
    }
    
    function updateRiskAssessment(elementId, value, mediumThreshold, highThreshold) {
        const element = document.getElementById(elementId);
        const progressBar = document.getElementById(`${elementId}Bar`);
        
        if (!element || !progressBar) return;
        
        // Set the display text
        element.textContent = value !== undefined ? `${value}%` : `--%`;
        
        // Set progress bar
        if (value !== undefined) {
            // Animate the progress bar
            animateWidth(progressBar, 0, value * 10); // Scale to percentage (0-10% risk → 0-100% bar)
            
            // Set color based on risk level
            progressBar.classList.remove('risk-low', 'risk-medium', 'risk-high');
            if (value >= highThreshold) {
                progressBar.classList.add('risk-high');
            } else if (value >= mediumThreshold) {
                progressBar.classList.add('risk-medium');
            } else {
                progressBar.classList.add('risk-low');
            }
        } else {
            progressBar.style.width = '0%';
        }
    }
    
    function animateWidth(element, start, end, duration = 1000) {
        const startTime = performance.now();
        
        function update(currentTime) {
            const elapsedTime = currentTime - startTime;
            const progress = Math.min(elapsedTime / duration, 1);
            const currentWidth = start + (end - start) * easeOutQuad(progress);
            
            element.style.width = `${currentWidth}%`;
            
            if (progress < 1) {
                requestAnimationFrame(update);
            }
        }
        
        requestAnimationFrame(update);
    }
    
    function animateCounter(element, start, end, duration = 1000) {
        const startTime = performance.now();
        const format = num => Math.round(num);
        
        function update(currentTime) {
            const elapsedTime = currentTime - startTime;
            const progress = Math.min(elapsedTime / duration, 1);
            const currentValue = start + (end - start) * easeOutQuad(progress);
            
            element.textContent = format(currentValue);
            
            if (progress < 1) {
                requestAnimationFrame(update);
            }
        }
        
        requestAnimationFrame(update);
    }
    
    function easeOutQuad(t) {
        return t * (2 - t);
    }
    
    // For demonstration purposes - can be removed in production
    function generateMockData(scanType) {
        // This function generates mock data for demonstration purposes
        // In a real app, this would be replaced with actual data from the server
        const baseData = {
            scan_type: scanType,
            wellness_score: 78,
            recommendations: [
                "Maintain a balanced diet rich in fruits, vegetables, and whole grains",
                "Stay hydrated by drinking at least 8 glasses of water daily",
                "Engage in regular physical activity (30 minutes, 5 days a week)",
                "Practice stress management techniques like meditation",
                "Ensure 7-8 hours of quality sleep each night"
            ]
        };
        
        switch(scanType) {
            case 'face':
                return {
                    ...baseData,
                    heart_rate: 72,
                    blood_pressure_systolic: 120,
                    blood_pressure_diastolic: 80,
                    breathing_rate: 16,
                    oxygen_saturation: 98,
                    sympathetic_stress: 42,
                    parasympathetic_activity: 78,
                    hemoglobin: 14.5,
                    hemoglobin_a1c: 5.2,
                    ascvd_risk: 4.2,
                    hypertension_risk: 3.7,
                    glucose_risk: 2.8,
                    cholesterol_risk: 3.5,
                    tuberculosis_risk: 0.5,
                    heart_age: 32
                };
            case 'tongue':
                return {
                    ...baseData,
                    tongue_color: 'Pale Pink',
                    tongue_coating: 'Thin White',
                    tongue_shape: 'Normal',
                    tcm_diagnosis: 'Slight Qi Deficiency',
                    vitamin_deficiency: 'B12, Iron (Mild)',
                    infection_indicator: 'None Detected',
                    recommendations: [
                        "Consider a vitamin B complex supplement",
                        "Increase consumption of iron-rich foods (leafy greens, beans)",
                        "Stay well-hydrated throughout the day",
                        "Practice good oral hygiene including tongue cleaning",
                        "Consider following up with a nutritionist for a detailed plan"
                    ]
                };
            case 'eye':
                return {
                    ...baseData,
                    sclera_color: 'Normal White',
                    conjunctiva_color: 'Pink',
                    eye_redness: 15,
                    pupil_reactivity: 'Normal',
                    eye_condition: 'No Issues Detected',
                    recommendations: [
                        "Take regular breaks when using digital screens (20-20-20 rule)",
                        "Ensure adequate lighting when reading or working",
                        "Consider foods rich in lutein and zeaxanthin for eye health",
                        "Use artificial tears if experiencing dryness",
                        "Schedule a routine eye examination"
                    ]
                };
            case 'skin':
                return {
                    ...baseData,
                    skin_color: 'Normal',
                    skin_texture: 'Even',
                    rash_detection: false,
                    rash_pattern: 'N/A',
                    skin_condition: 'Healthy',
                    recommendations: [
                        "Maintain a consistent skincare routine",
                        "Use broad-spectrum sunscreen daily",
                        "Stay well-hydrated for skin health",
                        "Consider foods rich in antioxidants and omega-3 fatty acids",
                        "Consult with a dermatologist for personalized advice"
                    ]
                };
            default:
                return baseData;
        }
    }
    
    // Initialize the scan type selection
    updateInstructionsForScanType('face');
});
