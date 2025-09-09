document.addEventListener('DOMContentLoaded', function() {
    console.log('Integrations script loaded');
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

    // Health Connect button handler
    const healthConnectBtn = document.getElementById('health-connect-btn');
    console.log('Health Connect button:', healthConnectBtn);
    if (healthConnectBtn) {
        healthConnectBtn.addEventListener('click', function() {
            console.log('Health Connect button clicked');
            const link = document.createElement('a');
            link.href = '/static/apk/hc_gateway.apk';
            link.download = 'hc_gateway.apk';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            console.log('APK download triggered');
        });
    } else {
        console.log('Health Connect button not found');
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