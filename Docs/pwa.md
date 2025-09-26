# Progressive Web App (PWA) Plan — Flexin.gg

This document captures a pragmatic, prioritized plan to ensure the Flexin.gg web app uses modern PWA capabilities and provides a smooth, reliable install experience for users. It intentionally focuses on useful features (installability, offline resilience, push, background sync, platform packaging) and avoids adding unnecessary complexity.

## Quick audit (current state)
- Manifest: [`static/app/manifest.json`](static/app/manifest.json:1) — present, contains shortcuts, icons, protocol handler. Needs improvement (icons, id, short_name length, screenshots).
- Service worker: [`static/app/sw.js`](static/app/sw.js:1) — present and functional but has issues:
  - Duplicate VERSION constant declarations.
  - No `self.clients.claim()` in activate, no Navigation Preload setup.
  - Broad caching strategy (network-first for navigation, cache-first for /static/) but needs better cache versioning, separate runtime caches, and graceful fallbacks.
  - Push handler references icons that may not exist at those paths.
- Offline asset: `/offline.html` referenced in sw but not currently audited. Treat as required asset: [`static/app/offline.html`](static/app/offline.html:1) (create if missing).
- Icons and platform packaging assets exist under [`static/app/icons/`](static/app/icons/:1) but do not include a full set of maskable/adaptive icons or properly-sized manifest entries.

## User-provided assets and items (things you must provide)

Below is a prioritized list of files, secrets, and external inputs the coding assistant cannot create for you. Once you provide these (placed at the paths below or give me the files), I can implement the remaining code changes, update the manifest, wire up server push, and finish packaging.

- App icons (provide PNGs + maskable/adaptive versions)
  - Place in: [`static/app/icons/`](static/app/icons/:1)
  - Recommended filenames & sizes:
    - `icon-48.png` — 48x48
    - `icon-72.png` — 72x72
    - `icon-96.png` — 96x96
    - `icon-144.png` — 144x144
    - `icon-192.png` — 192x192
    - `icon-512.png` — 512x512
  - Maskable/adaptive versions (PNG or SVG with safe area):
    - `icon-maskable-192.png` — 192x192 (purpose: maskable)
    - `icon-maskable-512.png` — 512x512 (purpose: maskable)
  - Adaptive icon layers (Android):
    - `adaptive-foreground.png` (512x512)
    - `adaptive-background.png` (512x512)

- Shortcut & platform icons used in manifest shortcuts
  - e.g., `flexingg_trophy.png`, `flexingg_weightlifting.png` (96x96 or 128x128) — place in [`static/app/icons/`](static/app/icons/:1)

- Store screenshots and promotional images
  - For Play Store / PWABuilder / TWA packaging: multiple screenshots at 16:9 and 9:16 aspect ratios (recommend 1080x1920, 1920x1080)
  - Place in a folder: `static/screenshots/` and name them `screenshot-1.png`, `screenshot-2.png`, etc.

- Privacy policy & marketing info
  - A publicly hosted Privacy Policy URL (required for Play Store and push consent best practices).
    - Make a placeholder html page if needed: `https://flexin.gg/privacy-policy.html`
  - Contact email to include in store listings and manifest metadata.
    - Should be set to 'support@flexin.gg'
  - Short app description and full description for store listings.
    - Short description: "Flex with your friends and compete in all health and fitness metrics you want to!"
    - Full description "Flexin.gg is a social fitness platform that lets you connect with friends, incentivizes tracking your health metrics and workouts, and compete in challenges across various categories. Whether you're into weightlifting, running, or general wellness, Flexin.gg has you covered with real-time leaderboards, personalized goals, and a supportive community. Join now and start flexing your progress!"

- VAPID keys for push notifications (security-sensitive)
  - Generate and keep the private key secret. Provide:
    - VAPID public key (string) — I can embed this client-side to subscribe.
    - VAPID private key — store securely on your server; do NOT commit to repo. Ensure user adds to .gitignore and store it in the enviromental variables. 
  - If you prefer, I can provide server-side code to accept keys and use them; you must generate keys and paste them into environment variables - yes I want this. 

