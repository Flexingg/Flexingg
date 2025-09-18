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

const VERSION = '1.0.2';
// Assets that need to be available offline
const ASSETS_TO_CACHE = [
    '/',
    '/offline.html',
    '/manifest.json',
    '/static/app/manifest.json',
    '/static/app/favicon.ico',
    '/static/app/sw.js',
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
            .catch(error => {
                log('Error caching static assets:', error);
            })
    );

    // Force activation of new SW
    self.skipWaiting();
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
            })
        ])
    );
});

// Fetch event - network first with cache fallback
self.addEventListener('fetch', event => {
    // Bypass service worker for non-GET requests, AJAX (e.g., POST, XHR), and API endpoints
    const url = new URL(event.request.url);
    const isAjax = event.request.headers.has('X-Requested-With') || event.request.mode === 'cors' || event.request.destination === 'empty';
    const isApi = url.pathname.startsWith('/healthconnect/') || url.pathname.startsWith('/garminconnect/') || url.pathname.startsWith('/liftosaur/');
    if (event.request.method !== 'GET' || isAjax || isApi) {
        event.respondWith(fetch(event.request));
        return;
    }
    
    // Handle navigation requests
    if (event.request.mode === 'navigate') {
        event.respondWith(
            (async () => {
                try {
                    const response = await fetch(event.request);
                    if (response && response.status === 200) {
                        const responseToCache = response.clone();
                        const cache = await caches.open(CACHE_NAME);
                        await cache.put(event.request, responseToCache);
                        log('Cached navigation page:', event.request.url);
                    }
                    return response;
                } catch (error) {
                    log('Navigation fetch failed, serving offline page');
                    const cache = await caches.open(CACHE_NAME);
                    const cachedResponse = await cache.match('/offline.html');
                    return cachedResponse || await caches.match('/');
                }
            })()
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

    // Default fetch behavior for remaining GET requests
    event.respondWith(
        fetch(event.request)
            .then(response => {
                if (response && response.status === 200 && !isAjax && !isApi) {
                    const responseToCache = response.clone();
                    caches.open(CACHE_NAME).then(cache => {
                        cache.put(event.request, responseToCache);
                        log('Cached dynamic resource:', event.request.url);
                    });
                }
                return response;
            })
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
