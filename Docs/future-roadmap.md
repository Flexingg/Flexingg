# Future Roadmap

Here is a list of features and fixes planned for the future development of Flexingg.

## Tasks

## PWA Work (deferred / future)

The following PWA-related items were intentionally deferred from the initial rollout and moved here. Once you are ready to provide the required assets, secrets, and approvals (see `Docs/pwa.md`), I can implement them in code.

- Push Notifications (deferred)
  - Tasks:
    - Generate VAPID keypair and provide values as environment variables (recommended names: `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`).
    - Server-side subscription endpoints: `POST /api/push/subscribe` and `DELETE /api/push/unsubscribe`.
    - Server push sender implementation (e.g., Django + pywebpush) and scheduled/triggered push workflows.
    - Client subscription UI and permission UX. Persist subscriptions to DB.
    - Acceptance criteria: successful subscription from an Android Chrome device, and ability to send a test notification from server.
  - Why deferred: requires sensitive keys and infra decisions; moved to roadmap until keys and policy are ready.

- Packaging & Store Distribution (deferred)
  - Tasks:
    - Prepare TWA using Bubblewrap or publishable PWABuilder package.
    - Provide store assets (screenshots, privacy policy URL, contact email).
    - Sign artifacts with your keystore (you keep signing keys private).
  - Why deferred: not shipping to Play/Store in this phase.

- Background Sync & Periodic Sync (deferred)
  - Tasks:
    - Implement Background Sync for queued writes (e.g., offline workout submissions).
    - Implement Periodic Background Sync for refreshing cached leaderboards where supported.
    - Provide fallbacks for unsupported browsers.
  - Why deferred: requires additional server-side idempotency and conflict-handling logic.

- Advanced integrations / enhancements
  - Badging API integration for unread counts (progressive enhancement).
  - Deeper offline snapshots for leaderboards/profile (pre-generated JSON).
  - CI Lighthouse automation for PWA checks.

See the main PWA plan for implementation details: [`Docs/pwa.md`](Docs/pwa.md:1). When you're ready to proceed with any of the deferred items, upload the required keys/assets or tell me which item to implement first and I will proceed with concrete code changes.