- Domain & HTTPS
  - A production domain pointed to your hosting and an active HTTPS certificate (Let's Encrypt or other).
  - If you want the `manifest.json` `"id"` to be absolute, confirm the canonical production URL (e.g., `https://flexin.gg/`) so I can set it. It will be https://flexin.gg/

WE ARE NOT SHIPPING TO PLAY STORE / APP STORE / WINDOWS STORE YET, IGNORE FOR NOW
- Developer/Store accounts & credentials (for packaging)
  - Google Play developer account info / keystore for signing TWA (you keep keys secure).
  - Microsoft developer account and code signing certificate if you want MSIX packaging.
  - I will not handle private signing keys; provide signed artifacts or sign locally as instructed.
WE ARE NOT SHIPPING TO PLAY STORE / APP STORE / WINDOWS STORE YET, IGNORE FOR NOW

- Branding assets & copy decisions
  - Final short_name (≤ 12 chars) and display name you want in the manifest (`Flexingg`).
  - Any variant names for store listings. ('Flexin.gg' and 'Flexin')

What I will do once you provide the above
- Update [`static/app/manifest.json`](static/app/manifest.json:1) with the full icon matrix, maskable/adaptive entries, absolute `"id"`, and screenshots.
- Patch [`static/app/sw.js`](static/app/sw.js:1) to use robust caching, add navigation preload, `clients.claim()`, and separate runtime caches.
- Add client-side install handling (hook into `beforeinstallprompt`) and analytics hooks.
- Add server endpoints and wiring for push (expecting you to place VAPID secret in server config / environment variables).
- Create packaging scripts for TWA / PWABuilder (instructions for signing with your keys).

When you have these files and values ready, upload them to the repository at the suggested paths (or tell me where you placed them), then request that I implement the remaining code changes and I will switch to code mode and apply them.

## Goals (short)
1. Make installation frictionless and discoverable on Android, desktop, and Windows.
2. Provide reliable offline experience for key flows (home, gym, leaderboards, profile).
3. Enable robust push notifications and background sync for queued actions.
4. Maintain high Lighthouse scores with automation and CI checks.
5. Provide packaging paths for Play Store and Windows (TWA / PWABuilder).

## Prioritized action plan (developer-focused)
The tasks below are ordered for implementation. Each item references files to update or create.

1) Audit & quick fixes (low friction, immediate)
   - Remove duplicate constants and add `self.clients.claim()` and navigation preload setup to [`static/app/sw.js`](static/app/sw.js:1).
   - Ensure `/offline.html` exists and is cached by SW: [`static/app/offline.html`](static/app/offline.html:1).
   - Verify manifest icon paths referenced in [`static/app/manifest.json`](static/app/manifest.json:1) exist and add missing sizes (see detailed step below).

2) Manifest improvements
   - Ensure `short_name` ≤ 12 characters; consider `Flexin.gg` -> `Flexin` or `Flex.gg`.
   - Replace `"id": "flexingg-pwa"` with an absolute URL id (e.g., `https://flexin.gg/`) for predictable scope/updates.
   - Add a full icon matrix: 48, 72, 96, 128, 144, 152, 192, 256, 384, 512 with `purpose: "any maskable"` where appropriate.
   - Add `screenshots` for Play Store and Microsoft packaging.
   - Keep `display_override` (good), set `prefer_related_applications` only when you have native apps submitted.

   Files to update: [`static/app/manifest.json`](static/app/manifest.json:1)

3) Service Worker: Stabilize & modernize
   - Fix duplicate constants and use semantic `CACHE_VERSION` variable.
   - Add `self.skipWaiting()` on install and `self.clients.claim()` on activate.
   - Enable Navigation Preload (when supported) to improve first-load reliability for navigations.
   - Use separate caches:
     - APP_SHELL_CACHE (core shell, versioned)
     - RUNTIME_CACHE_STATIC (assets under /static/)
     - RUNTIME_CACHE_API (API responses)
   - Strategy recommendations:
     - Navigation: network-first with preload, fallback to cached `offline.html`.
     - Static assets: stale-while-revalidate.
     - API: network-first for freshness but fallback to cache for GETs; never cache authenticated/private responses.
   - Provide granular cache keys and limit entries using LRU or simple trimming.
   - Carefully exclude API endpoints that must never be cached (auth, sync endpoints).
   - Add a SW health check route that returns version metadata for debugging.

   Files to update: [`static/app/sw.js`](static/app/sw.js:1)

4) Offline UX
   - Create [`static/app/offline.html`](static/app/offline.html:1) with clear messaging and quick links to supported cached pages.
   - Implement in-app fallbacks: React/Alpine pages should detect offline and show cached content placeholders for critical widgets (profile, last leaderboard snapshot).
   - Pre-cache minimal JSON snapshots for leaderboards and profile to show something useful offline.

5) Installability & custom prompt
   - Implement client-side `beforeinstallprompt` handler to capture event, defer it, and show a well‑designed install CTA (e.g., “Install Flexin.gg — Add to Home screen”).
   - Only show the prompt when session conditions are met (engagement threshold: e.g., visited > 2 times or opened gym 3+ times).
   - Track analytics events: prompt_shown, prompt_accepted, prompt_dismissed, installed (tie to server-side or analytics system).
   - Ensure UX for desktop: add a visible “Install on PC” banner when `window.matchMedia('(display-mode: browser)').matches` + installability checks.

   Files to add/update: client JavaScript (where app bootstrap happens), and docs in [`Docs/pwa.md`](Docs/pwa.md:1).

6) Notifications & VAPID push
   - Generate VAPID keys and store keys in server config.
   - Implement subscription endpoint on server: POST /api/push/subscribe and DELETE /api/push/unsubscribe.
   - Persist subscriptions and send push messages via WebPush using your server (Django: use pywebpush or similar).
   - In SW, use push payload best practices: include title/body/icon/actions and fallback behavior when event.data is empty.
   - Provide graceful UX for permission requests — explain value before asking and avoid immediate prompts.

   Files to update/create: SW (`static/app/sw.js`:1), server endpoints (e.g., `Flexingg/core/views.py`:1 or a dedicated notifications app), server config for VAPID.

