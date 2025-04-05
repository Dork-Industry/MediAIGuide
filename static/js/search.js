// Search functionality specific JavaScript

document.addEventListener('DOMContentLoaded', function() {
    const searchForm = document.querySelector('form[action*="search"]');
    const searchInput = searchForm ? searchForm.querySelector('input[name="medicine_name"]') : null;
    
    // Add search suggestions if input exists
    if (searchInput) {
        // Focus the search input automatically on the home page
        if (window.location.pathname === '/' || window.location.pathname === '/home') {
            searchInput.focus();
        }
        
        // Add event listener for input to implement autocomplete in the future
        searchInput.addEventListener('input', function() {
            const query = this.value.trim();
            if (query.length >= 3) {
                // In a real implementation, this would fetch suggestions from the server
                // For now, we'll just log that this would happen
                console.log('Would fetch suggestions for:', query);
            }
        });
        
        // Allow Enter key to submit the form
        searchInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                searchForm.submit();
            }
        });
    }
    
    // Add loading state to search form on submit
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            // Validate input
            const searchValue = searchInput.value.trim();
            if (!searchValue) {
                e.preventDefault();
                // Add invalid class to input
                searchInput.classList.add('is-invalid');
                // Add feedback if it doesn't exist
                let feedback = searchInput.nextElementSibling;
                if (!feedback || !feedback.classList.contains('invalid-feedback')) {
                    feedback = document.createElement('div');
                    feedback.classList.add('invalid-feedback');
                    searchInput.parentNode.insertBefore(feedback, searchInput.nextSibling);
                }
                feedback.textContent = 'Please enter a medicine name';
                return;
            }
            
            // Show loading state
            const submitButton = this.querySelector('button[type="submit"]');
            if (submitButton) {
                const originalContent = submitButton.innerHTML;
                submitButton.disabled = true;
                submitButton.innerHTML = `
                    <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                    Searching...
                `;
                
                // Store original content to restore it after navigation
                submitButton.dataset.originalContent = originalContent;
            }
        });
    }
    
    // Implement collapsible sections in search results if they exist
    const collapsibleHeaders = document.querySelectorAll('.collapsible-header');
    collapsibleHeaders.forEach(header => {
        header.addEventListener('click', function() {
            const content = this.nextElementSibling;
            if (content && content.classList.contains('collapsible-content')) {
                content.classList.toggle('collapsed');
                this.classList.toggle('collapsed');
            }
        });
    });
    
    // Add copy functionality for dosage information
    const copyButtons = document.querySelectorAll('.copy-dosage');
    copyButtons.forEach(button => {
        button.addEventListener('click', function() {
            const dosageText = this.dataset.dosage;
            if (dosageText) {
                navigator.clipboard.writeText(dosageText).then(() => {
                    // Show success message
                    const originalText = this.textContent;
                    this.textContent = 'Copied!';
                    setTimeout(() => {
                        this.textContent = originalText;
                    }, 2000);
                });
            }
        });
    });
    
    // Implement "scroll to top" functionality on search results page
    if (document.querySelector('.search-results')) {
        // Create the button if it doesn't exist
        let scrollButton = document.querySelector('.scroll-to-top');
        if (!scrollButton) {
            scrollButton = document.createElement('button');
            scrollButton.classList.add('scroll-to-top', 'btn', 'btn-primary', 'rounded-circle');
            scrollButton.innerHTML = '<i data-feather="chevron-up"></i>';
            document.body.appendChild(scrollButton);
            
            // Initialize the feather icon
            feather.replace();
        }
        
        // Show/hide the button based on scroll position
        window.addEventListener('scroll', function() {
            if (window.pageYOffset > 300) {
                scrollButton.classList.add('show');
            } else {
                scrollButton.classList.remove('show');
            }
        });
        
        // Scroll to top when clicked
        scrollButton.addEventListener('click', function() {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });
    }
});

// Function to handle AJAX search if needed
function performAjaxSearch(query) {
    // This would be used for API-based searching
    return fetch('/api/search', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ medicine_name: query })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Search failed');
        }
        return response.json();
    })
    .then(data => {
        // Process the returned data
        return data;
    })
    .catch(error => {
        console.error('Error performing search:', error);
        return {
            error: true,
            message: error.message
        };
    });
}
