document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded');
    const connectBtn = document.getElementById('garmin-connect-btn');
    console.log('Connect button:', connectBtn);
    if (connectBtn) {
        connectBtn.addEventListener('click', function() {
            console.log('Connect button clicked');
            toggleGarminModal();
        });
    } else {
        console.log('Connect button not found');
    }

    // Modal toggle function
    window.toggleGarminModal = function() {
        console.log('toggleGarminModal called');
        const modal = document.getElementById('garmin-modal');
        console.log('Modal element:', modal);
        if (modal) {
            modal.classList.toggle('hidden');
            console.log('Hidden class toggled');
        } else {
            console.log('Modal not found');
        }
    };

    // Close modal when clicking outside
    const modal = document.getElementById('garmin-modal');
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                modal.classList.add('hidden');
                console.log('Modal closed by outside click');
            }
        });
    } else {
        console.log('Modal not found on DOM load');
    }
});