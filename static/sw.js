// Service Worker Version
const VERSION = '1.0.0';
const CACHE_NAME = `flexingg-cache-${VERSION}`;

// Debug mode
const DEBUG = true;
function log(...args) {
    if (DEBUG) {
        console.log('[ServiceWorker]', ...args);
    }
}

// Assets that need to be available offline
const ASSETS_TO_CACHE = [
    '/',
    '/?source=pwa',
    '/manifest.json',
    '/static/manifest.json',
    '/static/icons/icon.png',
    '/static/icons/shortcuts/read_icon.png',
    '/static/icons/shortcuts/pray_icon.png',
    '/static/screenshots/home.png',
    '/static/css/styles.css',
    'https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js',
    'https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css'
];

// Install event - cache static assets
self.addEventListener('install', event => {
    log('Installing...');
    
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                log('Caching app shell and static assets');
                return cache.addAll(ASSETS_TO_CACHE);
            })
            .then(() => {
                log('Skip waiting on install');
                return self.skipWaiting();
            })
            .catch(error => {
                log('Error caching static assets:', error);
            })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    log('Activating...');
    
    event.waitUntil(
        Promise.all([
            // Clean up old caches
            caches.keys().then(cacheNames => {
                return Promise.all(
                    cacheNames.map(cacheName => {
                        if (cacheName !== CACHE_NAME) {
                            log('Deleting old cache:', cacheName);
                            return caches.delete(cacheName);
                        }
                    })
                );
            }),
            // Take control of all clients
            self.clients.claim().then(() => {
                log('Service Worker is now controlling all clients');
            })
        ])
    );
});

// Fetch event - network first with cache fallback
self.addEventListener('fetch', event => {
    log('Fetch event for:', event.request.url);
    
    // Handle navigation requests
    if (event.request.mode === 'navigate') {
        event.respondWith(
            fetch(event.request)
                .catch(() => {
                    log('Navigation fetch failed, falling back to cache');
                    return caches.match('/');
                })
        );
        return;
    }

    // Handle static asset requests
    if (event.request.url.includes('/static/')) {
        event.respondWith(
            caches.match(event.request)
                .then(cachedResponse => {
                    if (cachedResponse) {
                        log('Serving from cache:', event.request.url);
                        return cachedResponse;
                    }
                    
                    return fetch(event.request)
                        .then(response => {
                            // Cache successful responses
                            if (response.ok) {
                                const responseToCache = response.clone();
                                caches.open(CACHE_NAME)
                                    .then(cache => {
                                        cache.put(event.request, responseToCache);
                                        log('Cached new resource:', event.request.url);
                                    });
                            }
                            return response;
                        })
                        .catch(error => {
                            log('Fetch failed:', error);
                            throw error;
                        });
                })
        );
        return;
    }

    // Default fetch behavior
    event.respondWith(
        fetch(event.request)
            .catch(() => {
                return caches.match(event.request);
            })
    );
});

// Handle push notifications
self.addEventListener('push', event => {
    log('Push notification received');
    
    const options = {
        body: event.data.text(),
        icon: '/static/icons/icon-192x192.png',
        badge: '/static/icons/icon-96x96.png',
        data: {
            dateOfArrival: Date.now(),
            primaryKey: '1'
        },
        actions: [
            {
                action: 'explore',
                title: 'Open Flexin.gg',
                icon: '/static/icons/icon-faith.svg'
            }
        ]
    };

    event.waitUntil(
        self.registration.showNotification('Flexin.gg', options)
    );
});

// Handle notification clicks
self.addEventListener('notificationclick', event => {
    log('Notification clicked');
    
    event.notification.close();

    if (event.action === 'explore') {
        event.waitUntil(
            clients.openWindow('/')
        );
    }
});
