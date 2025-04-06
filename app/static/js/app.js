function flashMessage(message, category = 'info') {
    // Make sure DOM is loaded before trying to find elements
    const domReady = function(callback) {
        if (document.readyState === 'complete' || document.readyState === 'interactive') {
            setTimeout(callback, 1);
        } else {
            document.addEventListener('DOMContentLoaded', callback);
        }
    };

    domReady(function() {
        let flashContainer = document.getElementById('flash-messages');
        if (!flashContainer) {
            flashContainer = document.createElement('div');
            flashContainer.id = 'flash-messages';
            const mainContent = document.querySelector('.main-content');
            if (mainContent) {
                // Insert at the beginning of main-content
                mainContent.insertBefore(flashContainer, mainContent.firstChild);
            } else {
                // Fallback to body if main-content doesn't exist yet
                document.body.insertBefore(flashContainer, document.body.firstChild);
            }
        }

        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${category} alert-dismissible fade show`;
        alertDiv.role = 'alert';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;

        // Add to the container
        flashContainer.appendChild(alertDiv);

        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            alertDiv.classList.remove('show');
            setTimeout(() => alertDiv.remove(), 150);
        }, 5000);
    });
}