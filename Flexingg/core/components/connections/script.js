document.addEventListener('DOMContentLoaded', function () {
    // Toast helper (uses global showToast if available, otherwise creates a simple toast)
    window.showToast = window.showToast || function (message, type = 'info', timeout = 3500) {
        if (window._globalShowToastCalled) return; // avoid spam in tests
        if (typeof window.__toastGlobal__ !== 'undefined' && window.__toastGlobal__.show) {
            window.__toastGlobal__.show(message, type);
            return;
        }
        // create simple toast element
        const containerId = 'connections-toast-container';
        let container = document.getElementById(containerId);
        if (!container) {
            container = document.createElement('div');
            container.id = containerId;
            container.style.position = 'fixed';
            container.style.right = '16px';
            container.style.bottom = '16px';
            container.style.zIndex = 9999;
            document.body.appendChild(container);
        }
        const toast = document.createElement('div');
        toast.className = 'pixel-border';
        toast.style.background = (type === 'error') ? '#2f1b1b' : '#1b1b1b';
        toast.style.color = '#fff';
        toast.style.padding = '10px 12px';
        toast.style.marginTop = '8px';
        toast.style.borderRadius = '6px';
        toast.style.boxShadow = '0 4px 8px rgba(0,0,0,0.4)';
        toast.textContent = message;
        container.appendChild(toast);
        setTimeout(() => {
            toast.style.transition = 'opacity 300ms';
            toast.style.opacity = '0';
            setTimeout(() => container.removeChild(toast), 300);
        }, timeout);
    };

    function postFormAjax(form, opts = {}) {
        const action = form.action || opts.action;
        const method = (form.method || opts.method || 'POST').toUpperCase();
        const formData = new FormData(form);
        // include CSRF token if present in form
        return fetch(action, {
            method,
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'same-origin'
        }).then(async (res) => {
            const contentType = res.headers.get('content-type') || '';
            if (contentType.includes('application/json')) {
                const json = await res.json();
                return { ok: res.ok, status: res.status, json };
            } else {
                const text = await res.text();
                return { ok: res.ok, status: res.status, text };
            }
        });
    }

    // Liftosaur import (one-time file upload)
    const liftImportForm = document.getElementById('liftosaur-import-form');
    if (liftImportForm) {
        liftImportForm.addEventListener('submit', function (e) {
            e.preventDefault();
            showToast('Uploading Liftosaur file...', 'info');
            postFormAjax(liftImportForm).then(result => {
                if (result.json && result.json.status === 'success') {
                    showToast(result.json.message || 'Liftosaur import successful', 'info');
                    // close modal and reload to update state
                    if (window.toggleLiftosaurModal) window.toggleLiftosaurModal();
                    setTimeout(() => location.reload(), 700);
                } else if (result.json && result.json.status === 'error') {
                    showToast(result.json.message || 'Import failed', 'error');
                } else if (result.ok) {
                    showToast('Import completed. Reloading...', 'info');
                    setTimeout(() => location.reload(), 700);
                } else {
                    showToast('Import failed. Please try again.', 'error');
                }
            }).catch(err => {
                console.error('Liftosaur import error', err);
                showToast('Import error occurred', 'error');
            });
        });
    }

    // Liftosaur token (continuous)
    const liftTokenForm = document.getElementById('liftosaur-token-form');
    if (liftTokenForm) {
        liftTokenForm.addEventListener('submit', function (e) {
            e.preventDefault();
            showToast('Saving Liftosaur token...', 'info');
            postFormAjax(liftTokenForm).then(result => {
                if (result.json && result.json.status === 'success') {
                    showToast(result.json.message || 'Liftosaur connected', 'info');
                    if (window.toggleLiftosaurAdvancedModal) window.toggleLiftosaurAdvancedModal();
                    setTimeout(() => location.reload(), 700);
                } else if (result.json && result.json.status === 'error') {
                    showToast(result.json.message || 'Failed to save token', 'error');
                } else if (result.ok) {
                    showToast('Token saved. Reloading...', 'info');
                    setTimeout(() => location.reload(), 700);
                } else {
                    showToast('Failed to save token', 'error');
                }
            }).catch(err => {
                console.error('Liftosaur token save error', err);
                showToast('Error saving Liftosaur token', 'error');
            });
        });
    }

    // Health Connect form (connect)
    const hcForm = document.querySelector('form[action*="healthconnect:connect"], form[action*="/healthconnect/connect"]') || document.querySelector('form[action*="healthconnect/connect/"]');
    if (hcForm) {
        hcForm.addEventListener('submit', function (e) {
            e.preventDefault();
            showToast('Connecting Health Connect...', 'info');
            postFormAjax(hcForm).then(result => {
                if (result.json && result.json.status === 'success') {
                    showToast(result.json.message || 'Health Connect connected', 'info');
                    if (window.toggleHCModal) window.toggleHCModal();
                    setTimeout(() => location.reload(), 700);
                } else if (result.json && result.json.status === 'error') {
                    showToast(result.json.message || 'Health Connect connection failed', 'error');
                } else if (result.ok) {
                    showToast('Connected. Reloading...', 'info');
                    setTimeout(() => location.reload(), 700);
                } else {
                    showToast('Connection failed', 'error');
                }
            }).catch(err => {
                console.error('Health Connect connect error', err);
                showToast('Connection error occurred', 'error');
            });
        });
    }

    // Garmin connect form
    const garminForm = document.querySelector('form[action*="garminconnect:connect_garmin"], form[action*="/garminconnect/connect/"], #garmin-modal form');
    if (garminForm) {
        garminForm.addEventListener('submit', function (e) {
            e.preventDefault();
            showToast('Linking Garmin...', 'info');
            postFormAjax(garminForm).then(result => {
                if (result.json && result.json.status === 'success') {
                    showToast(result.json.message || 'Garmin connected', 'info');
                    if (window.toggleGarminModal) window.toggleGarminModal();
                    setTimeout(() => location.reload(), 700);
                } else if (result.json && result.json.status === 'error') {
                    showToast(result.json.message || 'Garmin connection failed', 'error');
                } else if (result.ok) {
                    showToast('Connected. Reloading...', 'info');
                    setTimeout(() => location.reload(), 700);
                } else {
                    showToast('Connection failed', 'error');
                }
            }).catch(err => {
                console.error('Garmin connect error', err);
                showToast('Connection error occurred', 'error');
            });
        });
    }

    // Disconnect forms (generic handler)
    document.querySelectorAll('form[action*="disconnect"]').forEach(form => {
        form.addEventListener('submit', function (e) {
            // let native confirm run for destructive actions where applicable
            const confirmed = confirm('Are you sure you want to disconnect this service?');
            if (!confirmed) {
                e.preventDefault();
                return;
            }
            e.preventDefault();
            showToast('Disconnecting...', 'info');
            postFormAjax(form).then(result => {
                if (result.json && result.json.status === 'success') {
                    showToast(result.json.message || 'Disconnected', 'info');
                    setTimeout(() => location.reload(), 600);
                } else if (result.ok) {
                    showToast('Disconnected. Reloading...', 'info');
                    setTimeout(() => location.reload(), 600);
                } else {
                    showToast('Disconnect failed', 'error');
                }
            }).catch(err => {
                console.error('Disconnect error', err);
                showToast('Disconnect error occurred', 'error');
            });
        });
    });

    // Add delegated submit handler as a safety net (catches cases where inline submit bypasses JS binding)
    document.body.addEventListener('submit', function (e) {
        try {
            const form = e.target;
            if (!form || !form.id) return;
            if (form.id === 'liftosaur-token-form') {
                e.preventDefault();
                // Use existing helper to post via AJAX
                showToast('Saving Liftosaur token...', 'info');
                postFormAjax(form).then(result => {
                    if (result.json && result.json.status === 'success') {
                        showToast(result.json.message || 'Liftosaur connected', 'info');
                        if (window.toggleLiftosaurAdvancedModal) window.toggleLiftosaurAdvancedModal();
                        setTimeout(() => location.reload(), 700);
                    } else if (result.json && result.json.status === 'error') {
                        showToast(result.json.message || 'Failed to save token', 'error');
                    } else if (result.ok) {
                        showToast('Token saved. Reloading...', 'info');
                        setTimeout(() => location.reload(), 700);
                    } else {
                        showToast('Failed to save token', 'error');
                    }
                }).catch(err => {
                    console.error('Liftosaur token delegated submit error', err);
                    showToast('Error saving Liftosaur token', 'error');
                });
            }
        } catch (err) {
            console.error('Delegated submit handler error', err);
        }
    }, true);

    // Dropdown menu close behavior when clicking outside
    document.addEventListener('click', function (e) {
        const menu = document.getElementById('liftosaur-dropdown-menu');
        const trigger = document.getElementById('liftosaur-connect-dropdown');
        if (!menu || !trigger) return;
        if (menu.classList.contains('hidden')) return;
        if (trigger.contains(e.target) || menu.contains(e.target)) return;
        menu.classList.add('hidden');
    });

    // Info modal hook (if template uses showInfoForService it will call toggleInfoModal/show content)
    // Ensure toggle functions exist as no-op fallbacks
    window.toggleLiftosaurModal = window.toggleLiftosaurModal || function () {
        const m = document.getElementById('liftosaur-modal');
        if (m) m.classList.toggle('hidden');
    };
    window.toggleLiftosaurAdvancedModal = window.toggleLiftosaurAdvancedModal || function () {
        const m = document.getElementById('liftosaur-advanced-modal');
        if (m) m.classList.toggle('hidden');
    };
    window.toggleGarminModal = window.toggleGarminModal || function () {
        const m = document.getElementById('garmin-modal');
        if (m) m.classList.toggle('hidden');
    };
    window.toggleHCModal = window.toggleHCModal || function () {
        const m = document.getElementById('hc-modal');
        if (m) m.classList.toggle('hidden');
    };
});