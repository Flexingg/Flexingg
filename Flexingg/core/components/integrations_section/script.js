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

    console.log('About to check Health Connect button');

    // Health Connect button handler
    const healthConnectBtn = document.getElementById('health-connect-btn');
    console.log('Health Connect button:', healthConnectBtn);
    if (healthConnectBtn) {
        healthConnectBtn.addEventListener('click', function() {
            console.log('Health Connect button clicked');
            toggleHCModal();
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
            // Prefer explicit show/hide to avoid conflicts with utility classes or duplicate definitions
            try {
                const isHiddenByClass = modal.classList.contains('hidden');
                const computed = getComputedStyle(modal);
                const isHiddenByStyle = computed.display === 'none' || computed.visibility === 'hidden' || computed.opacity === '0';
                if (isHiddenByClass || isHiddenByStyle) {
                    modal.classList.remove('hidden');
                    modal.style.display = 'flex';
                    // reset any inline hiding styles that may have been applied elsewhere
                    modal.style.visibility = '';
                    modal.style.opacity = '';
                    modal.style.pointerEvents = '';
                    console.log('Modal shown (removed hidden and set display:flex)');
                } else {
                    modal.classList.add('hidden');
                    modal.style.display = 'none';
                    console.log('Modal hidden (added hidden and set display:none)');
                }
            } catch (err) {
                // Fallback: just toggle class if computed style access fails
                modal.classList.toggle('hidden');
                console.log('Hidden class toggled (fallback)', err);
            }
        } else {
            console.log('Modal not found');
        }
    };

    // Close modal when clicking outside
    const modal = document.getElementById('garmin-modal');
    console.log('Modal inside event listener:', modal);
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

    // Health Connect modal toggle
    window.toggleHCModal = function() {
        console.log('toggleHCModal called');
        const modal = document.getElementById('hc-modal');
        if (modal) {
            modal.classList.toggle('hidden');
        } else {
            console.log('HC modal not found');
        }
    };

    // Close HC modal when clicking outside
    const hcModal = document.getElementById('hc-modal');
    if (hcModal) {
        hcModal.addEventListener('click', function(e) {
            if (e.target === hcModal) {
                hcModal.classList.add('hidden');
            }
        });
    }
});
