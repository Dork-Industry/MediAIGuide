/**
 * Performance optimization script for Medicine AI app
 */

// Lazy load images to improve initial page load
document.addEventListener('DOMContentLoaded', function() {
    // Lazy load images
    const lazyImages = document.querySelectorAll('img[data-src]');
    if (lazyImages.length > 0) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.getAttribute('data-src');
                    img.removeAttribute('data-src');
                    observer.unobserve(img);
                }
            });
        });
        
        lazyImages.forEach(img => {
            imageObserver.observe(img);
        });
    }
    
    // Cache common DOM elements for faster access
    if (window.MedicineAI === undefined) {
        window.MedicineAI = {};
    }
    
    // Initialize caching for various page types
    initPageSpecificCaching();
});

// Cache DOM elements based on page type
function initPageSpecificCaching() {
    const pageIdentifiers = {
        'health-scanner': document.querySelector('.scan-option'),
        'realtime-heart-rate': document.getElementById('video'),
        'user-dashboard': document.querySelector('.dashboard-cards'),
        'doctor-dashboard': document.querySelector('.doctor-patients'),
        'admin-dashboard': document.querySelector('.admin-controls')
    };
    
    // Determine current page
    let currentPage = null;
    for (const [page, element] of Object.entries(pageIdentifiers)) {
        if (element) {
            currentPage = page;
            break;
        }
    }
    
    // Cache elements specific to that page
    if (currentPage === 'health-scanner') {
        cacheHealthScannerElements();
    } else if (currentPage === 'realtime-heart-rate') {
        optimizeHeartRateMonitor();
    }
}

// Cache health scanner page elements
function cacheHealthScannerElements() {
    if (document.querySelector('.scan-option')) {
        const scanOptions = document.querySelectorAll('.scan-option');
        const scanDescriptions = {
            face: document.querySelector('.scan-description-face'),
            tongue: document.querySelector('.scan-description-tongue'),
            eye: document.querySelector('.scan-description-eye'),
            skin: document.querySelector('.scan-description-skin')
        };
        
        // Optimize scan type selection to avoid DOM reflows
        scanOptions.forEach(option => {
            option.addEventListener('click', function(e) {
                // Prevent event bubbling and default action
                e.stopPropagation();
                
                // Get scan type from the clicked option
                const scanType = this.querySelector('input').value;
                
                // Update UI without causing multiple reflows
                requestAnimationFrame(() => {
                    // Update active state
                    scanOptions.forEach(opt => opt.classList.remove('active'));
                    this.classList.add('active');
                    
                    // Show corresponding description
                    Object.values(scanDescriptions).forEach(desc => desc.style.display = 'none');
                    scanDescriptions[scanType].style.display = 'block';
                });
            });
        });
    }
}

// Optimize real-time heart rate monitor
function optimizeHeartRateMonitor() {
    // Throttle the frame processing to reduce CPU usage
    if (window.MedicineAI.heartRateThrottled) return;
    
    // Add a throttling mechanism to the original processVideoFrame function
    const originalProcessFrame = window.processVideoFrame;
    if (originalProcessFrame && typeof originalProcessFrame === 'function') {
        window.processVideoFrame = function() {
            if (!window.MedicineAI.throttleTimer) {
                window.MedicineAI.throttleTimer = setTimeout(() => {
                    window.MedicineAI.throttleTimer = null;
                    originalProcessFrame();
                }, 33); // ~30fps
            }
        };
    }
    
    // Reduce the quality and size of frames sent to the server
    if (window.sendFrameToServer && typeof window.sendFrameToServer === 'function') {
        const originalSendFrame = window.sendFrameToServer;
        window.sendFrameToServer = function() {
            // Reduce frame processing frequency
            if (!window.MedicineAI.lastFrameTime || 
                Date.now() - window.MedicineAI.lastFrameTime > 1000) { // Process every 1 second
                window.MedicineAI.lastFrameTime = Date.now();
                originalSendFrame();
            }
        };
    }
    
    window.MedicineAI.heartRateThrottled = true;
}

// Debounce function to limit how often a function can be called
function debounce(func, wait) {
    let timeout;
    return function() {
        const context = this;
        const args = arguments;
        clearTimeout(timeout);
        timeout = setTimeout(() => {
            func.apply(context, args);
        }, wait);
    };
}

// Add click debounce to all buttons to prevent accidental double clicks
document.addEventListener('DOMContentLoaded', function() {
    const buttons = document.querySelectorAll('button, .btn');
    buttons.forEach(button => {
        const originalClick = button.onclick;
        if (originalClick) {
            button.onclick = debounce(originalClick, 300);
        }
    });
});
