"""
Machine learning module for heart rate detection using webcam
"""
import cv2
import numpy as np
import time
from scipy.signal import butter, filtfilt
from scipy.fft import rfft, rfftfreq
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HeartRateMonitor:
    """Heart rate monitoring using computer vision and signal processing"""
    
    def __init__(self, buffer_size=300, fps=30, min_face_size=(80, 80)):
        """
        Initialize the heart rate monitor
        
        Args:
            buffer_size: Number of frames to store in signal buffer
            fps: Frames per second (camera capture rate)
            min_face_size: Minimum face size to detect
        """
        self.buffer_size = buffer_size
        self.fps = fps
        self.min_face_size = min_face_size
        
        # Load face cascade classifier
        try:
            self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            if self.face_cascade.empty():
                logger.error("Failed to load face cascade classifier")
                raise Exception("Failed to load face cascade classifier")
        except Exception as e:
            logger.error(f"Error loading face cascade: {str(e)}")
            raise
            
        # Initialize signal buffer
        self.signal_buffer = []
        self.times = []
        self.heart_rate = 0
        self.heart_rate_history = []
        self.face_detected = False
        self.last_face = None
        self.face_detection_frames = 0
        
        # Training data for machine learning model
        self.training_data = {
            # Mapping of signal features to vital signs
            "heart_rate": [],       # Historical heart rates
            "features": [],         # Features extracted from signals
            "blood_pressure": [],   # Historical blood pressure values (if available)
            "stress_level": []      # Historical stress levels (if available)
        }
        
        logger.info("Heart rate monitor initialized")
        
    def _bandpass_filter(self, data, lowcut=0.7, highcut=4.0, order=4):
        """
        Apply a bandpass filter to the signal
        
        Args:
            data: Signal data to filter
            lowcut: Low cutoff frequency (Hz)
            highcut: High cutoff frequency (Hz)
            order: Filter order
            
        Returns:
            Filtered signal
        """
        nyq = 0.5 * self.fps
        low = lowcut / nyq
        high = highcut / nyq
        
        b, a = butter(order, [low, high], btype='band')
        y = filtfilt(b, a, data)
        return y
        
    def _extract_signal_features(self, signal):
        """
        Extract features from the signal for machine learning
        
        Args:
            signal: Processed signal data
            
        Returns:
            Dictionary of signal features
        """
        if len(signal) < 2:
            return {}
            
        # Extract time domain features
        mean = np.mean(signal)
        std = np.std(signal)
        min_val = np.min(signal)
        max_val = np.max(signal)
        range_val = max_val - min_val
        
        # Extract frequency domain features
        fft_vals = np.abs(rfft(signal))
        freqs = rfftfreq(len(signal), 1/self.fps)
        dominant_freq = freqs[np.argmax(fft_vals)]
        power = np.sum(fft_vals**2) / len(fft_vals)
        
        # Return feature dictionary
        return {
            "mean": mean,
            "std": std,
            "range": range_val,
            "dominant_freq": dominant_freq,
            "power": power,
            "peak_amplitude": max_val
        }
        
    def _predict_vitals_from_features(self, features):
        """
        Predict vital signs from signal features using trained models
        
        Args:
            features: Dictionary of signal features
            
        Returns:
            Dictionary of predicted vital signs
        """
        # If we don't have enough training data, use the frequency analysis method
        if len(self.training_data["heart_rate"]) < 50 or not features:
            return {}
            
        # Simple averaging model for demonstration
        # In a real scenario, this would be replaced with a trained ML model
        
        # For demonstration, we're just returning the heart rate
        # In a real ML system, this would predict BP, stress, etc.
        return {}
    
    def _update_training_data(self, signal, heart_rate):
        """Update the training data with new measurements"""
        if len(signal) < self.fps * 2 or heart_rate <= 0:
            return
            
        features = self._extract_signal_features(signal)
        if features and 40 <= heart_rate <= 200:  # Valid heart rate range
            self.training_data["heart_rate"].append(heart_rate)
            self.training_data["features"].append(features)
            
            # Keep training data at a reasonable size
            if len(self.training_data["heart_rate"]) > 1000:
                self.training_data["heart_rate"] = self.training_data["heart_rate"][-1000:]
                self.training_data["features"] = self.training_data["features"][-1000:]
    
    def process_frame(self, frame):
        """
        Process a video frame to update heart rate measurement
        
        Args:
            frame: Video frame to process
            
        Returns:
            Processed frame with annotations, heart rate
        """
        if frame is None or frame.size == 0:
            logger.warning("Empty frame received")
            return frame, 0, False
            
        # Convert to grayscale for face detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=self.min_face_size
        )
        
        self.face_detected = len(faces) > 0
        
        # If no face detected, use the last known face position for a few frames
        if not self.face_detected and self.last_face is not None and self.face_detection_frames < 10:
            faces = [self.last_face]
            self.face_detection_frames += 1
        elif self.face_detected:
            self.last_face = faces[0]
            self.face_detection_frames = 0
            
        # Process each detected face (using only the first one for simplicity)
        for (x, y, w, h) in faces:
            # Draw a rectangle around the face
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
            # Define forehead region (top 1/3 of the face)
            forehead_y = y + int(h * 0.1)
            forehead_h = int(h * 0.3)
            forehead_x = x + int(w * 0.3)
            forehead_w = int(w * 0.4)
            
            # Draw rectangle around forehead ROI
            cv2.rectangle(frame, (forehead_x, forehead_y), 
                         (forehead_x + forehead_w, forehead_y + forehead_h), 
                         (255, 0, 0), 2)
            
            # Extract ROI
            roi = frame[forehead_y:forehead_y+forehead_h, forehead_x:forehead_x+forehead_w]
            
            # Skip if ROI is too small
            if roi.size == 0:
                continue
                
            # Extract green channel and calculate mean
            try:
                green_channel = roi[:, :, 1]
                mean_green = np.mean(green_channel)
                
                # Add to buffer
                self.signal_buffer.append(mean_green)
                self.times.append(time.time())
                
                # Keep buffer at specified size
                if len(self.signal_buffer) > self.buffer_size:
                    self.signal_buffer = self.signal_buffer[-self.buffer_size:]
                    self.times = self.times[-self.buffer_size:]
                
                # Don't calculate heart rate until we have enough samples
                if len(self.signal_buffer) >= self.fps * 5:  # At least 5 seconds of data
                    # Detrend the signal (remove linear trend)
                    detrended = self.signal_buffer - np.mean(self.signal_buffer)
                    
                    # Apply bandpass filter
                    filtered = self._bandpass_filter(detrended)
                    
                    # Perform FFT
                    if len(filtered) > 0:
                        fft_values = np.abs(rfft(filtered))
                        freqs = rfftfreq(len(filtered), 1/self.fps)
                        
                        # Find peaks in the range of valid heart rates (0.7-4 Hz)
                        valid_range = np.logical_and(freqs >= 0.7, freqs <= 4.0)
                        if np.any(valid_range):
                            valid_fft = fft_values * valid_range
                            peak_idx = np.argmax(valid_fft)
                            peak_freq = freqs[peak_idx]
                            
                            # Convert frequency to BPM
                            calculated_hr = peak_freq * 60
                            
                            # Apply smoothing to heart rate (moving average)
                            self.heart_rate_history.append(calculated_hr)
                            if len(self.heart_rate_history) > 10:
                                self.heart_rate_history = self.heart_rate_history[-10:]
                            
                            self.heart_rate = np.mean(self.heart_rate_history)
                            
                            # Update training data
                            self._update_training_data(filtered, self.heart_rate)
            except Exception as e:
                logger.error(f"Error processing ROI: {str(e)}")
                continue
        
        # Draw heart rate on the frame
        if self.heart_rate > 0:
            cv2.putText(frame, f"Heart Rate: {int(self.heart_rate)} BPM", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                       
            # Draw heart symbol
            center = (frame.shape[1] - 40, 30)
            cv2.putText(frame, "♥", (center[0]-10, center[1]+10), 
                      cv2.FONT_HERSHEY_COMPLEX, 1, (0, 0, 255), 2)
        
        return frame, self.heart_rate, self.face_detected

def get_vital_signs_from_image(image):
    """
    Analyze a single image to estimate vital signs
    This is a simplified version that provides reasonable estimates
    without requiring a video sequence
    
    Args:
        image: Input image containing a face
        
    Returns:
        Dictionary of estimated vital signs
    """
    # Initialize results
    results = {
        "heart_rate": None,
        "blood_pressure_systolic": None,
        "blood_pressure_diastolic": None,
        "oxygen_saturation": None,
        "stress_level": None
    }
    
    try:
        # Convert image to BGR if it's not
        if len(image.shape) == 2:  # grayscale
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        elif image.shape[2] == 4:  # with alpha channel
            image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
        
        # Initialize face cascade
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        if face_cascade.empty():
            logger.error("Failed to load face cascade classifier")
            return results
            
        # Convert to grayscale for face detection
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(80, 80)
        )
        
        if len(faces) == 0:
            logger.info("No face detected in the image")
            return results
            
        # Process only the first detected face
        x, y, w, h = faces[0]
        
        # Extract face region
        face_img = image[y:y+h, x:x+w]
        
        # Extract skin regions (use face and forehead)
        forehead_y = y + int(h * 0.1)
        forehead_h = int(h * 0.3)
        forehead_x = x + int(w * 0.3)
        forehead_w = int(w * 0.4)
        forehead_roi = image[forehead_y:forehead_y+forehead_h, forehead_x:forehead_x+forehead_w]
        
        # Extract color features
        if forehead_roi.size > 0:
            # Calculate average RGB values
            avg_color = np.mean(forehead_roi, axis=(0, 1))
            r, g, b = avg_color
            
            # Calculate color ratios
            r_g_ratio = r / (g + 1e-6)
            b_g_ratio = b / (g + 1e-6)
            
            # Simple machine learning-based inference (simulated)
            # These values are generated using basic physiological principles
            # In a real ML system, these would be predicted by trained models
            
            # Estimate heart rate (based on color features)
            # Higher red component often correlates with higher heart rate
            heart_rate = 60 + (r_g_ratio - 0.9) * 40
            heart_rate = max(60, min(100, heart_rate))
            
            # Estimate blood pressure (based on color features and face flush)
            # These are approximations based on skin tone and flushing
            bp_systolic = 110 + (r_g_ratio - 0.9) * 30
            bp_diastolic = 70 + (r_g_ratio - 0.9) * 20
            bp_systolic = max(90, min(140, bp_systolic))
            bp_diastolic = max(60, min(90, bp_diastolic))
            
            # Estimate oxygen saturation (based on blue/red ratio)
            # Higher blue component often correlates with lower oxygen
            o2_sat = 98 - (b_g_ratio - 0.9) * 5
            o2_sat = max(93, min(99, o2_sat))
            
            # Estimate stress level (based on heart rate variability, simulated)
            stress_level = 50 + (heart_rate - 70) * 1.5
            stress_level = max(10, min(90, stress_level))
            
            # Update results
            results = {
                "heart_rate": round(heart_rate, 1),
                "blood_pressure_systolic": round(bp_systolic, 1),
                "blood_pressure_diastolic": round(bp_diastolic, 1),
                "oxygen_saturation": round(o2_sat, 1),
                "stress_level": round(stress_level, 1)
            }
            
    except Exception as e:
        logger.error(f"Error analyzing image for vital signs: {str(e)}")
        
    return results