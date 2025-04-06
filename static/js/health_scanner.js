document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const videoElement = document.getElementById('videoElement');
    const overlayCanvas = document.getElementById('overlay');
    const loadingElement = document.getElementById('loading');
    const startScanBtn = document.getElementById('startScan');
    const captureBtn = document.getElementById('captureFace');
    const recordVoiceBtn = document.getElementById('recordVoice');
    const resultsSection = document.getElementById('results');
    const noResultsSection = document.getElementById('noResults');

    let stream = null;
    let recording = false;
    let mediaRecorder = null;
    let audioChunks = [];
    
    // Start camera
    startScanBtn.addEventListener('click', async () => {
        try {
            stream = await navigator.mediaDevices.getUserMedia({ 
                video: { facingMode: 'user' },
                audio: false
            });
            videoElement.srcObject = stream;
            startScanBtn.disabled = true;
            captureBtn.disabled = false;
            recordVoiceBtn.disabled = false;
            
            // Setup face detection markers
            setupFaceDetection();
        } catch (error) {
            console.error('Error accessing camera:', error);
            alert('Could not access camera. Please check permissions and try again.');
        }
    });
    
    // Setup face detection simulation
    function setupFaceDetection() {
        const ctx = overlayCanvas.getContext('2d');
        overlayCanvas.width = videoElement.videoWidth;
        overlayCanvas.height = videoElement.videoHeight;
        overlayCanvas.style.display = 'block';
        
        // Simulate face detection markers
        function drawFaceMarkers() {
            if (!stream) return;
            
            ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
            
            // Get current dimensions
            overlayCanvas.width = videoElement.videoWidth || videoElement.clientWidth;
            overlayCanvas.height = videoElement.videoHeight || videoElement.clientHeight;
            
            // Draw face detection box (just a simulation)
            const centerX = overlayCanvas.width / 2;
            const centerY = overlayCanvas.height / 2;
            const boxWidth = overlayCanvas.width * 0.6;
            const boxHeight = overlayCanvas.height * 0.6;
            
            ctx.strokeStyle = '#20c997';
            ctx.lineWidth = 2;
            ctx.strokeRect(
                centerX - boxWidth/2,
                centerY - boxHeight/2,
                boxWidth,
                boxHeight
            );
            
            // Add measurement points
            ctx.fillStyle = '#20c997';
            
            // Forehead
            ctx.beginPath();
            ctx.arc(centerX, centerY - boxHeight/3, 3, 0, 2 * Math.PI);
            ctx.fill();
            
            // Cheeks
            ctx.beginPath();
            ctx.arc(centerX - boxWidth/4, centerY, 3, 0, 2 * Math.PI);
            ctx.fill();
            
            ctx.beginPath();
            ctx.arc(centerX + boxWidth/4, centerY, 3, 0, 2 * Math.PI);
            ctx.fill();
            
            // Simulate pulsing effect
            const now = Date.now();
            const pulse = Math.sin(now / 500) * 3 + 5;
            
            ctx.beginPath();
            ctx.arc(centerX, centerY + boxHeight/4, pulse, 0, 2 * Math.PI);
            ctx.fillStyle = 'rgba(32, 201, 151, 0.5)';
            ctx.fill();
            
            requestAnimationFrame(drawFaceMarkers);
        }
        
        drawFaceMarkers();
    }
    
    // Capture face for analysis
    captureBtn.addEventListener('click', () => {
        if (!stream) return;
        
        // Show loading state
        loadingElement.style.display = 'flex';
        
        // Simulate scanning process
        setTimeout(() => {
            processHealthData();
        }, 2000);
    });
    
    // Record voice
    recordVoiceBtn.addEventListener('click', async () => {
        if (recording) {
            // Stop recording
            mediaRecorder.stop();
            recordVoiceBtn.innerHTML = '<i data-feather="mic" class="me-2"></i> Record Voice';
            recordVoiceBtn.classList.remove('btn-danger');
            recordVoiceBtn.classList.add('btn-outline-teal');
            recording = false;
            feather.replace();
        } else {
            // Start recording
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
                    // In a real app, we would send the audio data to the server
                    console.log('Audio recording completed');
                    
                    // Stop audio tracks
                    audioStream.getTracks().forEach(track => track.stop());
                });
                
                mediaRecorder.start();
            } catch (error) {
                console.error('Error accessing microphone:', error);
                alert('Could not access microphone. Please check permissions and try again.');
            }
        }
    });
    
    // Process health data
    function processHealthData() {
        // Prepare scan data - in a real app, this would include actual facial analysis
        const scanData = {
            scan_type: 'facial',
            scan_data: {
                timestamp: new Date().toISOString(),
                face_detected: true,
                voice_recording: audioChunks.length > 0,
                client_info: {
                    browser: navigator.userAgent,
                    screen_resolution: `${window.screen.width}x${window.screen.height}`
                }
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
            displayResults(data);
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error processing health scan. Please try again.');
        })
        .finally(() => {
            loadingElement.style.display = 'none';
        });
    }
    
    // Display results
    function displayResults(data) {
        if (data.error) {
            alert(`Error: ${data.error}`);
            return;
        }
        
        // Show results section
        resultsSection.style.display = 'block';
        noResultsSection.style.display = 'none';
        
        // Update wellness score
        const wellnessScore = document.getElementById('wellnessScore');
        const wellnessLabel = document.getElementById('wellnessLabel');
        const heartAge = document.getElementById('heartAge');
        const stressLevel = document.getElementById('stressLevel');
        const recoveryLevel = document.getElementById('recoveryLevel');
        
        // Animate wellness score counter
        animateCounter(wellnessScore, 0, data.wellness_score || 0, 1500);
        
        // Set wellness label based on score
        let label = 'Poor';
        if (data.wellness_score >= 90) label = 'Excellent';
        else if (data.wellness_score >= 80) label = 'Very Good';
        else if (data.wellness_score >= 70) label = 'Good';
        else if (data.wellness_score >= 60) label = 'Fair';
        
        wellnessLabel.textContent = label;
        
        // Update other summary metrics
        heartAge.textContent = data.heart_age ? `${Math.round(data.heart_age)}` : '--';
        stressLevel.textContent = data.sympathetic_stress ? `${Math.round(data.sympathetic_stress)}%` : '--';
        recoveryLevel.textContent = data.parasympathetic_activity ? `${Math.round(data.parasympathetic_activity)}%` : '--';
        
        // Update vital signs
        updateVitalSign('heartRate', data.heart_rate, 'bpm', 60, 100);
        updateVitalSign('bloodPressure', 
                      `${data.blood_pressure_systolic || '--'}/${data.blood_pressure_diastolic || '--'}`, 
                      'mmHg', 
                      90, 140,
                      data.blood_pressure_systolic);
        updateVitalSign('breathingRate', data.breathing_rate, 'bpm', 12, 20);
        updateVitalSign('oxygenSaturation', data.oxygen_saturation, '%', 95, 100);
        updateVitalSign('hemoglobin', data.hemoglobin, 'g/dL', 13.5, 17.5);
        updateVitalSign('hba1c', data.hemoglobin_a1c, '%', 4, 5.7);
        
        // Update risk assessments
        updateRiskAssessment('ascvdRisk', data.ascvd_risk, 5, 10);
        updateRiskAssessment('hypertensionRisk', data.hypertension_risk, 5, 10);
        updateRiskAssessment('glucoseRisk', data.glucose_risk, 5, 10);
        updateRiskAssessment('cholesterolRisk', data.cholesterol_risk, 5, 10);
        updateRiskAssessment('tbRisk', data.tuberculosis_risk, 1, 5);
        
        // Update recommendations
        const recommendationsEl = document.getElementById('recommendations');
        let recommendationsHTML = '';
        
        if (data.notes && data.notes.recommendations) {
            const recs = data.notes.recommendations;
            recommendationsHTML = `<ul class="mb-0">`;
            if (Array.isArray(recs)) {
                recs.forEach(rec => {
                    recommendationsHTML += `<li class="mb-2">${rec}</li>`;
                });
            } else if (typeof recs === 'string') {
                recommendationsHTML += `<li>${recs}</li>`;
            } else {
                for (const key in recs) {
                    recommendationsHTML += `<li class="mb-2">${recs[key]}</li>`;
                }
            }
            recommendationsHTML += `</ul>`;
        } else {
            recommendationsHTML = `
                <p>Based on your scan results:</p>
                <ul>
                    <li class="mb-2">Maintain a balanced diet rich in fruits, vegetables, and whole grains</li>
                    <li class="mb-2">Stay hydrated by drinking plenty of water throughout the day</li>
                    <li class="mb-2">Engage in regular physical activity for at least 30 minutes daily</li>
                    <li class="mb-2">Practice stress management techniques such as meditation</li>
                    <li>Ensure 7-8 hours of quality sleep each night</li>
                </ul>
            `;
        }
        
        recommendationsEl.innerHTML = recommendationsHTML;
    }
    
    // Helper functions
    function updateVitalSign(elementId, value, unit, minNormal, maxNormal, displayValue) {
        const element = document.getElementById(elementId);
        const progressBar = document.getElementById(`${elementId}Bar`);
        
        if (!element || !progressBar) return;
        
        // Set the display text
        element.textContent = value ? `${displayValue !== undefined ? displayValue : value}${unit}` : `--${unit}`;
        
        // Calculate progress percentage for the bar
        if (value) {
            let percentage = 0;
            // Different calculation based on the type of vital sign
            if (elementId === 'oxygenSaturation') {
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
            animateWidth(progressBar, 0, value);
            
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
});
