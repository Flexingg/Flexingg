# Static Files Documentation

## Overview
The `static/` directory contains assets for the PWA (Progressive Web App) functionality, icons, service worker, and screenshots. These support offline capability, app installation, and visual elements. No CSS/JS bundles; styles are inline or CDN. Structure: `static/app/` for icons/manifest, `static/screenshots/` for images. Served via STATICFILES_DIRS in settings.py and Whitenoise.

## PWA Configuration
- **manifest.json**: Defines PWA metadata for installability.
  - **Key Properties** (inferred standard):
    - name/short_name: "Flexin.gg" – App name.
    - icons: Array of PNG icons (e.g., 192x192, 512x512) from `static/app/icons/`.
    - start_url: "/" – Entry point.
    - display: "standalone" – Full-screen app mode.
    - theme_color/background_color: "#000000" – Dark theme.
    - orientation: "portrait-primary" – Mobile focus.
  - **Usage**: Linked in base.html `<link rel="manifest" href="/manifest.json">`; enables add-to-home-screen.
  - **Location**: `static/manifest.json`.

- **sw.js** (Service Worker):
  - **Purpose**: Handles caching for offline use, background sync.
  - **Key Features** (standard PWA SW):
    - Registers routes for caching static assets, API responses.
    - Cache-first for static, network-first for dynamic (e.g., chart data).
    - Offline fallback to `offline.html`.
    - Background sync for Garmin data.
  - **Usage**: Registered in base.html script: `navigator.serviceWorker.register('/sw.js')`.
  - **Location**: `static/sw.js`.

## Icons and App Assets
- **Directory**: `static/app/icons/` – Various sizes/formats for PWA, favicon.
  - **chrome-icon-144.png**, **192.png**, **512.png**: Chrome/Android icons (144x144, 192x192, 512x512).
  - **favicon.png**: Browser favicon.
  - **icon.png**: General app icon (likely 512x512).
  - **splash.png**: Splash screen image.
  - **adaptive-icon/background.png**, **foreground.png**: Android adaptive icon layers.
  - **pwa/chrome-icon/**: Subset for PWA-specific (duplicates).
  - **shortcuts/prayer_icon.png**, **read_icon.png**: App shortcut icons (possibly unused/misplaced for fitness app).
- **Usage**: Referenced in manifest.json and base.html `<link rel="icon" ...>`, `<link rel="apple-touch-icon" ...>`.
- **Format**: PNG; pixel-art style matching theme.

## Screenshots
- **Directory**: `static/screenshots/`.
  - **home.jpg**: Screenshot of home/dashboard page.
- **Usage**: For app store submission or manifest (screenshots array); displays app preview.
- **Format**: JPG; high-res for promotion.

## App Structure
- **static/app/**: Root for PWA assets.
  - **favicon.ico**: Fallback favicon.
  - Icons subdirs as above.
- **Overall**: No user-uploaded media; all static. Collect with `python manage.py collectstatic` for production.
- **Dependencies**: CDN for Tailwind, Font Awesome, Chart.js, Cal-Heatmap, Alpine.js, HTMX – not local.
- **Best Practices**: Optimize icons (compress PNGs); update manifest for new features; test SW with Lighthouse.

This setup enables PWA installation, offline viewing (via offline.html), and consistent branding.