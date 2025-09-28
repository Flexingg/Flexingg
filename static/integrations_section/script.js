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

    // Modal toggle function
    window.toggleGarminModal = function() {
        console.log('toggleGarminModal called');
        const modal = document.getElementById('garmin-modal');
        console.log('Modal element:', modal);
        if (modal) {
            try {
                const isHiddenByClass = modal.classList.contains('hidden');
                const computed = getComputedStyle(modal);
                const isHiddenByStyle = computed.display === 'none' || computed.visibility === 'hidden' || computed.opacity === '0';
                if (isHiddenByClass || isHiddenByStyle) {
                    modal.classList.remove('hidden');
                    modal.style.display = 'flex';
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
                modal.classList.toggle('hidden');
                console.log('Hidden class toggled (fallback)', err);
            }
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