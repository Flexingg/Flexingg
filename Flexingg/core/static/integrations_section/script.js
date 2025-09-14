document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded');
    const garminConnectBtn = document.getElementById('garmin-connect-btn');
    console.log('Garmin connect button:', garminConnectBtn);
    if (garminConnectBtn) {
        garminConnectBtn.addEventListener('click', function() {
            console.log('Garmin connect button clicked');
            toggleGarminModal();
        });
    } else {
        console.log('Garmin connect button not found');
    }

    const liftosaurConnectBtn = document.getElementById('liftosaur-connect-btn');
    console.log('Liftosaur connect button:', liftosaurConnectBtn);
    if (liftosaurConnectBtn) {
        liftosaurConnectBtn.addEventListener('click', function() {
            console.log('Liftosaur connect button clicked');
            toggleLiftosaurModal();
        });
    } else {
        console.log('Liftosaur connect button not found');
    }

    // Modal toggle function for Garmin
    window.toggleGarminModal = function() {
        console.log('toggleGarminModal called');
        const modal = document.getElementById('garmin-modal');
        console.log('Garmin modal element:', modal);
        if (modal) {
            modal.classList.toggle('hidden');
            console.log('Garmin hidden class toggled');
        } else {
            console.log('Garmin modal not found');
        }
    };

    // Modal toggle function for Liftosaur
    window.toggleLiftosaurModal = function() {
        console.log('toggleLiftosaurModal called');
        const modal = document.getElementById('liftosaur-modal');
        console.log('Liftosaur modal element:', modal);
        if (modal) {
            modal.classList.toggle('hidden');
            console.log('Liftosaur hidden class toggled');
        } else {
            console.log('Liftosaur modal not found');
        }
    };

    // Close modals when clicking outside
    const garminModal = document.getElementById('garmin-modal');
    if (garminModal) {
        garminModal.addEventListener('click', function(e) {
            if (e.target === garminModal) {
                garminModal.classList.add('hidden');
                console.log('Garmin modal closed by outside click');
            }
        });
    } else {
        console.log('Garmin modal not found on DOM load');
    }

    const liftosaurModal = document.getElementById('liftosaur-modal');
    if (liftosaurModal) {
        liftosaurModal.addEventListener('click', function(e) {
            if (e.target === liftosaurModal) {
                liftosaurModal.classList.add('hidden');
                console.log('Liftosaur modal closed by outside click');
            }
        });
    } else {
        console.log('Liftosaur modal not found on DOM load');
    }
});