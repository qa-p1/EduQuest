function flashMessage(message, category = 'info') {
    let flashContainer = document.getElementById('flash-messages');
    if (!flashContainer) {
        flashContainer = document.createElement('div');
        flashContainer.id = 'flash-messages';
        document.body.insertBefore(flashContainer, document.body.firstChild);
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

    setTimeout(() => {
        alertDiv.classList.remove('show');
        setTimeout(() => alertDiv.remove(), 150);
    }, 5000);
}