7) Background sync & periodic sync
   - Use Background Sync (one-off) to ensure writes (e.g., queued workouts or offline actions) are reliably sent when connectivity returns.
   - Implement Periodic Background Sync (where supported) for refreshing cached leaderboards or user stats.
   - Provide fallbacks for browsers that don't support these APIs.

   Files to update: SW and client sync logic (client JS + server endpoints).

8) Badging, Shortcuts, and Protocol handlers
   - Make use of Shortcuts in manifest (already present) and verify icon sizes for shortcuts.
   - Register protocol handlers in manifest (already present) and test in supported browsers.
   - Optionally support the Badging API for unread notifications/quests (progressive enhancement).

   Files to update: [`static/app/manifest.json`](static/app/manifest.json:1), client JS.

9) Packaging & Store distribution
   - Prepare for TWA using Bubblewrap (for Play Store).
   - Prepare PWABuilder export for MSIX/Windows packaging.
   - Add required store assets (screenshots, privacy policy, contact email).

   Artifacts: build scripts and packaging config in repository root (e.g., `packaging/`).

10) Testing & CI
   - Add Lighthouse CI or web.dev tests to CI pipeline to enforce performance/SEO/PWA scores.
   - Create automated checks that will fail the build on regressions (or add as a gating job).
   - Add manual QA checklist for install tests across Chrome Android, Edge, Safari (iOS), and Windows.

## Developer implementation notes (concrete)
- Service worker best-practices to implement:
  - Single source-of-truth `const CACHE_VERSION = 'v2025-09-24-01'`.
  - Install: cache app shell + critical assets; call `self.skipWaiting()`.
  - Activate: call `self.clients.claim()`, delete old caches.
  - Navigation preload: `if (self.registration.navigationPreload) { await self.registration.navigationPreload.enable(); }`.
  - Example navigation handler: network with preload fallback and offline.html when offline.
- Manifest:
  - Use `id` as absolute URL to ensure updates: `"id": "https://yourdomain.example/"`.
  - Example `icons` entry:
    - { "src": "/static/app/icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable" }
  - Keep `scope` restrictive if you want to limit PWA to app paths.
- Install flow:
  - Persist the `beforeinstallprompt` event (e.g., window.deferredInstallPrompt).
  - Expose UI button that calls `deferredInstallPrompt.prompt()` and logs result.
- Push:
  - Use VAPID: store public key in client config, subscribe with `applicationServerKey`.
  - Verify payload encryption and support for payload-less notifications.
- Background sync:
  - Use `registration.sync.register('sync-queued-workouts')` to retry failed POSTs.
  - On server, de-duplicate incoming data and validate timestamps.

## Files to change / create (actionable)
- Update: [`static/app/sw.js`](static/app/sw.js:1)
- Update: [`static/app/manifest.json`](static/app/manifest.json:1)
- Add: [`static/app/offline.html`](static/app/offline.html:1)
- Add/Update: client install-handling JS at app bootstrap (add file or modify existing entry point)
- Add: server endpoints for push subscription and health/version metadata (e.g., `Flexingg/core/views.py`:1 or a new `notifications` module)
- Add: packaging configs and scripts (e.g., `packaging/`)

## Metrics & rollout
- Track these events: pwa_prompt_shown, pwa_prompt_accepted, pwa_installed, push_subscription_created, push_permission_denied, offline_action_synced, sw_update_detected.
- Start with a beta rollout (feature-flag PWA changes) and monitor errors/analytics.
- Maintain an in-app “What’s new” message when SW updates major versions.

## Timeline (example)
- Week 0: Audit + quick SW fixes + offline.html (Items 1, 4)
- Week 1: Manifest improvements + install-flow UI (Items 2, 5)
- Week 2: Push subscription endpoints + server integration + tests (Item 6)
- Week 3: Background sync, periodic sync, Badging (Items 7, 8)
- Week 4: Packaging and CI Lighthouse integration (Items 9, 10)

## Checklist (developer tasks you can follow)
- [ ] Fix `static/app/sw.js` duplicate constants, add `clients.claim()` and navigation preload setup
- [ ] Ensure `static/app/offline.html` exists and is cached
- [ ] Expand and correct `static/app/manifest.json` icons, id, and screenshots
- [ ] Implement `beforeinstallprompt` handling and show a custom install CTA in app UI
- [ ] Generate VAPID keys and implement server subscription endpoints
- [ ] Add Background Sync handlers for queued writes and Periodic Sync for freshness
- [ ] Add Lighthouse CI in CI pipeline and guard PWA regressions
- [ ] Create packaging scripts for TWA and Windows packaging

---

If you want, I can:
- Produce a concrete patch for [`static/app/sw.js`](static/app/sw.js:1) to implement the recommended SW fixes and caching structure.
- Produce an updated [`static/app/manifest.json`](static/app/manifest.json:1) with a complete icon matrix and suggested fields.
Choose one of these next steps and I will switch to code mode to make the edits.