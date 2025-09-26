// Service Worker - Flexin.gg (stabilized)

// Versioned cache names
const CACHE_VERSION = 'v2025-09-25-01';
const APP_SHELL_CACHE = `flexingg-app-shell-${CACHE_VERSION}`;
const RUNTIME_CACHE_STATIC = `flexingg-runtime-static-${CACHE_VERSION}`;
const RUNTIME_CACHE_API = `flexingg-runtime-api-${CACHE_VERSION}`;

// Debug mode
const DEBUG = true;
function log(...args) {
    if (DEBUG) {
        console.log('[ServiceWorker]', ...args);
    }
}

// Assets that need to be available offline (app shell)
const ASSETS_TO_CACHE = [
    '/',
    '/offline.html',
    '/manifest.json',
    '/static/app/manifest.json',
    '/static/app/favicon.ico',
    '/static/app/icons/icon-192.png',
    '/static/app/icons/icon-512.png',
    '/static/app/sw.js'
];

// Install - cache app shell
self.addEventListener('install', event => {
    log('Installing service worker, caching app shell...');
    event.waitUntil(
        caches.open(APP_SHELL_CACHE)
            .then(cache => cache.addAll(ASSETS_TO_CACHE))
            .catch(err => log('Failed to cache app shell:', err))
    );
    // Activate new SW as soon as it's finished installing
    self.skipWaiting();
});

// Activate - clean up old caches and enable navigation preload
self.addEventListener('activate', event => {
    log('Activating service worker...', CACHE_VERSION);
    event.waitUntil((async () => {
        // Enable navigation preload if supported
        if (self.registration && self.registration.navigationPreload) {
            try {
                await self.registration.navigationPreload.enable();
                log('Navigation preload enabled');
            } catch (err) {
                log('Navigation preload enable failed:', err);
            }
        }

        // Claim clients so the SW starts controlling pages immediately
        self.clients && self.clients.claim && self.clients.claim();

        // Delete old caches not matching the current version
        const cacheNames = await caches.keys();
        await Promise.all(
            cacheNames.map(name => {
                if (![APP_SHELL_CACHE, RUNTIME_CACHE_STATIC, RUNTIME_CACHE_API].includes(name)) {
                    log('Deleting old cache:', name);
                    return caches.delete(name);
                }
            })
        );
    })());
});

// Helper: trim cache to a max item count (simple LRU-ish)
async function trimCache(cacheName, maxItems = 100) {
    const cache = await caches.open(cacheName);
    const keys = await cache.keys();
    if (keys.length > maxItems) {
        for (let i = 0; i < keys.length - maxItems; i++) {
            await cache.delete(keys[i]);
        }
    }
}

// Fetch - routing strategies
self.addEventListener('fetch', event => {
    const request = event.request;
    const url = new URL(request.url);

    // Bypass SW for non-GET requests or for deliberately excluded endpoints
    const isGet = request.method === 'GET';
    const isApi = url.pathname.startsWith('/healthconnect/') ||
                  url.pathname.startsWith('/garminconnect/') ||
                  url.pathname.startsWith('/liftosaur/') ||
                  url.pathname.startsWith('/api/') ||
                  url.pathname.startsWith('/auth/');

    // Always let navigation preload handle initial navigation where possible
    if (!isGet || isApi) {
        // Network-only for non-GET and critical API/auth endpoints
        event.respondWith(fetch(request).catch(() => caches.match('/offline.html')));
        return;
    }

    // Handle navigation requests (pages)
    if (request.mode === 'navigate') {
        event.respondWith((async () => {
            // Try preloadResponse first (fast), then network, then cache fallback
            try {
                const preloadResponse = await event.preloadResponse;
                if (preloadResponse) {
                    log('Using preload response for navigation:', url.pathname);
                    return preloadResponse;
                }

                const networkResponse = await fetch(request);
                // Optionally cache the navigation response in app-shell cache
                if (networkResponse && networkResponse.ok) {
                    const cache = await caches.open(APP_SHELL_CACHE);
                    cache.put(request, networkResponse.clone()).catch(err => log('Cache put failed:', err));
                }
                return networkResponse;
            } catch (err) {
                log('Navigation fetch failed, serving offline page:', err);
                const cache = await caches.open(APP_SHELL_CACHE);
                const cached = await cache.match('/offline.html');
                return cached || (await caches.match('/')) || new Response('Offline', { status: 503, statusText: 'Offline' });
            }
        })());
        return;
    }

    // Static assets (under /static/) => stale-while-revalidate
    if (request.url.includes('/static/')) {
        event.respondWith((async () => {
            const cache = await caches.open(RUNTIME_CACHE_STATIC);
            const cachedResponse = await cache.match(request);
            const networkFetch = fetch(request)
                .then(response => {
                    if (response && response.ok) {
                        cache.put(request, response.clone()).catch(err => log('Failed to put static asset into cache:', err));
                        trimCache(RUNTIME_CACHE_STATIC, 200);
                    }
                    return response;
                })
                .catch(err => {
                    log('Network fetch for static asset failed:', err);
                    return null;
                });

            // Serve cached if available, otherwise wait for network
            return cachedResponse || networkFetch;
        })());
        return;
    }

    // API / dynamic GETs => network-first with cache fallback
    event.respondWith((async () => {
        try {
            const response = await fetch(request);
            if (response && response.ok) {
                const cache = await caches.open(RUNTIME_CACHE_API);
                cache.put(request, response.clone()).catch(err => log('Failed to cache API response:', err));
                trimCache(RUNTIME_CACHE_API, 100);
            }
            return response;
        } catch (err) {
            log('Network failed for dynamic request, attempting cache:', request.url, err);
            const cache = await caches.open(RUNTIME_CACHE_API);
            const cached = await cache.match(request);
            return cached || (await caches.match('/offline.html')) || new Response('Offline', { status: 503, statusText: 'Offline' });
        }
    })());
});

// Push notifications
self.addEventListener('push', event => {
    log('Push event received');
    let payload = {};
    try {
        payload = event.data ? event.data.json() : { title: 'Flexin.gg', body: 'You have a notification' };
    } catch (err) {
        // event.data.text() fallback if not JSON
        try {
            payload = event.data ? { title: 'Flexin.gg', body: event.data.text() } : { title: 'Flexin.gg', body: 'You have a notification' };
        } catch (e) {
            payload = { title: 'Flexin.gg', body: 'You have a notification' };
        }
    }

    const title = payload.title || 'Flexin.gg';
    const options = {
        body: payload.body || '',
        icon: payload.icon || '/static/app/icons/icon-192.png',
        badge: payload.badge || '/static/app/icons/icon-96.png',
        data: payload.data || { dateOfArrival: Date.now() },
        actions: payload.actions || []
    };

    event.waitUntil(self.registration.showNotification(title, options));
});

// Notification click handling
self.addEventListener('notificationclick', event => {
    log('Notification clicked', event.notification);
    event.notification.close();

    const urlToOpen = (event.notification && event.notification.data && event.notification.data.url) ? event.notification.data.url : '/';
    event.waitUntil(clients.matchAll({ type: 'window', includeUncontrolled: true }).then(windowClients => {
        // Try to focus an existing client
        for (let i = 0; i < windowClients.length; i++) {
            const client = windowClients[i];
            if (client.url === urlToOpen && 'focus' in client) {
                return client.focus();
            }
        }
        // Otherwise open a new window/tab
        if (clients.openWindow) {
            return clients.openWindow(urlToOpen);
        }
    }));
});
