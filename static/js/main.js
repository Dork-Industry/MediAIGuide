// Main JavaScript file for Medicine AI application

document.addEventListener('DOMContentLoaded', function() {
    // Initialize feather icons
    feather.replace();
    
    // Setup tooltips if Bootstrap's tooltip component is needed
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
    
    // Setup alerts to auto-dismiss after 5 seconds
    const alerts = document.querySelectorAll('.alert:not(.persistent)');
    alerts.forEach(alert => {
        setTimeout(() => {
            const closeButton = alert.querySelector('.btn-close');
            if (closeButton) {
                closeButton.click();
            } else {
                alert.classList.add('fade');
                setTimeout(() => {
                    alert.remove();
                }, 150);
            }
        }, 5000);
    });
    
    // Add active class to current nav item
    const currentLocation = window.location.pathname;
    const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentLocation) {
            link.classList.add('active');
        }
    });

    // Form validation enhancement
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
                
                // Add visual feedback for invalid fields
                const invalidFields = form.querySelectorAll(':invalid');
                invalidFields.forEach(field => {
                    // Create feedback message if it doesn't exist
                    let feedback = field.nextElementSibling;
                    if (!feedback || !feedback.classList.contains('invalid-feedback')) {
                        feedback = document.createElement('div');
                        feedback.classList.add('invalid-feedback');
                        field.parentNode.insertBefore(feedback, field.nextSibling);
                    }
                    
                    // Set feedback message based on validity state
                    if (field.validity.valueMissing) {
                        feedback.textContent = 'This field is required';
                    } else if (field.validity.typeMismatch) {
                        feedback.textContent = 'Please enter a valid format';
                    } else if (field.validity.tooShort) {
                        feedback.textContent = `Must be at least ${field.minLength} characters`;
                    } else {
                        feedback.textContent = 'Invalid input';
                    }
                    
                    field.classList.add('is-invalid');
                });
            }
        });
    });
});

// Function to format date to a readable format
function formatDate(dateString) {
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    return new Date(dateString).toLocaleDateString(undefined, options);
}

// Function to safely initialize any third-party components
function initializeComponents() {
    // This can be extended with additional component initializations
    if (document.querySelector('.chart-container') && typeof Chart !== 'undefined') {
        initializeCharts();
    }
}

// Function to handle session timeout
function setupSessionTimeoutWarning() {
    // If user is logged in, set a warning for session timeout
    if (document.querySelector('.navbar-nav .nav-link[href="/logout"]')) {
        const sessionTimeout = 30 * 60 * 1000; // 30 minutes
        const warningTime = 5 * 60 * 1000; // 5 minutes before timeout
        
        setTimeout(() => {
            // Show warning
            const warningDiv = document.createElement('div');
            warningDiv.classList.add('alert', 'alert-warning', 'alert-dismissible', 'fade', 'show', 'fixed-top', 'w-50', 'mx-auto', 'mt-3');
            warningDiv.innerHTML = `
                <strong>Warning:</strong> Your session will expire in 5 minutes. 
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                <div class="mt-2">
                    <button class="btn btn-sm btn-primary extend-session">Extend Session</button>
                </div>
            `;
            document.body.appendChild(warningDiv);
            
            // Add event listener to extend session button
            const extendButton = warningDiv.querySelector('.extend-session');
            if (extendButton) {
                extendButton.addEventListener('click', function() {
                    // Make a request to the server to extend the session
                    fetch('/ping', { method: 'GET' })
                        .then(() => {
                            warningDiv.remove();
                            setupSessionTimeoutWarning(); // Reset the timeout warning
                        });
                });
            }
        }, sessionTimeout - warningTime);
    }
}

// Call any initialization functions
initializeComponents();
setupSessionTimeoutWarning();
